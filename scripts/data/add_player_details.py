"""
Adding Player Details

For each record in the MongoDB players collection, add detailed information from a Retrosheet
player detail file, if available.

Prerequisites: scripts/data/download_player_details.py
Expected runtime: About 4 minutes if download_player_details was run with --first-date as
    1980-01-01.
"""

import pymongo
import progressbar

import stengel.sim.player

# Set up connection to database
client = pymongo.MongoClient("mongodb://localhost:23415")
database = client.stengel

# Get list of all players
player_set = database.players.find()
num_players = player_set.count()

# Add the Retrosheet details for each player
with progressbar.ProgressBar(max_value=num_players) as bar:
    player_number = 0
    for player_record in player_set:
        bar.update(player_number)
        # numeric portions of IDs that are >= 801 are for coaches, managers, etc.
        id_numbers = int(player_record["id_"][5:])
        if id_numbers < 801:
            player = stengel.sim.player.Player.from_dict(player_record)
            player.add_details_from_retrosheet_page()
            database.players.update({"id_": player.id_}, player.as_dict())
        player_number += 1
