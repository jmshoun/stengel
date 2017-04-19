from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import datetime
import os
import copy

import bs4


class PlayerInfo(object):
    """Represent a single baseball player.

    This class captures basic demographic information about a player (height, weight,
    birth date, and so on). All information about the player's performance as a baseball
    player is in the Pitcher, Batter, and/or Fielder classes.
    """
    last_name_ndx = 0
    first_name_ndx = 1
    id_ndx = 2
    mlb_debut_ndx = 3

    bats_ndx = 1
    throws_ndx = 3
    height_feet_ndx = 5
    height_inches_ndx = 6
    weight_ndx = 8

    short_date_format = "%m/%d/%Y"
    long_date_format = "%B %d, %Y"
    iso_date_format = "%Y-%m-%d"

    date_attributes = ["mlb_debut", "mlb_final", "birth_date"]

    def __init__(self, id_, first_name=None, last_name=None, birth_date=None, mlb_debut=None,
                 mlb_final=None, bats=None, throws=None, height=None, weight=None, **kwargs):
        """Default constructor."""
        self.id_ = id_
        self.first_name = first_name
        self.last_name = last_name
        self.birth_date = birth_date
        self.mlb_debut = mlb_debut
        self.mlb_final = mlb_final
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
            if attribute in dict_ and dict_[attribute]:
                dict_[attribute] = datetime.datetime.strptime(dict_[attribute],
                                                              cls.iso_date_format).date()
        return cls(**dict_)

    def as_dict(self):
        """Return a dictionary representation of the object."""
        dict_ = copy.deepcopy(self.__dict__)
        # Convert dates to strings for serialization.
        for attribute in self.date_attributes:
            if attribute in dict_ and dict_[attribute]:
                dict_[attribute] = dict_[attribute].strftime(self.iso_date_format)
        return dict_

    def add_details_from_retrosheet_page(self, page_root="data/retrosheet/players",
                                         page_file=None):
        """Add details about a player from that player's own Retrosheet page.

        Some information (like date of birth and physical characteristics) are only
        accessible in Retrosheet from the player's individual page. This function scrapes
        the page for information we don't already have and adds it to the PlayerInfo object.

        Args:
            page_file: Filename with the player's HTML Retrosheet page.
            page_root: Root of the directory with Retrosheet player pages.
        Returns:
            bool: Whether details were successfully added
        """
        if page_file is None:
            page_file = os.path.join(page_root, self.id_ + ".html")
        if not os.path.exists(page_file):
            return False
        with open(page_file, "r") as infile:
            page = infile.read()

        source_soup = bs4.BeautifulSoup(page, "lxml")
        source_table = [e.text for e in source_soup.table.find_all("td")]
        self._add_birth_date_from_retrosheet(source_table)
        self._add_mlb_final_from_retrosheet(source_table)
        self._add_physical_attributes_from_retrosheet(source_table)
        return True

    def _add_birth_date_from_retrosheet(self, table):
        row = [row for row in table if row[:4] == "Born"][0]
        # Remove place of birth
        birth_date_string = ",".join(row.split(",")[:2])
        # Remove leading "Born:"...
        birth_date_string = birth_date_string[5:]
        self.birth_date = datetime.datetime.strptime(birth_date_string,
                                                     self.long_date_format).date()

    def _add_mlb_final_from_retrosheet(self, table):
        row_search = [row for row in table if row[:10] == "First Game"]
        # Some players don't have a row with first game info
        if not len(row_search):
            return
        row = row_search[0]
        # Format of the row is "First Game: <date>; Final Game: <date>".
        # If there's only one colon, that means the player is still active.
        tokens = row.split(":")
        if len(tokens) == 3:
            mlb_final_string = tokens[2].strip()
            self.mlb_final = datetime.datetime.strptime(mlb_final_string,
                                                        self.long_date_format).date()

    def _add_physical_attributes_from_retrosheet(self, table):
        row = [row for row in table if row[:3] == "Bat"][0]
        tokens = row.split()
        self.bats = tokens[self.bats_ndx]
        self.throws = tokens[self.throws_ndx]
        height_feet = tokens[self.height_feet_ndx]
        height_inches = tokens[self.height_inches_ndx]
        self.height = 12 * int(height_feet[:-1]) + float(height_inches[:-1])
        self.weight = int(tokens[self.weight_ndx])

    # Methods for dynamically calculated attributes

    def age(self, evaluation_date):
        """Return the age (in fractional years) of the player as of a given date.

        I'm defining age (in years) as age (in days) divided by 365.2425. I know that this
        isn't perfect for every application -- for example, a player's age is not
        guaranteed to be an integer on his birthday. However, this is good enough for our
        purposes. Age in days would be fine, and this rescaling of age_in_days makes it
        easier to sanity-check data and interpret model results.
        """
        if not self.birth_date:
            return None
        age_in_days = (evaluation_date - self.birth_date).days
        return age_in_days / 365.2425

    def mlb_tenure(self, evaluation_date):
        """Return the number of (floating-point) years the player has been active in the
        MLB as of a given date.

        See comments on age() about how the units are defined.
        """
        if not self.mlb_debut:
            return None
        tenure_in_days = (evaluation_date - self.mlb_debut).days
        return tenure_in_days / 365.2425


