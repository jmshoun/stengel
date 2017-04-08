from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

from . import serialize


class Substitution(serialize.DictSerialize):
    """Represent a player substitution in a baseball game."""
    player_ndx = 1
    team_ndx = 3
    batting_ndx = 4
    fielding_ndx = 5

    def __init__(self, player_id, team, batting, fielding):
        """Default constructor."""
        self.event_type = "substitution"
        self.player_id = player_id
        self.team = team
        self.batting = batting
        self.fielding = fielding

    @classmethod
    def from_retrosheet(cls, row):
        """Constructor from a Retrosheet event file row."""
        player_id = row[cls.player_ndx]
        team = "home" if row[cls.team_ndx] == "1" else "away"
        batting = int(row[cls.batting_ndx]) - 1
        fielding = int(row[cls.fielding_ndx])
        return cls(player_id, team, batting, fielding)


class HandednessAdjustment(serialize.DictSerialize):
    """Represent an unexpected change in handedness from a pitcher or batter."""
    position_ndx = 0
    handedness_ndx = 2

    def __init__(self, handedness, position="batter"):
        """Default constructor."""
        self.event_type = "handedness_adjustment"
        self.handedness = handedness
        self.position = position

    @classmethod
    def from_retrosheet(cls, row):
        """Constructor from a Retrosheet event file row."""
        position = "batter" if row[cls.position_ndx] == "badj" else "pitcher"
        return cls(handedness=row[cls.handedness_ndx], position=position)
