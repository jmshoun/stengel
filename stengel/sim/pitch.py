from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import xml.etree.ElementTree as ET

from . import serialize
from . import bases


class Pitch(serialize.DictSerialize):
    """Represent a single action by the pitcher.

    The set of actions that a pitcher can take is more broad than just throwing a pitch
    over the plate: for example, the pitcher could also throw a pickoff, or balk. For the
    sake of expediency, we'll consider all of these actions "pitches", even if some of
    them aren't pitches in the truest sense of the word. We'll also consider pickoffs
    thrown by the catcher as pitches, even though the pitcher isn't even the one
    throwing.

    Instance variables:
        pitch_event: A human-readable summary of the pitch (i.e., ball, strike.)
        threw: Whether the ball was actually thrown. Can be false for called balls when
            the pitcher goes to his mouth, or for balks.
        swung: Whether the batter swung at the pitch.
        bunted: Whether the batter's swing was a bunt.
        ran_on_play: Whether a runner on base was going on the play.
        blocked: Whether the pitch was blocked by the catcher.
        thrown_by_catcher: Whether the pitch was thrown by the catcher.
        intentional: If the pitch was a ball, whether the ball was deemed intentional.
        destination: The base the pitch was thrown to. Will be bases.HOME_PLATE for
            normal pitches; other values represent pickoffs.
        play_on_pitch: Whether there was a play on the pitch. Necessarily true if the
            pitch_event is "contact", but could be true for base running plays.
        pitch_fx: PitchFX data on the pitch.
    """
    modifier_ndx = 0
    pitch_ndx = -1

    attribute_objects = ["pitch_fx"]

    def __init__(self, pitch_event, threw=True, swung=False, bunted=False, ran_on_play=False,
                 blocked=False, pitchout=False, thrown_by_catcher=False, intentional=False,
                 destination=bases.HOME_PLATE, play_on_pitch=False, pitch_fx=None):
        """Default constructor."""
        self.event_type = "pitch"
        self.pitch_event = pitch_event
        self.threw = threw
        self.swung = swung
        self.bunted = bunted
        self.ran_on_play = ran_on_play
        self.blocked = blocked
        self.pitchout = pitchout
        self.thrown_by_catcher = thrown_by_catcher
        self.intentional = intentional
        self.destination = destination
        self.play_on_pitch = play_on_pitch
        self.pitch_fx = pitch_fx

    @classmethod
    def from_retrosheet(cls, pitch):
        """Constructor from Retrosheet event file representation.

        Retrosheet represents pitches as one- or two-character strings. If the string is
        two characters, the first character is a modifier (such as if if the pitch was
        blocked, or if there was a run on the play. The last character is always a
        basic descriptor of the pitch.
        """

        pitch_event = cls._retrosheet_pitch_event(pitch[cls.pitch_ndx])
        threw = pitch[cls.pitch_ndx] != "V"
        swung = pitch[cls.pitch_ndx] in "FKLMOQRSTX"
        bunted = pitch[cls.pitch_ndx] in "LMO"
        pitchout = pitch[cls.pitch_ndx] in "PQRY"
        ran_on_play = pitch[cls.modifier_ndx] == ">"
        blocked = pitch[cls.modifier_ndx] == "*"
        thrown_by_catcher = pitch[cls.modifier_ndx] == "+"
        intentional = pitch[cls.pitch_ndx] == "I"
        destination = cls._retrosheet_destination(pitch[cls.pitch_ndx])
        return cls(pitch_event, threw=threw, swung=swung, bunted=bunted, pitchout=pitchout,
                   ran_on_play=ran_on_play, blocked=blocked, thrown_by_catcher=thrown_by_catcher,
                   intentional=intentional, destination=destination)

    @staticmethod
    def _retrosheet_pitch_event(pitch):
        """Convert a Retrosheet pitch descriptor character to a pitch event."""
        if pitch in "BIPV":
            return "ball"
        elif pitch in "CKMOQST":
            return "strike"
        elif pitch == "L":
            return "foul_bunt"
        elif pitch in "FR":
            return "foul"
        elif pitch in "H":
            return "hit_by_pitch"
        elif pitch in "X":
            return "contact"
        elif pitch in "123":
            return "pickoff"
        raise Exception("Unexpected pitch type: {}".format(pitch))

    @staticmethod
    def _retrosheet_destination(pitch):
        if pitch in "123":
            return int(pitch) - 1
        else:
            return bases.HOME_PLATE

    def type(self):
        """Get a simplified Retrosheet-style description of the pitch.

        Useful for debugging, monitoring, zipping, and other situations where a concise,
        simplified representation of the pitch is very useful.

        Returns:
            A single character with a Retrosheet-style description of the pitch. Not guaranteed
            to be the same as the actual Retrosheet representation of the pitch -- for example,
            modifiers and foul tips are completely ignored.
        """
        if self.pitchout:
            return "Q" if self.swung else "P"
        elif self.pitch_event == "foul_bunt":
            return "L"
        elif self.pitch_event == "foul":
            return "F"
        elif self.pitch_event == "ball":
            return "B"
        elif self.pitch_event == "hit_by_pitch":
            return "H"
        elif self.pitch_event == "contact":
            return "X"
        elif self.pitch_event == "strike":
            if self.bunted:
                return "M"
            return "S" if self.swung else "C"
        else:
            return "?"

    def is_over_plate(self):
        """Returns if the pitch was actually thrown over the plate."""
        return self.destination == bases.HOME_PLATE and self.pitch_event != "balk"

    @staticmethod
    def _from_dict_pitch_fx(dict_):
        return PitchFx(**dict_)


