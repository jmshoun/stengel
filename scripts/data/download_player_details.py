"""
Downloading Player Details

The basic Retrosheet information on each player is extremely bare-bones -- it doesn't even
have handedness! There's a good bit more information on Retrosheet, but unfortunately it's
split up into one file per player. This script downloads these HTML files for every player
in the MongoDB players collection.

Prerequisites: scripts/data/add_players.py
Expected runtime: About 90 minutes if --first-date is 1980-01-01 and --last-date is
    2016-12-31.
"""

import argparse
import datetime

import pymongo
import progressbar

import stengel.data.download
import stengel.sim.player


def valid_date(s):
    """Validate a date input as a command-line argument."""
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)

parser = argparse.ArgumentParser(description="Download Retrosheet player data.")
parser.add_argument("-f", "--first-date", type=valid_date, default="1900-01-01",
                    help="Earliest player MLB debut date to download, as YYYY-MM-DD.")
parser.add_argument("-l", "--last-date", type=valid_date, default="9999-12-31",
                    help="Latest player MLB debut date to download, as YYYY-MM-DD.")

args = parser.parse_args()

# Set up connection to database
client = pymongo.MongoClient("mongodb://localhost:23415")
database = client.stengel

# Get list of players whose MLB debuts fall within the specified range
player_set = database.players.find({
    "mlb_debut": {"$gte": args.first_date.strftime("%Y-%m-%d"),
                  "$lte": args.last_date.strftime("%Y-%m-%d")}
})
num_players = player_set.count()

# Download the Retrosheet player data for each player
with progressbar.ProgressBar(max_value=num_players) as bar:
    player_number = 0
    for player_record in player_set:
        bar.update(player_number)
        player_id = player_record["id_"]
        stengel.data.download.retrosheet_player(player_id)
        player_number += 1
