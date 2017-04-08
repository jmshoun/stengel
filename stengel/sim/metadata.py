from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import datetime
import re

from . import serialize


class GameMetadata(serialize.DictSerialize):
    """Metadata associated with a baseball game.

    This class stores information about the game that doesn't have anything to do with the
    outcome of the game itself: for for example, the game ID, date, starting time, umpires,
    ambient conditions, and attendance. We consider information like whether a designated
    hitter was used, the identities of the two teams, and so forth to be metadata as well.

    The full list of metadata attributes is the set of values in the class-level variable_map
    variable.
    """
    # A map of variable names. The keys are names of variables as spelled in Retrosheet
    # event files, and the values are names of variables as spelled inside the class.
    variable_map = {"hometeam": "home_team", "visteam": "away_team", "site": "location",
                    "date": "game_date", "number": "game_number", "starttime": "start_time",
                    "usedh": "use_designated_hitter", "umphome": "home_plate_umpire",
                    "ump1b": "first_base_umpire", "ump2b": "second_base_umpire",
                    "ump3b": "third_base_umpire", "temp": "temperature",
                    "winddir": "wind_direction", "windspeed": "wind_speed",
                    "fieldcond": "field_condition", "precip": "precipitation",
                    "sky": "sky_condition", "attendance": "attendance", None: "id_"}
    # Variables that should be coerced to integers when reading from Retrosheet.
    integer_variables = ["game_number", "wind_speed", "temperature", "attendance"]
    # Variables that should be coerced to booleans when reading from Retrosheet.
    boolean_variables = ["use_designated_hitter"]

    # Regex to find integer values
    integer_re = re.compile(r"[0-9]+")

    # Commonly used indices
    name_ndx = 1
    value_ndx = 2
    id_ndx = 1

    def __init__(self, **kwargs):
        """Construct from a set of named arguments."""
        for name in self.variable_map.values():
            value = kwargs.get(name)
            setattr(self, name, value)
        # Convert time objects from strings.
        if self.start_time:
            self.start_time = datetime.datetime.strptime(self.start_time, "%I:%M%p").time()

    @classmethod
    def from_retrosheet(cls, rows):
        """Construct from a list of Retrosheet event file rows."""
        metadata_dict = {cls.variable_map[row[cls.name_ndx]]: row[cls.value_ndx] for row in rows
                         if row[cls.name_ndx] in cls.variable_map.keys()}
        # We know that the id row is always the first row in a Retrosheet event file.
        metadata_dict["id_"] = rows[0][cls.id_ndx]

        # Convert variables from strings to native types.
        for k in metadata_dict.keys():
            if k in cls.integer_variables:
                metadata_dict[k] = int(re.findall(cls.integer_re, metadata_dict[k])[0])
            elif k in cls.boolean_variables:
                metadata_dict[k] = bool(metadata_dict[k])
        return cls(**metadata_dict)

    def year_month_day(self):
        """Return the year, month, and day (as integers) of the date the game was played."""
        # game_date is YYYY-MM-DD.
        year = self.game_date[0:4]
        month = self.game_date[5:7]
        day = self.game_date[8:10]
        return year, month, day

    def gameday_id(self):
        """Get the MLB GameDay ID of the game."""
        year, month, day = self.year_month_day()
        away = self.away_team.lower() + "mlb"
        home = self.home_team.lower() + "mlb"
        game_number = str(self.game_number) if self.game_number > 0 else "1"
        return "_".join(["gid", year, month, day, away, home, game_number])

    def gameday_url(self):
        """Get the root URL containing MLB GameDay data for the game."""
        year, month, day = self.year_month_day()
        base_url = "http://gd2.mlb.com/components/game/mlb/"
        date_folder = "year_{}/month_{}/day_{}/".format(year, month, day)
        return base_url + date_folder + self.gameday_id()

    def as_dict(self):
        """Return a representation of self as a dictionary."""
        metadata_dict = super(GameMetadata, self).as_dict()
        # Convert the start time back to a string if necessary.
        if self.start_time:
            metadata_dict["start_time"] = self.start_time.strftime("%I:%M%p")
        return metadata_dict
