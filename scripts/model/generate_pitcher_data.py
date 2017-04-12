import argparse
import pickle
import datetime

import pymongo

import stengel.model.pitch_data
import stengel.data.download


def valid_date(s):
    """Validate a date input as a command-line argument."""
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


parser = argparse.ArgumentParser(
    description="Generate pitch data in a format suitable for subsequent analysis.")
parser.add_argument("-f", "--first-date", type=valid_date, default="1900-01-01",
                    help="Earliest date to include in dataset, as YYYY-MM-DD.")
parser.add_argument("-l", "--last-date", type=valid_date, default="9999-12-31",
                    help="Latest date to include in dataset, as YYYY-MM-DD.")

args = parser.parse_args()

# Set up connection to database
client = pymongo.MongoClient("mongodb://localhost:23415")
database = client.stengel

generator = stengel.model.pitch_data.PitchDataGenerator(
    database,
    args.first_date.strftime("%Y/%m/%d"),
    args.last_date.strftime("%Y/%m/%d")
)

print("Generating data...")
generator.generate_data()

stengel.data.download.create_directory_if_needed("data/python")
print("Saving pitch data...")
with file("data/python/pitch_data.p", "wb") as outfile:
    pickle.dump(generator.pitcher_data, outfile, pickle.HIGHEST_PROTOCOL)
print("Saving batter lookup...")
with file("data/python/batter_lookup.p", "wb") as outfile:
    pickle.dump(generator.batters, outfile, pickle.HIGHEST_PROTOCOL)
print("Saving pitcher lookup...")
with file("data/python/pitcher_lookup.p", "wb") as outfile:
    pickle.dump(generator.pitchers, outfile, pickle.HIGHEST_PROTOCOL)
