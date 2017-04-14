import os
import sys
import unittest
import datetime

parent_directory = os.path.abspath(os.path.join(sys.path[0], os.pardir))
sys.path.insert(0, parent_directory)

import stengel.sim.player as player

# Dictionary representation of a player for testing.
player_dict = {"id_": "cleej001", "last_name": "Cleese", "weight": 314,
               "mlb_debut": "1970-01-01", "birth_date": "1947-03-14",
               "bats": None, "throws": None, "first_name": None, "height": None}


class TestPlayer(unittest.TestCase):
    def test_player_from_row(self):
        test_player = player.Player.from_player_row(["Cleese", "John", "cleej001", "02/29/1996"])
        self.assertEqual(test_player.last_name, "Cleese")
        self.assertEqual(test_player.first_name, "John")
        self.assertEqual(test_player.id_, "cleej001")
        self.assertEqual(test_player.mlb_debut, datetime.date(1996, 2, 29))

    def test_player_details_from_retrosheet(self):
        test_player = player.Player(id_="ogeac001")
        test_player.add_details_from_retrosheet_page("test_data/retrosheet/players")
        self.assertEqual(test_player.birth_date, datetime.date(1970, 11, 9))
        self.assertEqual(test_player.bats, "Right")
        self.assertEqual(test_player.throws, "Right")
        self.assertEqual(test_player.height, 74)
        self.assertEqual(test_player.weight, 200)

    def test_player_from_dict(self):
        test_player = player.Player.from_dict(player_dict)
        self.assertEqual(test_player.id_, "cleej001")
        self.assertEqual(test_player.last_name, "Cleese")
        self.assertEqual(test_player.weight, 314)
        self.assertEqual(test_player.mlb_debut, datetime.date(1970, 1, 1))
        self.assertEqual(test_player.birth_date, datetime.date(1947, 3, 14))

    def test_player_to_dict(self):
        test_player = player.Player(id_="cleej001", last_name="Cleese", weight=314,
                                    mlb_debut=datetime.date(1970, 1, 1),
                                    birth_date=datetime.date(1947, 3, 14))
        self.assertEqual(test_player.as_dict(), player_dict)
