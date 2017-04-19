import os
import sys
import unittest
import datetime

parent_directory = os.path.abspath(os.path.join(sys.path[0], os.pardir))
sys.path.insert(0, parent_directory)

import stengel.sim.player as player

# Dictionary representation of a player for testing.
player_dict_input = {"id_": "cleej001", "last_name": "Cleese", "weight": 314,
                     "mlb_debut": "1970-01-01", "junk_attribute": "some_value"}
player_dict_output = {"id_": "cleej001", "last_name": "Cleese", "weight": 314,
                      "mlb_debut": "1970-01-01", "birth_date": None, "bats": None, "throws": None,
                      "first_name": None, "height": None, "mlb_final": None}


class TestPlayer(unittest.TestCase):
    def test_player_from_row(self):
        test_player = player.PlayerInfo.from_player_row(["Cleese", "John", "cleej001", "02/29/1996"])
        self.assertEqual(test_player.last_name, "Cleese")
        self.assertEqual(test_player.first_name, "John")
        self.assertEqual(test_player.id_, "cleej001")
        self.assertEqual(test_player.mlb_debut, datetime.date(1996, 2, 29))

    def test_player_details_from_retrosheet(self):
        test_player = player.PlayerInfo(id_="ogeac001")
        test_player.add_details_from_retrosheet_page("test_data/retrosheet/players")
        self.assertEqual(test_player.birth_date, datetime.date(1970, 11, 9))
        self.assertEqual(test_player.mlb_final, datetime.date(1999, 10, 2))
        self.assertEqual(test_player.bats, "Right")
        self.assertEqual(test_player.throws, "Right")
        self.assertEqual(test_player.height, 74)
        self.assertEqual(test_player.weight, 200)

    def test_alt_format_player_details_from_retrosheet(self):
        test_player = player.PlayerInfo(id_="adamr001")
        test_player.add_details_from_retrosheet_page("test_data/retrosheet/players")
        self.assertEqual(test_player.birth_date, datetime.date(1959, 1, 21))
        self.assertEqual(test_player.mlb_final, datetime.date(1985, 10, 5))
        self.assertEqual(test_player.bats, "Right")
        self.assertEqual(test_player.throws, "Right")
        self.assertEqual(test_player.height, 74)
        self.assertEqual(test_player.weight, 180)

    def test_player_details_fractional_height(self):
        test_player = player.PlayerInfo(id_="andea001")
        test_player.add_details_from_retrosheet_page("test_data/retrosheet/players")
        self.assertEqual(test_player.height, 71.5)

    def test_player_details_no_debut(self):
        test_player = player.PlayerInfo(id_="kigem001")
        test_player.add_details_from_retrosheet_page("test_data/retrosheet/players")
        self.assertEqual(test_player.birth_date, datetime.date(1980, 5, 30))
        self.assertEqual(test_player.height, 71)
        self.assertEqual(test_player.bats, "Right")

    def test_player_from_dict(self):
        test_player = player.PlayerInfo.from_dict(player_dict_input)
        self.assertEqual(test_player.id_, "cleej001")
        self.assertEqual(test_player.last_name, "Cleese")
        self.assertEqual(test_player.weight, 314)
        self.assertEqual(test_player.mlb_debut, datetime.date(1970, 1, 1))

    def test_player_to_dict(self):
        test_player = player.PlayerInfo(id_="cleej001", last_name="Cleese", weight=314,
                                        mlb_debut=datetime.date(1970, 1, 1))
        self.assertEqual(test_player.as_dict(), player_dict_output)

    def test_player_age_and_tenure(self):
        test_player = player.PlayerInfo(id_="cleej001", birth_date=datetime.date(1950, 2, 11),
                                        mlb_debut=datetime.date(1978, 9, 27))
        test_player_alt = player.PlayerInfo(id_="idlee001")
        evaluation_date = datetime.date(2017, 4, 15)
        self.assertAlmostEqual(test_player.age(evaluation_date), 67.17455, places=4)
        self.assertAlmostEqual(test_player.mlb_tenure(evaluation_date), 38.54973, places=4)
        self.assertIsNone(test_player_alt.age(evaluation_date))
        self.assertIsNone(test_player_alt.mlb_tenure(evaluation_date))
