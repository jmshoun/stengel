import os
import sys
import unittest
import csv

parent_directory = os.path.abspath(os.path.join(sys.path[0], os.pardir))
sys.path.insert(0, parent_directory)

import stengel.sim.sub as sub


class TestSubstitution(unittest.TestCase):
    def test_substitution_from_retrosheet(self):
        substitution = sub.Substitution.from_retrosheet(["sub", "melam001", "Mark Melancon", "0", "0", "1"])
        self.assertEqual(substitution.__dict__, sub.Substitution("melam001", "away", -1, 1).__dict__)


class TestHandednessAdjustment(unittest.TestCase):
    def test_handedness_adjustment_from_retrosheet(self):
        adjustment = sub.HandednessAdjustment.from_retrosheet(["badj", "abcde001", "R"])
        self.assertEqual(adjustment.__dict__, sub.HandednessAdjustment("R").__dict__)
        adjustment = sub.HandednessAdjustment.from_retrosheet(["padj", "abcde001", "L"])
        self.assertEqual(adjustment.__dict__, sub.HandednessAdjustment("L", "pitcher").__dict__)
