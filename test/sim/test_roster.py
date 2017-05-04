import os
import sys
import unittest
import csv

parent_directory = os.path.abspath(os.path.join(sys.path[0], os.pardir))
sys.path.insert(0, parent_directory)

import stengel.sim.roster as roster
import stengel.sim.sub as sub


def load_test_rosters():
    return {"home": load_test_roster("test_data/retrosheet/home_roster.csv"),
            "away": load_test_roster("test_data/retrosheet/away_roster.csv")}


def load_test_roster(filename):
    with open(filename, "r") as infile:
        reader = csv.reader(infile, delimiter=",")
        return [row for row in reader]

test_roster_rows = load_test_rosters()


class TestRoster(unittest.TestCase):
    def test_roster_from_retrosheet(self):
        home_roster = roster.Roster.from_retrosheet(test_roster_rows["home"])
        away_roster = roster.Roster.from_retrosheet(test_roster_rows["away"])
        self.assertTrue(home_roster.home_team)
        self.assertFalse(away_roster.home_team)
        self.assertEqual(home_roster.current_batting_index, 8)
        self.assertEqual(away_roster.current_batting_index, 0)

    def test_current_and_next(self):
        home_roster = roster.Roster.from_retrosheet(test_roster_rows["home"])
        self.assertEqual(home_roster.current_pitcher(), "saunj001")
        self.assertEqual(home_roster.current_batter(), "aybae001")
        home_roster.move_to_next_batter()
        self.assertEqual(home_roster.current_batter(), "figgc001")
        for _ in range(3):
            home_roster.move_to_next_batter()
        self.assertEqual(home_roster.current_batter(), "guerv001")

    def test_substitution(self):
        substitution = sub.Substitution.from_retrosheet(["sub", "melam001", "Mark Melancon", "0", "0", "1"])
        away_roster = roster.Roster.from_retrosheet(test_roster_rows["away"])
        away_roster.substitute(substitution)
        self.assertEqual(away_roster.current_pitcher(), "melam001")
        self.assertEqual(away_roster.relieved, ["bradd002"])