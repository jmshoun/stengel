from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import re

from . import bases
from . import serialize


# Enum of the possible strategies for interpreting ambiguous Retrosheet play advances.
NEVER_ADVANCE = 0
OUT_IF_NEW_DESTINATION = 1
ALWAYS_ADVANCE = 2


def running_play_re(pattern):
    """Return a regex that will match a running play (a play with baserunning only, without
    any contact by the batter."""
    running_preamble = r"^(((K(25?3)?)|(I?W))\+)?"
    return re.compile(running_preamble + pattern)


class Play(serialize.DictSerialize):
    """Base class for all plays (batted balls or base running) in a baseball game.

    Instance Variables:
        advances: Advances object representing base running transition.
        fielders: Integer list of fielders who participated in the play, in chronological
            order. Integers correspond to fielding positions in stengel.sim.roster.
        errors: Integer list of fielders who were charged with errors on the play.
    """

    attribute_objects = ["advances"]
    # Dictionary with pattern names as keys and regexes as values. This is what we will
    # use to decide how to parse a Retrosheet play.
    play_patterns = {}

    def __init__(self, advances=None, fielders=None, errors=None):
        """Default constructor."""
        self.event_type = "play"
        self.fielders = self._list_default(fielders)
        self.errors = self._list_default(errors)
        self.advances = Advances() if advances is None else advances

    @staticmethod
    def _list_default(x):
        return [] if x is None else x

    @classmethod
    def from_retrosheet(cls, text, out_on_error=NEVER_ADVANCE):
        """Create a play from a Retrosheet text description."""
        # Find the name of the pattern that the text matches.
        pattern_name = "_retrosheet_no_match"
        for name, pattern in cls.play_patterns.items():
            if re.match(pattern, text):
                pattern_name = name
                break
        # Grab the function that shares a name with the pattern, and use it to parse the
        # contents of the text.
        play = getattr(cls, pattern_name)(text)
        if play:
            play.advances.out_on_error = out_on_error
        return play

    @staticmethod
    def _retrosheet_no_match(text):
        # Default pattern in case the text doesn't match any of the defined patterns.
        return None

    @staticmethod
    def _from_dict_advances(dict_):
        return Advances.from_dict(dict_)


