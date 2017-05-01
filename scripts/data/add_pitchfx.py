import argparse
import datetime

import pymongo
import progressbar

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

processed_game_ids = []
# Add the PitchFx data to each of the games
with progressbar.ProgressBar(max_value=num_games) as bar:
    game_number = 0
    for game_record in game_set:
        bar.update(game_number)
        game = stengel.sim.game.Game.from_dict(game_record)
        if game.metadata.id_ in processed_game_ids:
            continue

        processed_game_ids.append(game.metadata.id_)
        game.add_pitch_fx("data/gameday/pitches")
        database.games.update({"metadata.id_": game.metadata.id_}, game.as_dict())
        game_number += 1
