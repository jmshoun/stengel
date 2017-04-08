import os
import sys
import argparse
import glob

import pymongo
import progressbar

script_path = os.path.dirname(os.path.abspath(__file__))
main_path = os.path.join(script_path, os.pardir, os.pardir)
sys.path.insert(0, main_path)

import stengel.data.parse as parse


def year(filename):
    return int(filename.split("/")[2])


def get_event_files(first_year, last_year):
    all_files = glob.glob("data/retrosheet/*/*.EV*")
    return [f for f in all_files
            if first_year <= year(f) <= last_year]

# Set up argument parser
arg_parser = argparse.ArgumentParser(description="Parse one or years of Retrosheet event data.")
arg_parser.add_argument("-f", "--first-year", type=int, default=0001,
                        help="""First year of Retrosheet events to parse. Default is the earliest
                        event file in data/retrosheet.""")
arg_parser.add_argument("-l", "--last-year", type=int, default=9999,
                        help="""Last year of Retrosheet events to parse. Default is the latest
                        event file in data/retrosheet.""")
args = arg_parser.parse_args()

# Set up connection to database
client = pymongo.MongoClient("mongodb://localhost:23415")
database = client.stengel

# Parse all of the Retrosheet files
print("Parsing Retrosheet game files...")
bar = progressbar.ProgressBar()
files = get_event_files(args.first_year, args.last_year)
for f in bar(files):
    game_parser = parse.RetrosheetGameFileParser(f)
    game_parser.parse()
    game_parser.upload(database)

# Create indices for the games
print("Creating index on metadata.id_...")
database.games.create_index([("metadata.id_", pymongo.ASCENDING)])
print("Creating index on metadata.game_date...")
database.games.create_index([("metadata.game_date", pymongo.ASCENDING)])
