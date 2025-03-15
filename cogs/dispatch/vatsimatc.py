from collections import defaultdict
import threading
import requests
import json
import csv
import datetime
import pathlib


def _path(x):
    return pathlib.Path(__file__).parent.resolve().joinpath(f"data/{x}")


class Station:
    def __init__(self, ident, typ):
        self.ident = ident
        self.type = typ

    def __hash__(self):
        return hash(self.ident + '_' + self.type)
    
    def __eq__(self, other):
        return self.ident == other.ident and self.type == other.type

    def __repr__(self):
        return f"<Station {self.ident} {self.type}>"

    def score(self):
        if self.type == "ATIS":
            score = 50
        if self.type == "CTR":
            score = 100
        if self.type in ("APP", "DEP"):
            score = 100
        if self.type == "TWR":
            score = 100
        if self.type == "GND":
            score = 50
        if self.type == "DEL":
            score = 10
        nowutc = datetime.datetime.now(tz=datetime.timezone.utc)
        ratio = 1.0 - (nowutc - self.start) / datetime.timedelta(hours=3)
        if ratio <= 0.25:
            ratio = 0.25
        if ratio > 1:
            ratio = 1
        return int(score * ratio)



class ATCPresence:
    def __init__(self):
        self.mutex = threading.Lock()

    def load_stations(self):
        self.stations = defaultdict(set)
        with open(_path("stations.csv"), "r", encoding="utf-8-sig") as csvfile:
            reader = csv.reader(csvfile)
            next(reader)
            for row in reader:
                stations = []
                for cell in filter(lambda cell: cell != "\\N", row[1:]):
                    x = cell.split('_')
                    stations.append(Station(x[0], x[1]))
                self.stations[row[0]] = set(stations)
        with open(_path("computed_positions.csv"), "r", encoding="utf-8-sig") as csvfile:
            reader = csv.reader(csvfile)
            next(reader)
            for row in reader:
                stations = []
                for cell in filter(lambda cell: cell != "\\N", row[1:]):
                    x = cell.split('_')
                    stations.append(Station(x[0], x[1]))
                self.stations[row[0]] = set(stations)
        with open(_path("airport_to_fir_callsigns.csv"), "r") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                for fir in row[1].split("|"):
                    f = fir.split("_")[0]
                    self.stations[row[0]].add(Station(f, "CTR"))
        def _maybe_fixup(airport, typ):
            if not list(filter(lambda x: x.type == typ, self.stations[airport])):
                self.stations[airport].add(Station(airport, typ))
        for airport in self.stations:
            _maybe_fixup(airport, "TWR")
            _maybe_fixup(airport, "DEP")
            _maybe_fixup(airport, "ARR")
            _maybe_fixup(airport, "GND")
            _maybe_fixup(airport, "DEL")



    def _get_json(self, url):
        payload = {}
        headers = {"Accept": "application/json"}
        response = requests.request("GET", url, headers=headers, data=payload)
        return json.loads(response.text)

    def fetch(self):
        self.json = self._get_json("https://api.vatsim.net/v2/atc/online")
        self.json_atis = self._get_json("https://data.vatsim.net/v3/afv-atis-data.json")

    def process(self):
        vatsim_stations = {}
        for x in self.json:
            y = x["callsign"].split("_")
            station = Station(y[0], y[-1])
            station.start = datetime.datetime.fromisoformat(x["start"])
            vatsim_stations[station] = station
        for x in self.json_atis:
            station = Station(x["callsign"].split("_")[0], 'ATIS')
            station.start =  datetime.datetime.fromisoformat(x['logon_time'])
            vatsim_stations[station] = station
        with self.mutex:
            self.vatsim_stations = vatsim_stations

    def list_coverage(self, airport_code):
        ret = set()
        for station in self.stations[airport_code]:
            with self.mutex:
                if station in self.vatsim_stations:
                    ret.add(self.vatsim_stations[station])
        if Station(airport_code, 'ATIS') in self.vatsim_stations:
            ret.add(self.vatsim_stations[Station(airport_code, 'ATIS')])
        return list(ret)
    
    def score(self, icao):
        score = 0
        for coverage in self.list_coverage(icao):
            score += coverage.score()
        return score

    def load(self):
        self.load_stations()
        self.fetch()
        self.process()
        return self

    def run(self):
        self.event = threading.Event()
        with self.mutex:
            self.loop = True
        def _get_loop():
            with self.mutex:
                return self.loop
        while _get_loop():
            self.fetch()
            self.process()
            self.event.wait(timeout=5 * 60)

    def stop(self):
        with self.mutex:
            self.loop = False
        self.event.set()
        self.thread.join()

    def start(self):
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
        return self

atc_presence = ATCPresence().load().start()


def main():
    print(list(atc_presence.stations["KDEN"]))
    print(list(atc_presence.stations["LFPG"]))
    print(list(atc_presence.list_coverage("LFPG")))
    print(list(atc_presence.stations["LGAV"]))
    print(list(atc_presence.list_coverage("LGAV")))
    print(list(atc_presence.stations["KCLE"]))
    print(list(atc_presence.list_coverage("KCLE")))
    print(list(atc_presence.list_coverage("EGHE")))

    atc_presence.stop()


if __name__ == "__main__":
    main()