class Balk(Pitch):
    """Represent a balk by the pitcher.

    Annoyingly, balks are coded in Retrosheet as plays instead of pitches, so we're
    deriving this subclass of Pitch just for the constructor.
    """
    def __init__(self):
        """Default constructor."""
        super(Balk, self).__init__("balk", threw=False)


class PitchFx(serialize.DictSerialize):
    """Represents the PitchFx data associated with a pitch.

    PitchFx data consists of ~20 numeric attributes that describe characteristics of a pitch
    thrown in a game. Most of the PitchFx system variables are retained here, but there are
    a couple of exceptions. Zone is dropped, because documentation on what it represents is
    a little sparse. Pitch_type and type_confidence are also dropped because pitch type
    inference will be handled internally.
    """
    # Map of variable names. Keys are GameDay PitchFX attribute names; values are Stengel
    # attribute names.
    variable_map = {"start_speed": "start_speed", "end_speed": "end_speed",
                    "sz_top": "strike_zone_top", "sz_bot": "strike_zone_bottom",
                    "pfx_x": "delta_x", "pfx_z": "delta_z",
                    "px": "plate_x", "pz": "plate_z",
                    "x0": "start_x", "y0": "start_y", "z0": "start_z",
                    "vx0": "velocity_x", "vy0": "velocity_y", "vz0": "velocity_z",
                    "ax": "accel_x", "ay": "accel_y", "az": "accel_z",
                    "break_y": "break_y", "break_angle": "break_angle",
                    "break_length": "break_length", "spin_dir": "spin_direction",
                    "spin_rate": "spin_rate"}

    def __init__(self, **kwargs):
        """Default constructor."""
        for name in self.variable_map.values():
            value = kwargs.get(name)
            setattr(self, name, value)

    @classmethod
    def from_gameday(cls, element):
        """Constructor from a pitch element for a GameDay XML parse tree."""
        xml_dict = element.attrib
        attribute_dict = {}
        for xml_name, attribute_name in cls.variable_map.items():
            if xml_name in xml_dict:
                attribute_dict[attribute_name] = float(xml_dict[xml_name])
        return cls(**attribute_dict)


class ZipPitches(object):
    """Harmonize the pitches in a baseball game according according to Retrosheet and GameDay.

    There can be significant differences between the two data sources about what the exact
    sequence of pitches thrown was, so combining the data sources is definitely non-trivial.
    This class uses a few best-guess heuristics to harmonize the two sources. In general,
    Retrosheet is given more credence, so there may be some pitches for which PitchFx data
    from GameDay is missing.
    """
    def __init__(self, pitches_by_batter, pitch_elements_by_batter):
        """Default constructor.

        Args:
            pitches_by_batter: A list of lists of Pitch objects derived from Retrosheet;
                each sub-list corresponds to a single at-bat.
            pitch_elements_by_batter: A list of lists of pitch XML elements from GameDay;
                each sub-list corresponds to a single at-bat.
        """
        self.pitches_by_batter = pitches_by_batter
        self.pitch_elements_by_batter = pitch_elements_by_batter
        self._update_counts()

    def zip(self):
        """Zip together the pitches from the two sources.

        Returns:
            A list of Pitch objects, (almost) all of which have PitchFx data attached."""
        self.match_at_bats()
        clean_pitches = []
        for pitches, elements in zip(self.pitches_by_batter, self.pitch_elements_by_batter):
            clean_pitches += ZipPlateAppearance(pitches, elements).zip()
        return clean_pitches

    def match_at_bats(self):
        """Ensure that both data sources agree about the number of at-bats in the game."""
        at_bat_count_delta = len(self.pitch_counts) - len(self.element_counts)
        if at_bat_count_delta >= 1:
            while at_bat_count_delta > 0:
                self._fix_pitch_elements()
                at_bat_count_delta = len(self.pitch_counts) - len(self.element_counts)
        elif at_bat_count_delta <= -1:
            # Occasionally, there will be more GameDay elements. This is always because of
            # an ejection at the end of the game.
            self.pitch_elements_by_batter = self.pitch_elements_by_batter[:len(self.pitch_counts)]
            self._update_counts()

    def _fix_pitch_elements(self):
        # If pitch elements is missing the last plate appearance, add a blank
        if self.pitch_counts[:-1] == self.element_counts:
            self.pitch_elements_by_batter.append([])
        else:
            mismatch_ndx = self._find_mismatch_index()
            if (self.element_counts[mismatch_ndx] ==
                    sum(self.pitch_counts[mismatch_ndx:(mismatch_ndx + 2)])):
                # If Retrosheet splits two separate batters who are part of the same plate
                # appearance, combine them.
                self.pitches_by_batter[mismatch_ndx] += self.pitches_by_batter.pop(mismatch_ndx + 1)
            else:
                # Otherwise, stick in a dummy record for a plate appearance that's missing
                # in the GameDay data.
                self.pitch_elements_by_batter.insert(mismatch_ndx, [])
        self._update_counts()

    def _find_mismatch_index(self):
        ndx = 0
        while self.pitch_counts[ndx] == self.element_counts[ndx]:
            ndx += 1
        return ndx

    def _update_counts(self):
        self.pitch_counts = [len(p) for p in self.pitches_by_batter]
        self.element_counts = [len(p) for p in self.pitch_elements_by_batter]


