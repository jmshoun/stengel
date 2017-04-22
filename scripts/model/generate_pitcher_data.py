import argparse
import pickle
import datetime
import os

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
parser.add_argument("-o", "--output", default="data/python/pitch_data.p",
                    help="Name of the file to save the resulting data in.")

args = parser.parse_args()

# Set up connection to database
client = pymongo.MongoClient("mongodb://localhost:23415")
database = client.stengel

print("Generating data...")
generator = stengel.model.pitch_data.PitchDataGenerator(database)
pitch_data = generator.generate_data(
    args.first_date.strftime("%Y/%m/%d"),
    args.last_date.strftime("%Y/%m/%d"))

print("Saving pitch data...")
destination_directory = os.path.join(*args.output.split("/")[-1])
stengel.data.download.create_directory_if_needed(destination_directory)
with file(args.output, "wb") as outfile:
    pickle.dump(pitch_data.as_dict(), outfile, pickle.HIGHEST_PROTOCOL)
