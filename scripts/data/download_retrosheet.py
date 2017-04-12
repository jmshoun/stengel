import argparse

import stengel.data.download as download


def download_season_verbose(year):
    print("Downloading {} season data".format(year))
    download.retrosheet_season(year)


def download_multiple_seasons(first_year, last_year):
    for year in range(first_year, last_year + 1):
        download_season_verbose(year)


parser = argparse.ArgumentParser(description="Download one or years of Retrosheet event data.")
parser.add_argument("-y", "--year", type=int, help="Single year to download.")
parser.add_argument("-f", "--first-year", type=int,
                    help="""First of a range of years to download. Ignored if -y supplied,
                    if supplied, must also supply --last-year.""")
parser.add_argument("-l", "--last-year", type=int, help="Last of a range of years to download.")

args = parser.parse_args()

if args.year:
    download_season_verbose(args.year)
elif args.first_year and args.last_year:
    if args.first_year > args.last_year:
        print("WARNING: first_year > last_year; nothing will be downloaded.")
    download_multiple_seasons(args.first_year, args.last_year)