class BattedBall(Play):
    """Represent a play triggered by a batted ball.

    Instance variables:
        hit_location: A HitLocation object representing where the ball was hit.
    """

    attribute_objects = ["advances", "hit_location"]

    play_patterns = {
        "_retrosheet_base_hit": re.compile(r"(S|D|T|(HR?)|(DGR))[1-9]*$"),
        "_retrosheet_base_on_error": re.compile(r"[1-9]*?E[1-9]$"),
        "_retrosheet_foul_ball_error": re.compile(r"FLE[1-9]$"),
        "_retrosheet_base_on_interference": re.compile(r"C$"),
        "_retrosheet_fielders_choice": re.compile(r"FC[1-9]?$"),
        "_retrosheet_force_out": re.compile(r"[1-9]+\([1-3]\)$"),
        "_retrosheet_single_out": re.compile(r"[1-9]+$"),
        "_retrosheet_multiple_out":
            re.compile(r"""([1-9]+\([1-3]\)[1-9])       # Ground into double play
                           |([1-9]+\(B\)([1-9]+\([1-3]\))? # Line into double play
                             ([1-9]+\([1-3]\))?         # Extension for triple play
                            )$""", re.VERBOSE),
    }

    hit_type_ndx = 0
    hit_type_map = {"S": bases.FIRST_BASE,
                    "D": bases.SECOND_BASE,  # also maps to DGR (ground rule double)
                    "T": bases.THIRD_BASE,
                    "H": bases.HOME_PLATE}

    runner = re.compile(r"\([B1-3]\)")
    ground_double_play = re.compile(r"[1-9]+\([1-3]\)[1-9]$")
    fielder = re.compile(r"[1-9]")
    error = re.compile(r"E[1-9]")

    def __init__(self, advances=None, fielders=None, errors=None, hit_location=None,
                 interference=False):
        """Default constructor."""
        super(BattedBall, self).__init__(advances, fielders, errors)
        self.event_type = "batted_ball"
        self.hit_location = hit_location
        self.interference = interference

    # Methods to parse specific Retrosheet patterns.

    @classmethod
    def _retrosheet_base_hit(cls, text):
        batter_advance = cls.hit_type_map[text[cls.hit_type_ndx]]
        fielders = cls._retrosheet_get_fielders(text)
        hit_location = cls._retrosheet_get_hit_location(fielders)
        return cls(fielders=fielders,
                   advances=Advances(batter=batter_advance),
                   hit_location=hit_location)

    @classmethod
    def _retrosheet_base_on_error(cls, text):
        fielders = cls._retrosheet_get_fielders(text)
        errors = cls._retrosheet_get_errors(text)
        hit_location = cls._retrosheet_get_hit_location(fielders)
        return cls(fielders=fielders,
                   errors=errors,
                   advances=Advances(batter=bases.FIRST_BASE),
                   hit_location=hit_location)

    @classmethod
    def _retrosheet_foul_ball_error(cls, text):
        fielder_ndx = 3
        fielders = [int(text[fielder_ndx])]
        return cls(fielders=fielders,
                   errors=fielders,  # Again, we know the fielder has committed an error here
                   advances=Advances(batter=bases.STILL_ACTIVE))

    @classmethod
    def _retrosheet_base_on_interference(cls, text):
        # All we know at this point is that the batter is on first base. We'll fill in
        # the rest of the details later with explicit modifiers.
        return cls(advances=Advances(batter=bases.FIRST_BASE),
                   interference=True)

    @classmethod
    def _retrosheet_fielders_choice(cls, text):
        fielder_ndx = 2
        fielders = [int(text[fielder_ndx])] if len(text) > fielder_ndx else None
        hit_location = cls._retrosheet_get_hit_location(fielders, arc="ground")
        return cls(advances=Advances(batter=bases.FIRST_BASE),
                   fielders=fielders,
                   hit_location=hit_location)

    @classmethod
    def _retrosheet_force_out(cls, text):
        fielders = cls._retrosheet_get_fielders(text)
        runners = cls._retrosheet_get_outs(text)
        hit_location = cls._retrosheet_get_hit_location(fielders, arc="ground")
        return cls(advances=Advances(batter=bases.FIRST_BASE, runners=runners),
                   fielders=fielders,
                   hit_location=hit_location)

    @classmethod
    def _retrosheet_single_out(cls, text):
        fielders = [int(fielder) for fielder in text]
        # A single fielder means that that ball was caught (and therefore probably a fly ball);
        # multiple fielders means that it's an assisted out (and therefore probably a grounder)
        arc = "fly" if len(fielders) == 1 else "ground"
        hit_location = cls._retrosheet_get_hit_location(fielders, arc)
        return cls(fielders=fielders,
                   advances=Advances(batter=bases.OUT),
                   hit_location=hit_location)

    @classmethod
    def _retrosheet_multiple_out(cls, text):
        fielders = cls._retrosheet_get_fielders(text)
        runners = cls._retrosheet_get_outs(text)
        arc = "ground" if re.match(cls.ground_double_play, text) else "line"
        hit_location = cls._retrosheet_get_hit_location(fielders, arc)
        batter_out = ("B" in text) or (text[-1] != ")")
        batter = bases.OUT if batter_out else bases.FIRST_BASE
        return cls(advances=Advances(batter=batter, runners=runners),
                   fielders=fielders,
                   hit_location=hit_location)

    # All methods that follow are support methods used by the patterns above.

    @classmethod
    def _retrosheet_get_fielders(cls, text):
        # Remove text with details on baserunners
        fielders = re.sub(cls.runner, "", text)
        return [int(fielder) for fielder in re.findall(cls.fielder, fielders)]

    @classmethod
    def _retrosheet_get_errors(cls, text):
        return [int(fielder[1]) for fielder in re.findall(cls.error, text)]

    @classmethod
    def _retrosheet_get_hit_location(cls, fielders, arc=None):
        if not fielders:
            return None
        location = str(fielders[0])
        return HitLocation.from_retrosheet(location=location, arc=arc)

    @classmethod
    def _retrosheet_get_outs(cls, text):
        base_ndx = 1
        runners = [None] * 3
        runners_text = re.findall(cls.runner, text)
        for runner_text in runners_text:
            base_text = runner_text[base_ndx]
            if base_text in "123":
                base_id = int(base_text) - 1
                runners[base_id] = bases.OUT
        return runners

    @staticmethod
    def _from_dict_hit_location(dict_):
        return HitLocation.from_dict(dict_)