class Players(object):
    """Represent a pool of baseball players.

    This class is intended to represent a group of players -- in practice, likely at least
    all of the players that are active in a league at a given point in time. Players is an
    object instead of a simple dict or list so that new players can be seamlessly inserted on
    an as-needed basis, and so that the player-as-pitcher, player-as-fielder, and
    player-as-batter can remain distinct entities.
    """
    def __init__(self, pitchers=None, batters=None, fielders=None, runners=None):
        """Default constructor."""
        self.pitchers = pitchers if pitchers else {}
        self.batters = batters if batters else {}
        self.fielders = fielders if fielders else {}
        self.runners = runners if runners else {}

    def update(self, event):
        """Update the set of players to reflect a new event.

        Args:
            event: A BoxScoreEvent object.
        """
        if event.pitcher:
            self._update_pitcher(event.pitcher, event)
        if event.batter:
            self._update_batter(event.batter, event)
        if event.runner:
            self._update_runner(event.batter, event)
        if event.fielders:
            self._update_fielders(event.fielders, event)

    def _update_pitcher(self, pitcher, event):
        if pitcher not in self.pitchers:
            self.pitchers[pitcher] = Pitcher(pitcher)
        self.pitchers[pitcher].update(event)

    def _update_batter(self, batter, event):
        if batter not in self.batters:
            self.batters[batter] = Batter(batter)
        self.batters[batter].update(event)

    def _update_runner(self, runner, event):
        if runner not in self.runners:
            self.runners[runner] = Runner(runner)
        self.runners[runner].update(event)

    def _update_fielders(self, fielders, event):
        for fielder in fielders:
            self._update_fielder(fielder, event)

    def _update_fielder(self, fielder, event):
        if fielder not in self.fielders:
            self.fielders[fielder] = Fielder(fielder)
        self.fielders[fielder].update(event)


class PlayerRole(object):
    """Represent the state of one player-role: for example, batter, pitcher, or runner.

    This is a superclass for specific Batter, Pitcher, Fielder, and Runner classes, and
    should rarely be called directly. This handles functionality common to all of the
    subclasses.

    Attributes:
        id_: Retrosheet ID of the player being represented.
        event_counters: Dict where keys are types of events and values are the number of
            times the corresponding event has occurred.
    """
    def __init__(self, id_):
        """Default constructor."""
        self.id_ = id_
        self.event_counters = {}

    def update(self, event):
        """Update the player role to account for a new event.

        If the player role class has specifically defined behavior for that class of event,
        the custom logic is used. Otherwise, fallback logic for generic events is applied.

        Args:
            event: a BoxScoreEvent object.
        """
        event_method = "_update_" + event.name
        if getattr(self, event_method, None):
            getattr(self, event_method)(event)
        else:
            self._update_generic(event)

    def _update_generic(self, event):
        # Implement default behavior: increment or decrement the relevant event counter, as
        # appropriate.
        if event.name not in self.event_counters:
            self.event_counters[event.name] = 0
        delta = -1 if event.decrement else 1
        self.event_counters[event.name] += delta


class Pitcher(PlayerRole):
    """Represent the state of a baseball pitcher."""
    def __init__(self, id_):
        """Default constructor."""
        super(Pitcher, self).__init__(id_)
        self.pitch_count_game = None
        self.pickoff_count_game = None
        self.pitch_count_at_bat = None
        self.pickoff_count_at_bat = None

        # Keep track of the most recent game.
        self.last_game_date = None
        self.days_since_last_game = None
        self.pitches_at_last_game = 0

    def _update_call_pitcher(self, event):
        if self.last_game_date:
            self.pitches_at_last_game = self.pitch_count_game
            self.days_since_last_game = (event.date - self.last_game_date).days
        self.last_game_date = event.date

        self.pitch_count_game = 0
        self.pickoff_count_game = 0
        self.pitch_count_at_bat = 0
        self.pickoff_count_at_bat = 0

    def _update_plate_appearance(self, event):
        if not event.decrement:
            self.pitch_count_at_bat = 0
            self.pickoff_count_at_bat = 0

    def _update_pitch(self, event):
        self.pitch_count_at_bat += 1
        self.pitch_count_game += 1
        self._update_generic(event)

    def _update_pickoff(self, event):
        self.pickoff_count_at_bat += 1
        self.pickoff_count_game += 1
        self._update_generic(event)


class Batter(PlayerRole):
    pass


class Runner(PlayerRole):
    pass


class Fielder(PlayerRole):
    pass
