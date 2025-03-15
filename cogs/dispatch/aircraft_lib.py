import csv
import functools
import pathlib
import collections

_GuessCruiseSpeed = None

def _path(x):
    return pathlib.Path(__file__).parent.resolve().joinpath(f"data/{x}")


class Aircraft:
    def __init__(self, data):
        self.data = data
        self._cruise_speed = None

    def set_cruise_speed(self, cruise):
        self._cruise_speed = float(cruise)

    @property
    def code(self):
        return self.data["ICAO_Code"]

    @property
    @functools.cache
    def Approach_Speed_knot(self):
        return float(self.data["Approach_Speed_knot"])

    @property
    @functools.cache
    def cruise_speed(self):
        if self._cruise_speed:
            return self._cruise_speed
        # If we don't know we guess
        return _GuessCruiseSpeed(self)

    @property
    def cwt(self):
        return self.data["CWT"]

    @property
    def Model_FAA(self):
        return self.data["Model_FAA"]



class Aircrafts:
    def __init__(self):
        self.data = {}
        self.ratio_avg_per_cwt = {}

    def get(self, x):
        if not x in self.data:
            return None
        return self.data[x]

    def load_database(self):
        with open(_path("aircraft_data.csv")) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.data[row["ICAO_Code"]] = Aircraft(row)
        ratio_sum_per_cwt = collections.defaultdict(float)
        with open(_path("cruise_speeds.csv")) as f:
            reader = csv.DictReader(f)
            aircrafts = []
            for row in reader:
                ac = self.get(row["ICAO_Code"])
                ac.set_cruise_speed(row["cruise_kts"])
                aircrafts.append(ac)
            count_per_cwt = collections.defaultdict(int)
            for aircraft in aircrafts:
                count_per_cwt[aircraft.cwt] += 1
                ratio_sum_per_cwt[aircraft.cwt] += (
                    aircraft.cruise_speed / aircraft.Approach_Speed_knot
                )
        for k in ratio_sum_per_cwt:
            self.ratio_avg_per_cwt[k] = ratio_sum_per_cwt[k] / count_per_cwt[k]
        global _GuessCruiseSpeed
        _GuessCruiseSpeed = self.guess_cruise_speed

    def guess_cruise_speed(self, aircraft):
        return aircraft.Approach_Speed_knot * self.ratio_avg_per_cwt[aircraft.cwt]