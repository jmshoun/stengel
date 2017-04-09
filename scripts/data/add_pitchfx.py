import os
import sys
import argparse
import pymongo
import progressbar
import datetime

script_path = os.path.dirname(os.path.abspath(__file__))
main_path = os.path.join(script_path, os.pardir, os.pardir)
sys.path.insert(0, main_path)

import stengel.sim.game


def valid_date(s):
    """Validate a date input as a command-line argument."""
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


parser = argparse.ArgumentParser(description="Add PitchFx data to game records.")
parser.add_argument("-f", "--first-date", type=valid_date, default="1900-01-01",
                    help="Earliest date to add PitchFx data to, as YYYY-MM-DD.")
parser.add_argument("-l", "--last-date", type=valid_date, default="9999-12-31",
                    help="Latest date to add PitchFx data to, as YYYY-MM-DD.")

args = parser.parse_args()

# Set up connection to database
client = pymongo.MongoClient("mongodb://localhost:23415")
database = client.stengel

# Find the games we want to get PitchFx data for
game_set = database.games.find({
    "metadata.game_date": {"$gte": args.first_date.strftime("%Y/%m/%d"),
                           "$lte": args.last_date.strftime("%Y/%m/%d")}
})
num_games = game_set.count()

# Add the PitchFx data to each of the games
with progressbar.ProgressBar(max_value=num_games) as bar:
    game_number = 0
    for game_record in game_set:
        bar.update(game_number)
        game = stengel.sim.game.Game.from_dict(game_record)
        game.add_pitch_fx("data/gameday/pitches")
        game.update(database)
        game_number += 1
