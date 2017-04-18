import os
import sys
import unittest
import datetime

from . import test_roster

parent_directory = os.path.abspath(os.path.join(sys.path[0], os.pardir))
sys.path.insert(0, parent_directory)

import stengel.sim.game_status as game_status
import stengel.sim.roster as roster
import stengel.sim.pitch as pitch

test_rosters = {"home": roster.Roster.from_retrosheet(test_roster.test_roster_rows["home"]),
                "away": roster.Roster.from_retrosheet(test_roster.test_roster_rows["away"])}


class TestBoxScoreEventGeneration(unittest.TestCase):
    def test_initial(self):
        test_status = game_status.GameStatus(test_rosters, datetime.date(2010, 1, 1))
        events = test_status.clear_event_buffer()
        self.assertEqual(events[0].name, "call_pitcher")
        self.assertEqual(events[0].pitcher, "saunj001")
        self.assertEqual(events[0].date, datetime.date(2010, 1, 1))
        self.assertEqual(events[1].name, "call_pitcher")
        self.assertEqual(events[1].pitcher, "bradd002")
        self.assertEqual(events[1].date, datetime.date(2010, 1, 1))
        self.assertEqual(events[2].name, "plate_appearance")
        self.assertEqual(events[2].pitcher, "saunj001")
        self.assertEqual(events[2].batter, "sweer001")

    def test_pitch_and_pickoff(self):
        test_status = game_status.GameStatus(test_rosters, datetime.date(2010, 1, 1))
        test_status.clear_event_buffer()
        test_status.pitch(pitch.Pitch.from_retrosheet("C"))
        test_status.pitch(pitch.Pitch.from_retrosheet("S"))
        test_status.pickoff(pitch.Pitch.from_retrosheet("2"))
        test_status.pitch(pitch.Pitch.from_retrosheet("S"))
        events = test_status.clear_event_buffer()
        self.assertEqual(events[0].name, "pitch")
        self.assertEqual(events[1].name, "pitch")
        self.assertEqual(events[2].name, "pickoff")
        self.assertEqual(events[3].name, "pitch")
        self.assertEqual(events[4].name, "strikeout")
        self.assertEqual(events[5].name, "plate_appearance")
        for i in range(6):
            self.assertEqual(events[i].pitcher, "saunj001")
        self.assertEqual(events[4].batter, "sweer001")
        self.assertEqual(events[5].batter, "cabro001")
