from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

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
