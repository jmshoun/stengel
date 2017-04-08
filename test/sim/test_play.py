import os
import sys
import unittest

parent_directory = os.path.abspath(os.path.join(sys.path[0], os.pardir))
sys.path.insert(0, parent_directory)

import stengel.sim.play as play


class TestGameCalled(unittest.TestCase):
    def test_retrosheet_success(self):
        event = play.GameCalled.from_retrosheet(["com", "Game called due to rain."])
        self.assertEqual(type(event).__name__, "GameCalled")

    def test_retrosheet_failure(self):
        event = play.GameCalled.from_retrosheet(["com", "Some other comment."])
        self.assertIsNone(event)
