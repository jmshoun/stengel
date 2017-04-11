from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import datetime


class Players(object):
    """Represent a pool of baseball players.

    This class is intended to represent a group of players -- in practice, likely at least
    all of the players that are active in a league at a given point in time. Players is an
    object instead of a simple dict or list so that new players can be seamlessly inserted on
    an as-needed basis, and so that the player-as-pitcher, player-as-fielder, and
    player-as-batter can remain distinct entities.
    """
    def __init__(self, pitchers=None, batters=None, fielders=None):
        """Default constructor."""
        self.pitchers = pitchers if pitchers else {}
        self.batters = batters if batters else {}
        self.fielders = fielders if fielders else {}

    def update_pitcher(self, pitcher, event, *args):
        """Update a pitcher's status in light of an event.

        Args:
            pitcher: The ID of the pitcher to update.
            event: string: The name of the event to update the pitcher with regard to.
            *args: Any other information about the event.
        """
        if pitcher not in self.pitchers:
            self.pitchers[pitcher] = Pitcher(pitcher)
        getattr(self.pitchers[pitcher], event)(*args)


class Pitcher(object):
    """Represent the state of a baseball pitcher.

    Lots of interesting baseball analysis depends on the internal state of players, and
    pitchers are the most obvious example of this. Knowing how many pitches a pitcher has
    thrown in a game are critical to modeling his effectiveness on the mound. This class
    tracks basic pitcher state over time.
    """
    def __init__(self, id_):
        """Default constructor."""
        self.id_ = id_

        # These -1s are are here to ensure that end-users never see a pitcher's uninitialized state.
        self.pitch_count_game = -1
        self.pickoff_count_game = -1
        self.pitch_count_at_bat = -1
        self.pickoff_count_at_bat = -1
        # Keep track of the most recent game.
        self.last_game_date = datetime.date(1900, 1, 1)
        self.days_since_last_game = None
        self.pitches_at_last_game = None

    def call(self, game_date):
        """Call a pitcher from the bullpen to the mound.

        This method should also be called on starting pitchers at the beginning of the game.
        Args:
            game_date: The date the game takes place.
        """
        # When the first is called, the pitcher initially has the state he did at the end of
        # the previous game.
        game_date = datetime.datetime.strptime(game_date, "%Y/%m/%d").date()
        self.pitches_at_last_game = self.pitch_count_game
        self.days_since_last_game = (game_date - self.last_game_date).days
        # Set up the pitcher with values to reflect the new game.
        self.last_game_date = game_date
        self.pitch_count_game = 0
        self.pickoff_count_game = 0
        self.next_batter()

    def next_batter(self):
        """Update the pitcher when the next batter reaches the plate."""
        self.pitch_count_at_bat = 0
        self.pickoff_count_at_bat = 0

    def pitch(self):
        """Update the pitcher after a pitch."""
        self.pitch_count_at_bat += 1
        self.pitch_count_game += 1

    def pickoff(self):
        """Update the pitcher after a pickoff."""
        self.pickoff_count_at_bat += 1
        self.pickoff_count_game += 1
