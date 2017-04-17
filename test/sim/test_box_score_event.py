import os
import sys
import unittest
import datetime

parent_directory = os.path.abspath(os.path.join(sys.path[0], os.pardir))
sys.path.insert(0, parent_directory)

import stengel.sim.player as player
import stengel.sim.box_score_event as bse


class TestBoxScoreEvent(unittest.TestCase):
    def test_batter_events(self):
        players = player.Players()

        # First PA: strikeout
        players.update(bse.PlateAppearance("clemr001", "boggw001"))
        players.update(bse.Strikeout("clemr001", "boggw001"))
        boggs_stats = players.batters["boggw001"].event_counters
        self.assertEqual(boggs_stats, {"plate_appearance": 1, "strikeout": 1})

        # Second PA: Walk
        players.update(bse.PlateAppearance("clemr001", "boggw001"))
        players.update(bse.Walk("clemr001", "boggw001"))
        self.assertEqual(boggs_stats, {"plate_appearance": 2, "strikeout": 1, "walk": 1})

        # Third PA: Cancelled
        players.update(bse.PlateAppearance("clemr001", "boggw001"))
        self.assertEqual(boggs_stats, {"plate_appearance": 3, "strikeout": 1, "walk": 1})
        players.update(bse.PlateAppearance("clemr001", "boggw001", decrement=True))
        self.assertEqual(boggs_stats, {"plate_appearance": 2, "strikeout": 1, "walk": 1})

        # Fourth PA: Walk
        players.update(bse.PlateAppearance("cler001", "boggw001"))
        players.update(bse.Walk("clemr001", "boggw001"))
        self.assertEqual(boggs_stats, {"plate_appearance": 3, "strikeout": 1, "walk": 2})

        # Fifth PA: Hit by Pitch
        players.update(bse.PlateAppearance("cler001", "boggw001"))
        players.update(bse.HitByPitch("clemr001", "boggw001"))
        self.assertEqual(boggs_stats, {"plate_appearance": 4, "strikeout": 1, "walk": 2,
                                       "hit_by_pitch": 1})

    def test_pitcher_default_events(self):
        players = player.Players()
        players.update(bse.Strikeout("clemr001", "boggw001"))
        clemens_stats = players.pitchers["clemr001"].event_counters
        self.assertEqual(clemens_stats, {"strikeout": 1})
        players.update(bse.Walk("clemr001", "boggw001"))
        self.assertEqual(clemens_stats, {"strikeout": 1, "walk": 1})
        players.update(bse.Walk("clemr001", "boggw001"))
        self.assertEqual(clemens_stats, {"strikeout": 1, "walk": 2})
        players.update(bse.HitByPitch("clemr001", "boggw001"))
        self.assertEqual(clemens_stats, {"strikeout": 1, "walk": 2, "hit_by_pitch": 1})

    def test_pitcher_first_call(self):
        players = player.Players()
        players.update(bse.CallPitcher("clemr001", datetime.date(2010, 1, 1)))
        clemens = players.pitchers["clemr001"]
        self._assert_pitch_counts(clemens, 0, 0, 0, 0)
        self.assertEqual(clemens.pitches_at_last_game, 0)
        self.assertIsNone(clemens.days_since_last_game)

    def test_pitcher_second_call(self):
        players = player.Players()
        players.update(bse.CallPitcher("clemr001", datetime.date(2010, 1, 1)))
        players.update(bse.Pitch("clemr001"))
        players.update(bse.Pitch("clemr001"))
        players.update(bse.Pickoff("clemr001", "sciom001"))
        players.update(bse.CallPitcher("clemr001", datetime.date(2010, 1, 25)))
        clemens = players.pitchers["clemr001"]
        self._assert_pitch_counts(clemens, 0, 0, 0, 0)
        self.assertEqual(clemens.pitches_at_last_game, 2)
        self.assertEqual(clemens.days_since_last_game, 24)

    def test_pitcher_pitch_counts(self):
        players = player.Players()
        players.update(bse.CallPitcher("clemr001", datetime.date(2010, 1, 1)))
        clemens = players.pitchers["clemr001"]
        players.update(bse.Pitch("clemr001"))
        self._assert_pitch_counts(clemens, 1, 1, 0, 0)
        players.update(bse.Pitch("clemr001"))
        self._assert_pitch_counts(clemens, 2, 2, 0, 0)
        players.update(bse.Pickoff("clemr001", "sciom001"))
        self._assert_pitch_counts(clemens, 2, 2, 1, 1)
        players.update(bse.PlateAppearance("clemr001", "boggw001"))
        players.update(bse.Pickoff("clemr001", "sciom001"))
        self._assert_pitch_counts(clemens, 2, 0, 2, 1)
        players.update(bse.Pitch("clemr001"))
        self._assert_pitch_counts(clemens, 3, 1, 2, 1)

    def _assert_pitch_counts(self, pitcher, pitch_count_game, pitch_count_at_bat,
                             pickoff_count_game, pickoff_count_at_bat):
        self.assertEqual(pitcher.pitch_count_game, pitch_count_game)
        self.assertEqual(pitcher.pitch_count_at_bat, pitch_count_at_bat)
        self.assertEqual(pitcher.pickoff_count_game, pickoff_count_game)
        self.assertEqual(pitcher.pickoff_count_at_bat, pickoff_count_at_bat)