class BaseRunning(Play):
    """Represent a play triggered by a base running event."""

    play_patterns = {
        "_retrosheet_base_running": running_play_re(r"((DI)|(OA)|(PB)|(WP))$"),
        "_retrosheet_caught_stealing": running_play_re(r"(PO)?CS[23H]\((E?[1-9](/TH)?)+\)(\(UR\))?$"),
        "_retrosheet_picked_off": running_play_re(r"PO[1-3]\((E?[1-9](/TH)?)+\)$"),
        "_retrosheet_stolen_base": running_play_re(r"SB[23H](\(UR\))?(;SB[23H])*$")
    }

    stolen_base_starts = {"2": bases.FIRST_BASE, "3": bases.SECOND_BASE, "H": bases.THIRD_BASE}

    steal_fielders = re.compile(r"\((E?[1-9](/TH)?)+\)")
    steal_fielder = re.compile(r"E?[1-9]")
    base = re.compile(r"[1-3H]")
    preamble = running_play_re("")

    target_ndx = 2
    fielder_ndx = -1
    error_ndx = 0

    def __init__(self, advances=None, fielders=None, errors=None):
        super(BaseRunning, self).__init__(advances, fielders, errors)
        self.event_type = "base_running"

    # Methods to parse specific Retrosheet patterns.

    @classmethod
    def _retrosheet_base_running(cls, text):
        # This is the generic method that gets called whenever an unusual base running
        # event (like defensive indifference) is found, where all of the details will be
        # given explicitly by modifiers.
        return cls(advances=Advances(batter=bases.STILL_ACTIVE))

    @classmethod
    def _retrosheet_caught_stealing(cls, text):
        text = re.sub(cls.preamble, "", text)
        fielders, errors = cls._retrosheet_get_steal_fielders(text)
        runners = [None] * 3

        steal_runner = cls._retrosheet_get_steal_runner(text)
        if not errors:
            runners[steal_runner] = bases.OUT
        else:
            runners[steal_runner] = steal_runner + 1
        return cls(advances=Advances(batter=bases.STILL_ACTIVE, runners=runners),
                   fielders=fielders,
                   errors=errors)

    @classmethod
    def _retrosheet_picked_off(cls, text):
        # The big difference between this and *caught_stealing is that *caught_stealing
        # references batters by the base they were headed to, while *picked_off references
        # batters by the base they were starting from.
        text = re.sub(cls.preamble, "", text)
        fielders, errors = cls._retrosheet_get_steal_fielders(text)
        runners = [None] * 3
        if not errors:
            steal_runner_text = re.findall(cls.base, text)[0]
            steal_runner = int(steal_runner_text) - 1
            runners[steal_runner] = bases.OUT
        return cls(advances=Advances(batter=bases.STILL_ACTIVE, runners=runners),
                   fielders=fielders,
                   errors=errors)

    @classmethod
    def _retrosheet_stolen_base(cls, text):
        text = re.sub(cls.preamble, "", text)
        runners = [None] * 3
        stolen_bases = text.split(";")
        for stolen_base in stolen_bases:
            runner = cls._retrosheet_parse_single_stolen_base(stolen_base)
            runners[runner] = runner + 1
        return cls(advances=Advances(batter=bases.STILL_ACTIVE, runners=runners))

    # All the methods that follow are support methods for the patterns above.

    @classmethod
    def _retrosheet_get_steal_fielders(cls, text):
        fielders_text = cls._retrosheet_split_steal_fielders(text)
        fielders, errors = [], []
        for fielder_text in fielders_text:
            fielder = int(fielder_text[cls.fielder_ndx])
            fielders.append(fielder)
            if fielder_text[cls.error_ndx] == "E":
                errors.append(fielder)
        if not errors:
            errors = None
        return fielders, errors

    @classmethod
    def _retrosheet_split_steal_fielders(cls, text):
        fielders_text = cls.steal_fielders.search(text).group()
        return re.findall(cls.steal_fielder, fielders_text)

    @classmethod
    def _retrosheet_get_steal_runner(cls, text):
        target_base = re.findall(cls.base, text)[0]
        return cls.stolen_base_starts[target_base]

    @classmethod
    def _retrosheet_parse_single_stolen_base(cls, base_text):
        return cls.stolen_base_starts[base_text[cls.target_ndx]]


