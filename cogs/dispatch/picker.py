from typing import List, Optional, Set, Dict, Tuple, Self

import math
import pathlib
import csv
import random
import cogs.dispatch.aircraft_lib as aircraft_lib
import cogs.dispatch.vatsimatc as vatsimatc
import pathlib


class Airport:
    def __init__(self, row):
        self.code, self.type, self.lat, self.long, self.continent = (
            row["icao_code"],
            row["type"],
            float(row["latitude_deg"]),
            float(row["longitude_deg"]),
            row["continent"],
        )

    # haversine distance, per https://www.movable-type.co.uk/scripts/latlong.html
    def distance(self, other: Self) -> float:
        """Distance between self and other in nautical miles."""
        lat1, lon1 = self.lat, self.long
        lat2, lon2 = other.lat, other.long
        R = 3440  # Earth average radius in nautical miles
        φ1 = lat1 * math.pi / 180
        φ2 = lat2 * math.pi / 180
        Δφ = (lat2 - lat1) * math.pi / 180
        Δλ = (lon2 - lon1) * math.pi / 180

        a = math.sin(Δφ / 2) * math.sin(Δφ / 2) + math.cos(φ1) * math.cos(
            φ2
        ) * math.sin(Δλ / 2) * math.sin(Δλ / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        d = R * c  # in nautical miles
        return d


class AirportFilter:
    types: Set[str]
    continents: Set[str]

    def __init__(self):
        self.types = set()
        self.continents = set()

    def airport_filter(self, x: Airport) -> bool:
        if self.continents and not x.continent in self.continents:
            return False
        if self.types and not x.type in self.types:
            return False
        return True

    def filter_airports(self, airports: List[Airport]) -> List[Airport]:
        return list(filter(self.airport_filter, airports))


class Airports:
    airports: List[Airport]

    def __init__(self):
        self.airports = []

    def load(self):
        path = pathlib.Path(__file__).parent.resolve().joinpath("data/airports.csv")
        with open(path, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                airport = Airport(row)
                if airport.code:
                    self.airports.append(airport)

    def pick_random(self, ap_filter: AirportFilter) -> Optional[Airport]:
        filtered_airports = ap_filter.filter_airports(self.airports)
        if not filtered_airports:
            return None
        return random.choice(filtered_airports)

    def airports_sorted_by_distance_to(
        self,
        ref_airport: Airport,
        ap_filter: AirportFilter,
        min_distance_nm: int = 200,
        max_distance_nm: int = 400,
    ) -> List[Airport]:
        filtered_airports_with_distance = []
        for airport in ap_filter.filter_airports(self.airports):
            d = ref_airport.distance(airport)
            if d < min_distance_nm:
                continue
            if d > max_distance_nm:
                continue
            filtered_airports_with_distance.append((d, airport))
        return list(
            map(
                lambda x: x[1],
                sorted(filtered_airports_with_distance, key=lambda x: x[0]),
            )
        )


class AirportPairPicker:
    airports: Airports
    airport_filter: AirportFilter
    aircraft_type: str

    def __init__(self, airports: Airports, aircrafts: aircraft_lib.Aircrafts):
        self.airports = airports
        self.aircrafts = aircrafts
        self.aircraft_type = "SF50"

    def set_aircraft_type(self, t: str) -> Optional[str]:
        """Returns None on success, an error code otherwise."""
        if not self.aircrafts.get(t):
            return "unknown"
        self.aircraft_type = t
        return None

    def distances_from_type(self, hours: float) -> Tuple[float, float]:
        acceptable_shift = hours / 3
        if acceptable_shift > 1:
            acceptable_shift = 1
        min_hours = hours - (acceptable_shift/2)
        if min_hours <= 0.25:
            min_hours = 0.25
        max_hours = hours + (acceptable_shift/2)
        ac = self.aircrafts.get(self.aircraft_type)
        min_ = ac.cruise_speed * min_hours
        max_ = ac.cruise_speed * max_hours
        print(f"Guessed distances for {self.aircraft_type} min: {min_} max: {max_}")
        return (min_, max_)

    def pick_pair(
        self, hours: float, ap_filter: AirportFilter
    ) -> Tuple[Optional[Airport], Optional[Airport], Dict[str, str]]:
        min_distance_nm, max_distance_nm = self.distances_from_type(hours)
        for i in range(1, 25):
            airport1 = self.airports.pick_random(ap_filter=ap_filter)
            if not airport1:
                return None, None, {}
            print(f'->{airport1.code}')
            airports = self.airports.airports_sorted_by_distance_to(
                airport1,
                ap_filter=ap_filter,
                min_distance_nm=int(min_distance_nm),
                max_distance_nm=int(max_distance_nm),
            )
            if len(airports) > 1:
                airport2 = airports[1]
                return airport1, airport2, {}
        return None, None, {}


class AirportPairPickerVatsim(AirportPairPicker):
    kept: List[Tuple[int, Tuple[Airport, Airport]]]
    vatsim_scored_airports: List[Airport]
    score_buckets: Dict[int, List[Airport]]

    def __init__(self, airports, aircrafts):
        super().__init__(airports, aircrafts)
        self.vatsim_scores = dict()

    def vatsim_score(self, code: str | Airport) -> int:
        if isinstance(code, Airport):
            code = code.code
        if not code in self.vatsim_scores:
            return 0
        return self.vatsim_scores[code]

    def pick_pair(
        self, hours: float, ap_filter: AirportFilter
    ) -> Tuple[Optional[Airport], Optional[Airport], Dict[str, str]]:
        dbg_hash = dict()
        self.kept = []
        self.score_airports_vatsim(ap_filter)
        min_distance_nm, max_distance_nm = self.distances_from_type(hours)
        print(
            f"Picking pair from {len(self.vatsim_scored_airports)} airports with distance within {min_distance_nm} and {max_distance_nm}"
        )

        for i in range(0, len(self.vatsim_scored_airports)):
            a1 = self.vatsim_scored_airports[i]
            added_with_a1 = 0
            for j in range(i + 1, len(self.vatsim_scored_airports)):
                a2 = self.vatsim_scored_airports[j]
                distance = a1.distance(a2)
                if min_distance_nm <= distance <= max_distance_nm:
                    score = self.vatsim_score(a1) + self.vatsim_score(a2)
                    data = a1, a2
                    self.keep_top_n(self.kept, score, data)
                    added_with_a1 += 1
                # elite optimization, we know scores are decreasing in self.vatsim_scored_airports, so as soon as we selected 3 matching airports, futher discovered airport should only be lower scoring.
                if added_with_a1 >= 3:
                    break
        score_text = ""
        for x in self.kept:
            score, (a1, a2) = x
            score_text += f"{a1.code}-{a2.code}: {score}\n"
        dbg_hash["Pair scores:"] = score_text

        ap_score_text = ""
        for ap in self.vatsim_scored_airports[0:20]:
            ap_score_text += f"{ap.code}: {self.vatsim_score(ap)}\n"
        dbg_hash["Airport scores"] = ap_score_text

        if not self.kept:
            return None, None, dbg_hash

        # pick out of self.kept
        _, (a1, a2) = random.choice(self.kept)
        if a1:

            def dbgstr(a):
                a_dbgstr = []
                a_coverage = vatsimatc.atc_presence.list_coverage(a.code)
                for station in a_coverage:
                    a_dbgstr.append(
                        f"{station.ident} {station.type} {station.score()}"
                    )
                return "\n".join(a_dbgstr)

            dbg_hash["Chosen"] = (
                f"{a1.code}: {self.vatsim_score(a1)} ({dbgstr(a1)})\n"
                f"{a2.code}:{self.vatsim_score(a2)} ({dbgstr(a2)})\n"
            )

        # The algorithm organically gives the highest scoring first... we'd
        # rather land there.
        return a2, a1, dbg_hash

    def score_airports_vatsim(self, ap_filter: AirportFilter):
        score_buckets: Dict[int, List[Airport]] = {}
        for airport in ap_filter.filter_airports(self.airports.airports):
            score = vatsimatc.atc_presence.score(airport.code)
            self.vatsim_scores[airport.code] = score
            if score == 0:
                continue
            if score not in score_buckets:
                score_buckets[score] = []
            score_buckets[score].append(airport)
        ret = []
        for score in sorted(score_buckets.keys(), reverse=True):
            random.shuffle(score_buckets[score])
            ret += score_buckets[score]
        self.vatsim_scored_airports = ret

    def keep_top_n(
        self,
        l: List[Tuple[int, Tuple[Airport, Airport]]],
        score: int,
        data: Tuple[Airport, Airport],
        n: int = 20,
    ):
        if len(l) >= n:
            if score < l[0][0]:
                return
        l.insert(0, (score, data))
        l.sort(key=lambda x: x[0])
        if len(l) > n:
            l.pop(0)
