import unittest
import aircraft_lib


class TestAircrafts(unittest.TestCase):

    def test_smoketest(self):
        acs = aircraft_lib.Aircrafts()
        acs.load_database()
        self.assertEqual(acs.get("SF50").cruise_speed, 300)
        self.assertEqual(acs.get("C172").cruise_speed, 122)
        self.assertEqual(acs.get("TBM9").cruise_speed, 330)
        self.assertEqual(acs.get("LJ35").cruise_speed, 418)
        # A320 is in the db but not A321, check that our guess is roughly ok
        self.assertLess(acs.get("A321").cruise_speed / 451, 1.25)
        self.assertGreater(acs.get("A321").cruise_speed / 451, 0.75)


if __name__ == "__main__":
    unittest.main()