class HitLocation(serialize.DictSerialize):
    """Represent the place where a ball was hit.

    Instance variables:
        angle: Angle of the ball's path. To center field is 0, right is positive.
        depth: The depth of the ball's path. 0 is at home plate; larger numbers are
            farther away.
        arc: The vertical trajectory of the ball. Larger numbers are higher flight.
        bunt: Whether the hit was a bunt.
    """

    arc_map = {"P": 2, "F": 1, "fly": 1, "L": 0, "line": 0, "G": -1, "ground": -1}
    location_map = {2: [0, 0], 25: [-1, 1], 23: [1, 1], 1: [0, 2], 15: [-1, 2], 13: [1, 2],
                    5: [-3, 4], 56: [-2, 4], 6: [-1, 4], 4: [1, 4], 34: [2, 4], 3: [3, 4], 46: [0, 4],
                    7: [-2, 7], 78: [-1, 7], 8: [0, 7], 89: [1, 7], 9: [2, 7], 0: [0, 0]}
    modifier_map = {"S": [0, -1], "D": [0, 1], "XD": [0, 2],
                    "M": [-0.5, 0], "L": [1, 0], "": [0, 0],
                    "LS": [1, -1], "LD": [1, 1], "LXD": [1, 2], "MD": [-0.5, 1]}

    location = re.compile(r"[1-9]+")
    arc_modifier = re.compile(r"[+-]")

    def __init__(self, angle=0, depth=0, arc=None, bunt=False):
        """Default constructor."""
        self.angle = angle
        self.depth = depth
        self.arc = arc
        self.bunt = bunt

    @classmethod
    def from_retrosheet(cls, location="0", modifier="", arc=None, bunt=False):
        """Constructor from a Retrosheet event description."""
        angle, depth = cls.location_map[int(location)]
        modifier = cls.modifier_map[modifier]
        if angle < 0:
            modifier[0] *= -1
        angle, depth = angle + modifier[0], depth + modifier[1]
        arc = None if arc is None else cls.arc_map[arc]
        return cls(angle=angle, depth=depth, arc=arc, bunt=bunt)

    @classmethod
    def from_retrosheet_modifier(cls, text):
        """Constructor from a Retrosheet play description modifier."""
        text = re.sub(cls.arc_modifier, "", text)
        text, bunt = cls._parse_bunt(text)
        text, arc = cls._parse_arc(text)
        text, location = cls._parse_location(text)
        modifier = cls._parse_modifier(text)
        return cls.from_retrosheet(location=location, modifier=modifier, arc=arc, bunt=bunt)

    def add_retrosheet_arc(self, arc):
        """Add arc information to hit location from a Retrosheet modifier."""
        if arc[0] == "B":
            self.bunt = True
            arc = arc[1:]
        self.arc = self.arc_map[arc[0]]

    @classmethod
    def _parse_bunt(cls, text):
        bunt = (text[0] == "B")
        if bunt:
            text = text[1:]
        return text, bunt

    @classmethod
    def _parse_arc(cls, text):
        return text[1:], text[0]

    @classmethod
    def _parse_location(cls, text):
        location = re.findall(cls.location, text)[0]
        text = re.sub(cls.location, "", text)
        return text, location

    @classmethod
    def _parse_modifier(cls, text):
        # If there's a trailing F, it means the ball landed foul, but we don't care
        if len(text) and text[-1] == "F":
            text = text[:-1]
        return text


