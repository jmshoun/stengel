"""
Adding Players

This script does the following:
    - Download a table with basic player information from Retrosheet.
    - Creates a new collection called players in MongoDB.
    - Uploads Player records for all players born after 1900 to the database.

Expected runtime: A few seconds.
"""

import csv

import pymongo

import stengel.sim.player as player
import stengel.data.download as download

# Download the basic player info
print("Downloading Retrosheet player list...")
player_file = download.retrosheet_players()

# Set up connection to database
client = pymongo.MongoClient("mongodb://localhost:23415")
database = client.stengel

# Load all the player info CSV
with open(player_file, "r") as infile:
    game_reader = csv.reader(infile)
    player_data = [row for row in game_reader]
# Remove header row
player_data = player_data[1:]

print("Parsing Retrosheet player list...")
players = [player.Player.from_player_row(row) for row in player_data
           if len(row) and row[3][6:] >= "1900"]  # strftime years must be >= 1900
print("Uploading player objects...")
database.players.insert_many([p.as_dict() for p in players])
print("Creating index on id_...")
database.games.create_index([("id_", pymongo.ASCENDING)])
print("Creating index on mlb_debut....")
database.games.create_index([("mlb_debut", pymongo.ASCENDING)])
print("Creating index on mlb_final...")
database.games.create_index([("mlb_final", pymongo.ASCENDING)])
