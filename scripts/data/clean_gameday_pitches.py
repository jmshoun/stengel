"""
Cleaning GameDay Pitch Records

There are a lot of strange things in GameDay PitchFx data, especially in the 2008 season
(most notoriously, at-bats with hundreds of pitches). Stengel's parser is robust enough to
handle most of these issues, but there are still a few edge cases that throw everything for
a loop. This script removes all of the edge cases in GameDay records from 2008 through
2016.
"""

import os

import stengel.data.clean as clean


# Define the path to the data directory
script_path = os.path.dirname(os.path.abspath(__file__))
data_root = os.path.join(script_path, os.pardir, os.pardir, "data")

# Bizarre duplicated at-bat in one game.
clean.remove_at_bat("TBA201209080", 78, data_root)

# Plate appearances with four balls prior to a strikeout.
clean.remove_pitch("COL201109060", 389, data_root)
clean.remove_pitch("TEX201106250", 122, data_root)
clean.remove_pitch("DET200809040", 237, data_root)

# Extremely weird hit-by-pitch call that was later ruled to be an unchecked bunt.
clean.remove_pitch("MIN200807310", 451)
