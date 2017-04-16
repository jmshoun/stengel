from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

from . import serialize

"""Static module-level variables mapping position names to Roster indices.

0 is left open so that the indices will line up with Retrosheet conventions (and so that
positions 1-9 will line up with longstanding baseball convention).
"""
PITCHER = 1
CATCHER = 2
FIRST_BASE = 3
SECOND_BASE = 4
THIRD_BASE = 5
SHORTSTOP = 6
LEFT_FIELD = 7
CENTER_FIELD = 8
RIGHT_FIELD = 9
DESIGNATED_HITTER = 10
PINCH_HITTER = 11
PINCH_RUNNER = 12


class Roster(serialize.DictSerialize):
    """Represent a team roster and state during a baseball game.

    All of the instance variable lists are lists of Retrosheet player IDs.

    Instance variables:
        batting: A list with the batting order for the team. The length is 10 to accommodate
            designated hitter rule. In DH games, batting[9] is the pitcher; in non-DH games,
            it's None.
        fielding: A list of the fielding positions for the team.
        bench: A list of all fielders (non-pitchers) who have not played in the game yet.
        bullpen: A list of all pitchers who have not played in the game yet.
        relieved: A list of all players (fielders or pitchers) who have been relieved
            from the game.
    """
    # Constants for parsing Retrosheet files.
    player_ndx = 1
    team_ndx = 3
    batting_ndx = 4
    fielding_ndx = 5

    unpassed_attributes = ["current_batting_index"]

    def __init__(self, batting=None, fielding=None, bench=None, bullpen=None, relieved=None,
                 home_team=False):
        """Default constructor."""
        self.batting = self._list_default(batting)
        self.fielding = self._list_default(fielding)
        self.bench = self._list_default(bench)
        self.bullpen = self._list_default(bullpen)
        self.relieved = self._list_default(relieved)
        self.home_team = home_team
        # When the home team comes up to bat for the first time, move_to_next_batter will
        # be called before the first batter is assigned. This is an easy workaround.
        self.current_batting_index = 8 if self.home_team else 0

    @staticmethod
    def _list_default(x):
        return [] if x is None else x

    @classmethod
    def from_retrosheet(cls, rows):
        """Constructor from a list of Retrosheet event file rows."""
        batting = [None] * 10
        # Index 0 of fielding is always NULL, the last three positions are for  the
        # designated hitter, pinch hitter, and pinch runner.
        fielding = [None] * 13
        home_team = rows[0][cls.team_ndx] == "1"
        for row in rows:
            player_id = row[cls.player_ndx]
            batting_position = int(row[cls.batting_ndx]) - 1
            fielding_position = int(row[cls.fielding_ndx])
            batting[batting_position] = player_id
            fielding[fielding_position] = player_id
        return cls(batting, fielding, home_team=home_team)

    def current_batter(self):
        """Return the Retrosheet ID of the batter currently at the plate."""
        return self.batting[self.current_batting_index]

    def current_pitcher(self):
        """Return the Retrosheet ID of the pitcher currently on the mound."""
        return self.fielding[PITCHER]

    def move_to_next_batter(self):
        """Update the state of the roster to bring the next batter up to the plate."""
        self.current_batting_index += 1
        self.current_batting_index %= 9

    def substitute(self, sub):
        """"Substitute a new player into the lineup.

        Arguments:
            sub: A Substitution object with the details on the substitution.
        Returns:
            Retrosheet ID of the player that was replaced
        """
        old_player = self.batting[sub.batting]
        # Retrosheet substitution semantics allow for a pinch hitter to sub for himself
        # into a fielding position, which is why this conditional can be false.
        if not sub.player_id == old_player:
            self._substitute_player(sub, old_player)
            self._substitute_batting(sub)
        self._substitute_fielding(sub, old_player)
        return old_player

    def _substitute_player(self, sub, old_player):
        # Add the old player to the list of relieved players.
        self.relieved.append(old_player)
        # Take the new player off of the list of available players.
        if sub.player_id in self.bench:
            self.bench.remove(sub.player_id)
        elif sub.player_id in self.bullpen:
            self.bullpen.remove(sub.player_id)

    def _substitute_batting(self, sub):
        self.batting[sub.batting] = sub.player_id

    def _substitute_fielding(self, sub, old_player):
        # Remove old player from lineup.
        self.fielding = [None if fielder == old_player else fielder
                         for fielder in self.fielding]
        # Put new player into lineup.
        self.fielding[sub.fielding] = sub.player_id