class ZipPlateAppearance(object):
    """Combine Retrosheet and PitchFx data from a single plate appearance."""

    # Map of GameDay pitch descriptions to Retrosheet-style pitch codes.
    element_type_map = {"Ball": "B", "Foul (Runner Going)": "F", "Pitchout": "P",
                        "In play, out(s)": "X", "Intent Ball": "B", "Automatic Ball": "B",
                        "In play, run(s)": "X", "Foul": "F", "Automatic Strike": "C",
                        "Foul Tip": "S", "Swinging Strike": "S", "Called Strike": "C",
                        "Foul Bunt": "L", "Swinging Pitchout": "Q", "Hit By Pitch": "H",
                        "Ball In Dirt": "B", "Swinging Strike (Blocked)": "S",
                        "Missed Bunt": "M", "In play, no out": "X"}

    def __init__(self, pitches, pitch_elements):
        """Default constructor.

        Args:
            pitches: List of Pitch objects derived from Retrosheet for a single plate appearance.
            pitch_elements: List of GameDay pitch XML elements for a single plate appearance.
        """
        self.pitches = pitches
        self.pitch_elements = pitch_elements
        self.pitch_fx = [PitchFx.from_gameday(e) for e in self.pitch_elements]
        # We want to track whether any pitches were inserted in the zipping process.
        for pitch in self.pitches:
            pitch.inserted = False

    def zip(self):
        """Combine the information from the two data sources.

        Returns:
            A list of Pitch objects with PitchFx data attached wherever possible.
        """
        if len(self.pitches) != len(self.pitch_fx):
            self.balance_pitches()
        for pitch, pitch_fx in zip(self.pitches, self.pitch_fx):
            pitch.pitch_fx = pitch_fx
        return self.pitches

    def balance_pitches(self):
        """Harmonize the list of pitches thrown at the at-bat between the two data sources."""
        pitch_count_delta = len(self.pitches) - len(self.pitch_fx)
        if abs(pitch_count_delta) == 1 and len(self.pitch_fx) > 0:
            self._add_missing_pitch()
        else:
            self._fill_in_pitch_fx()

    def _fill_in_pitch_fx(self):
        self.pitch_fx = [PitchFx() for p in self.pitches]

    def _add_missing_pitch(self):
        try:
            insert_ndx, insert_pitch_type = self._find_missing_pitch()
            self._insert_missing_pitch(insert_ndx, insert_pitch_type)
        except PitchZipException:
            self._fill_in_pitch_fx()

    def _find_missing_pitch(self):
        long_summary, short_summary = self._get_pitch_summaries()
        # Find the index of the first mismatch and assume it's missing the element from
        # the long summary.
        ndx = 0
        while ndx < len(short_summary) and long_summary[ndx] == short_summary[ndx]:
            ndx += 1
        # Verify that the rest of the sequence matches.
        for i in range(len(long_summary) - 1, ndx, -1):
            if long_summary[i] != short_summary[i - 1]:
                raise PitchZipException("Plate appearance with multiple disagreements.")
        return ndx, long_summary[ndx]

    def _get_pitch_summaries(self):
        element_summary = [self._summarize_element(e) for e in self.pitch_elements]
        pitch_summary = [p.type() for p in self.pitches]
        if len(pitch_summary) > len(element_summary):
            return pitch_summary, element_summary
        else:
            return element_summary, pitch_summary

    def _insert_missing_pitch(self, insert_ndx, insert_pitch_type):
        if len(self.pitches) > len(self.pitch_elements):
            self.pitch_fx.insert(insert_ndx, PitchFx())
        else:
            self.pitches.insert(insert_ndx, Pitch.from_retrosheet(insert_pitch_type))
            self.pitches[insert_ndx].inserted = True

    def _summarize_element(self, element):
        element_type = element.attrib["des"]
        return self.element_type_map[element_type]


class PitchZipException(Exception):
    pass
