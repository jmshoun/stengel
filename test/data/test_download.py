import sys
import os
import time
import math
import shutil
import unittest

foo = os.path.abspath(os.path.join(sys.path[0], os.pardir))
sys.path.insert(0, foo)

import stengel.data.download as download

TEST_DATA_PATH = "_data_download/"


@download.metered_delay(-2.5, 0.001)
def stub_function():
    # A stub function used to test the functionality of metered_delay
    return 42


class TestMeteredDelay(unittest.TestCase):
    def test_return_value(self):
        self.assertEqual(stub_function(), 42, "Return value is incorrect.")

    def test_delay_length(self):
        start_time = time.time()
        stub_function()
        end_time = time.time()
        time_delta = end_time - start_time
        # Allowing ten sigma on either side of the expected delay time. This should
        # essentially never fail due to random variance...
        self.assertGreaterEqual(time_delta, math.exp(-2.51))
        self.assertLessEqual(time_delta, math.exp(-2.49) + 0.001)


class TestRetrosheetPlayers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(TestRetrosheetPlayers, cls).setUpClass()
        download.create_directory_if_needed(TEST_DATA_PATH)
        cls.filename = download.retrosheet_players(TEST_DATA_PATH)

    @classmethod
    def tearDownClass(cls):
        super(TestRetrosheetPlayers, cls).tearDownClass()
        shutil.rmtree(TEST_DATA_PATH)

    def setUp(self):
        if not os.path.exists(self.filename):
            self.fail("File did not download.")

    def test_file_header(self):
        with open(self.filename) as f:
            content = f.readlines()
            content = [line.strip() for line in content]
            self.assertEqual(content[0], "LAST,FIRST,ID,DEBUT", "Header is missing.")

    def test_file_length(self):
        with open(self.filename) as f:
            content = f.readlines()
            # The file had >20K lines as of April 1, 2017; it will get bigger over time.
            self.assertGreaterEqual(len(content), 20000, "File is too short.")

    def test_file_format(self):
        with open(self.filename) as f:
            content = f.readlines()
            commas_per_line = [self._count_commas_on_line(line) for line in content]
            commas_per_line = [commas for commas in commas_per_line if commas > 0]
            self.assertEqual(max(commas_per_line), 3, "Too many commas on at least one line.")
            self.assertEqual(min(commas_per_line), 3, "Not enough commas on at least one line.")
            self.assertGreaterEqual(len(commas_per_line), 20000, "Not enough formatted lines.")

    @staticmethod
    def _count_commas_on_line(line):
        length = len(line.split(",")) - 1
        if length == 1:
            print(line)
        return length
