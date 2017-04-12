"""
Cleaning Retrosheet Game records

Much like MLB GameDay, there are a few extremely unusual records in the Retrosheet data, to
the point where it wasn't worth adapting the parse to cope with them. Most of the issues
here are games that were called early due to weather or umpires who forgot the count.
There are a few plays in here should be parseable, but the play description didn't follow
Retrosheet conventions. This script removes all of the edge cases in Retrosheet event files
from 2008 through 2016.
"""

import os

import stengel.data.clean as clean

# Define the path to the data directory
script_path = os.path.dirname(os.path.abspath(__file__))
data_root = os.path.join(script_path, os.pardir, os.pardir, "data")

# Games with comments that (according to the parser) mean the game ended early, when it
# really didn't.
clean.replace_line("DET200708240",
                   'com,"$Game ended at 3:30 AM"',
                   'com,""',
                   data_root)
clean.replace_line("TEX200907310",
                   'com,"$Game stopped for rain delay of 2:18 with 3-2 count on Young. When"',
                   'com,""',
                   data_root)

# Games with comments that the parser doesn't recognize as signalling the game ended,
# but that in fact do mean the game ended.
clean.replace_line("CHN200808040",
                   'com,"$Lightning and rain return, game called at this point as"',
                   'com,"$Game called"')
clean.replace_line("CHN201408190",
                   'com,"$Game called for wet grounds after 4:34 rain delay;"',
                   'com,""')

# Plate appearances with four balls (!) before the strikeout.
clean.replace_line("DET200809040",
                   "play,4,0,rodrs002,42,BCBFBFBS,K",
                   "play,4,0,rodrs002,32,BCBFBFS,K")
clean.replace_line("TEX201106250",
                   "play,2,1,cruzn002,32,SBC*BBBFS,K",
                   "play,2,1,cruzn002,32,SBC*BBFS,K")

# Another plate appearance with four balls before the strikeout. Note that this plate
# appearance was interrupted by an umpire review (which was likely the proximate cause
# of the mistake), so to force the most natural sequence of pitches, we have to modify
# both records associated with the plate appearance.
clean.replace_line("TBA201404220",
                   "play,5,1,escoy001,31,BFBBN,OA/UREV",
                   "play,5,1,escoy001,31,BFBCN,OA/UREV")
clean.replace_line("TBA201404220",
                   "play,5,1,escoy001,42,BFBBCBC,K",
                   "play,5,1,escoy001,32,BFBCBC,K")

# A play where the runner was called out on appeal, so it shows as a separate record.
clean.replace_line("CIN201604200",
                   "play,7,0,rabur001,21,.BBCX,S9/L.2-2",
                   "play,7,0,rabur001,21,.BBCX,S9/L.2X2")

# A pickoff without an explicit throw.
clean.replace_line("NYN201405280",
                   "play,5,1,wrigd002,10,*BN,CS3(15)",
                   "play,5,1,wrigd002,10,*B3,CS3(15)")

# A play with an implicit force out at home -- the parser handles implicit force outs at
# second, but everything else must be given explicitly.
clean.replace_line("BAL201009190",
                   "play,4,0,penar002,12,CFBFFX,12(3)/FO/G.2-3;1-2",
                   "play,4,0,penar002,12,CFBFFX,12(3)/FO/G.2-3;1-2;3XH")