class Advances(serialize.DictSerialize):
    """Represent the base advances on a hit or base running play.

    Instance variables:
        batter: Integer destination of the batter.
        runners: 3-vector of integers listed destinations of runners at first, second,
            and third base, respectively.
        out_on_error: The strategy to use when handling ambiguous situations in Retrosheet
            advance descriptions. If the advance contains an error modifier, the correct
            interpretation isn't consistent, but some possibilities are:
                NEVER_ADVANCE: If the batter is marked out, the batter is out.
                OUT_IF_NEW_DESTINATION: If the batter is marked out, the batter is out only if
                    the ending base isn't the starting base -- i.e., 2X2 is safe, 2X3 is out.
                ALWAYS_ADVANCE: If the batter is marked out, he still advances.
    """
    runner_ndx = 0
    success_ndx = 1
    destination_ndx = 2

    destination_map = {"1": bases.FIRST_BASE,
                       "2": bases.SECOND_BASE,
                       "3": bases.THIRD_BASE,
                       "H": bases.HOME_PLATE}

    run_marker = re.compile(r"\([NU]R\)")

    unpassed_attributes = ["event_type", "out_on_error"]

    def __init__(self, batter=None, runners=None, out_on_error=NEVER_ADVANCE):
        """Default constructor."""
        self.batter = batter
        self.runners = [None] * 3 if runners is None else runners
        self.out_on_error = out_on_error

    def add_retrosheet_advances(self, text):
        """Take the advance information from a play and use it to update self."""
        advances = text.split(";")
        for advance in advances:
            self._retrosheet_parse_advance(advance)

    def _retrosheet_parse_advance(self, advance):
        player = advance[self.runner_ndx]
        if player == "B":
            self._parse_batter_advance(advance)
        else:
            self._parse_runner_advance(advance)

    def _parse_batter_advance(self, advance):
        self.batter = self._parse_advance_destination(advance, self.batter)

    def _parse_runner_advance(self, advance):
        runner = int(advance[self.runner_ndx]) - 1
        self.runners[runner] = self._parse_advance_destination(advance)

    def _parse_advance_destination(self, advance, current_destination=None):
        destination = self.destination_map[advance[self.destination_ndx]]
        is_new_destination = (current_destination not in [None, bases.STILL_ACTIVE, bases.OUT]
                              and destination != current_destination)
        known_run = re.search(self.run_marker, advance)

        if self.out_on_error == NEVER_ADVANCE:
            error_advance = known_run
        elif self.out_on_error == OUT_IF_NEW_DESTINATION:
            error_advance = known_run or ("E" in advance and not is_new_destination)
        else:
            error_advance = known_run or ("E" in advance)

        if advance[self.success_ndx] == "X" and not error_advance:
            return bases.OUT
        return destination


class GameCalled(serialize.DictSerialize):
    """Special event to represent when a game was called early by an umpire."""
    comment_ndx = 1

    def __init__(self):
        """Default constructor."""
        self.event_type = "game_called"

    @classmethod
    def from_retrosheet(cls, row):
        """Constructor from a Retrosheet row."""
        comment = row[cls.comment_ndx].lower()
        if "called" in comment or "stopped" in comment or " ended" in comment:
            return cls()
        else:
            return None
