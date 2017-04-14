from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import datetime
import os
import copy

import bs4


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


class Player(object):
    """Represent a single baseball player.

    This class captures basic demographic information about a player (height, weight,
    birth date, and so on). All information about the player's performance as a baseball
    player is in the Pitcher, Batter, and/or Fielder classes.
    """
    last_name_ndx = 0
    first_name_ndx = 1
    id_ndx = 2
    mlb_debut_ndx = 3

    birth_date_ndx = 1
    physical_ndx = 3
    bats_ndx = 1
    throws_ndx = 3
    height_feet_ndx = 5
    height_inches_ndx = 6
    weight_ndx = 8

    short_date_format = "%m/%d/%Y"
    long_date_format = "%B %d, %Y"
    iso_date_format = "%Y-%m-%d"

    date_attributes = ["mlb_debut", "birth_date"]

    def __init__(self, id_, first_name=None, last_name=None, birth_date=None, mlb_debut=None,
                 bats=None, throws=None, height=None, weight=None):
        """Default constructor."""
        self.id_ = id_
        self.first_name = first_name
        self.last_name = last_name
        self.birth_date = birth_date
        self.mlb_debut = mlb_debut
        self.bats = bats
        self.throws = throws
        self.height = height
        self.weight = weight

    @classmethod
    def from_player_row(cls, row):
        """Constructor from row of the Retrosheet players file.

        Args:
            row: Row from the Retrosheet players file, parsed as a list of strings.
        """
        last_name = row[cls.last_name_ndx]
        first_name = row[cls.first_name_ndx]
        id_ = row[cls.id_ndx]
        mlb_debut = datetime.datetime.strptime(row[cls.mlb_debut_ndx], cls.short_date_format).date()
        return cls(id_=id_, first_name=first_name, last_name=last_name, mlb_debut=mlb_debut)

    @classmethod
    def from_dict(cls, dict_):
        """Constructor from a dictionary representation of the object."""
        dict_ = copy.deepcopy(dict_)
        # Convert string-dates back to dates
        for attribute in cls.date_attributes:
            if attribute in dict_:
                dict_[attribute] = datetime.datetime.strptime(dict_[attribute],
                                                              cls.iso_date_format).date()
        return cls(**dict_)

    def as_dict(self):
        """Return a dictionary representation of the object."""
        dict_ = copy.deepcopy(self.__dict__)
        # Convert dates to strings for serialization.
        for attribute in self.date_attributes:
            if attribute in dict_:
                dict_[attribute] = dict_[attribute].strftime(self.iso_date_format)
        return dict_

    def add_details_from_retrosheet_page(self, page_root="data/retrosheet/players",
                                         page_file=None):
        """Add details about a player from that player's own Retrosheet page.

        Some information (like date of birth and physical characteristics) are only
        accessible in Retrosheet from the player's individual page. This function scrapes
        the page for information we don't already have and adds it to the Player object.

        Args:
            page_file: Filename with the player's HTML Retrosheet page.
            page_root: Root of the directory with Retrosheet player pages.
        """
        if page_file is None:
            page_file = os.path.join(page_root, self.id_ + ".html")
        with open(page_file, "r") as infile:
            page = infile.read()

        source_soup = bs4.BeautifulSoup(page, "lxml")
        source_table = [e.text for e in source_soup.table.find_all("td")]
        self._add_birth_date_from_retrosheet(source_table)
        self._add_physical_attributes_from_retrosheet(source_table)

    def _add_birth_date_from_retrosheet(self, table):
        row = table[self.birth_date_ndx]
        # Remove place of birth
        birth_date_string = ",".join(row.split(",")[:2])
        # Remove leading "Born:"...
        birth_date_string = birth_date_string[5:]
        self.birth_date = datetime.datetime.strptime(birth_date_string,
                                                     self.long_date_format).date()

    def _add_physical_attributes_from_retrosheet(self, table):
        row = table[self.physical_ndx]
        tokens = row.split()
        self.bats = tokens[self.bats_ndx]
        self.throws = tokens[self.throws_ndx]
        height_feet = tokens[self.height_feet_ndx]
        height_inches = tokens[self.height_inches_ndx]
        self.height = 12 * int(height_feet[:-1]) + int(height_inches[:-1])
        self.weight = int(tokens[self.weight_ndx])


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
