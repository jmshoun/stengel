import sys
import os
import unittest

parent_directory = os.path.abspath(os.path.join(sys.path[0], os.pardir))
sys.path.insert(0, parent_directory)

import stengel.data.clean as clean


class TestCleanRetrosheet(unittest.TestCase):
    def test_missing_file(self):
        result = clean.replace_line("BAL999906130", "this file", "shouldn't exist")
        self.assertFalse(result)
