import os
import sys
import unittest

parent_directory = os.path.abspath(os.path.join(sys.path[0], os.pardir))
sys.path.insert(0, parent_directory)

import stengel.sim.pitch as pitch
import stengel.sim.bases as bases


class TestPitch(unittest.TestCase):
    def test_retrosheet_constructor(self):
        # Retrosheet code for called strike
        strike = pitch.Pitch.from_retrosheet("C")
        self.assertEqual(strike.pitch_event, "strike")
        self.assertFalse(strike.swung)
        self.assertFalse(strike.bunted)
        self.assertTrue(strike.threw)

    def test_retrosheet_constructor_with_modifier(self):
        ball = pitch.Pitch.from_retrosheet(">B")
        self.assertEqual(ball.pitch_event, "ball")
        self.assertTrue(ball.threw)
        self.assertFalse(ball.swung)
        self.assertTrue(ball.ran_on_play)

    def test_retrosheet_constructor_of_pickoff(self):
        pickoff = pitch.Pitch.from_retrosheet("2")
        self.assertEqual(pickoff.pitch_event, "pickoff")
        self.assertEqual(pickoff.destination, bases.SECOND_BASE)
        self.assertTrue(pickoff.threw)
        self.assertFalse(pickoff.swung)
