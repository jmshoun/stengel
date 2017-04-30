import csv
import re
import copy

from ..sim import game
from ..sim import pitch
from ..sim import roster
from ..sim import sub
from ..sim import play
from ..sim import metadata


class RetrosheetGameFileParser(object):
    """Parse a complete Retrosheet event file, which consists of multiple game records."""

    def __init__(self, filename, error_on_failure=True):
        """Default constructor.

        Args:
            filename: Name of Retrosheet event file to parse games from.
            error_on_failure: Whether to throw an error if any game fails to parse correctly.
        """
        self.games = []
        self.parsed_games = []
        self.error_on_failure = error_on_failure
        with open(filename, "r") as infile:
            game_reader = csv.reader(infile)
            self._split_games(game_reader)

    def _split_games(self, game_reader):
        # Split the full event file into its constituent games.
        current_game = []
        for row in game_reader:
            # A new game will always start with an id record
            if row[0] == "id":
                self._add_game(current_game)
                current_game = [row]
            else:
                current_game.append(row)
        self._add_game(current_game)    # Add the last game in the file

    def _add_game(self, current_game):
        # current_game will be [] on the first call to this function, thus the conditional.
        if current_game:
            self.games.append(current_game)

    def parse(self):
        """Parse each individual game in the event file."""
        self.parsed_games = [RetrosheetGameParser(g, self.error_on_failure).parse()
                             for g in self.games]

    def upload(self, database):
        """Upload each game from the event file to the supplied database."""
        database.games.insert_many([g.as_dict() for g in self.parsed_games])


class RetrosheetGameParser(object):
    """Parse a single game as represented in a Retrosheet event file."""

    # Keys are Retrosheet row types, values are row types as classified by the parser.
    row_type_map = {"id": "metadata_rows", "info": "metadata_rows", "start": "roster_rows",
                    "play": "event_rows", "sub": "event_rows", "badj": "event_rows",
                    "padj": "event_rows", "com": "event_rows"}

    row_type_ndx = 0
    team_ndx = 3

    def __init__(self, rows, error_on_failure=True):
        """Default constructor.

        Args:
            rows: Rows from the Retrosheet event file describing a single game.
            error_on_failure: Whether to raise an error if the game fails to parse correctly.
        """
        self.error_on_failure = error_on_failure
        self.metadata_rows = []
        self.roster_rows = []
        self.event_rows = []
        self._partition_rows(rows)

    def _partition_rows(self, rows):
        """Partition all of the input rows by type.

        This will append every row to one of self.metadata_rows, self.roster_rows, or
        self.event_rows, as applicable.
        """
        for row in rows:
            row_type = self.row_type_map.get(row[self.row_type_ndx])
            if row_type:
                getattr(self, row_type).append(row)

    def parse(self):
        """Parse a complete game."""
        # The semantics around advances in Retrosheet advances are not always consistent --
        # there is often no unique way to determine how to interpret a set of advances
        # without considering broader context. The good news is that an incorrect
        # interpretation of an advance record will lead to a wrong count of outs, which will
        # always lead to a wrong conclusion about when the game ends. Therefore, our strategy
        # is to try each type of advance semantics in turn on a game, and accept the first
        # set of semantics that yields the right conclusion about when the game is over.
        for advance_type in [play.OUT_IF_NEW_DESTINATION, play.ALWAYS_ADVANCE, play.NEVER_ADVANCE]:
            parsed_game = self._attempt_parse_game(advance_type)
            verified = parsed_game.verify_ending()
            if verified:
                break

        if not verified and self.error_on_failure:
            raise Exception("Game parsing failed: " + parsed_game.metadata.id_)
        return parsed_game

    def _attempt_parse_game(self, advance_type):
        parsed_metadata = metadata.GameMetadata.from_retrosheet(self.metadata_rows)
        rosters = self._parse_rosters()
        events = RetrosheetEventParser(self.event_rows, out_on_error=advance_type).parse()
        return game.Game(metadata_=parsed_metadata, rosters=rosters, events=events)

    def _parse_rosters(self):
        # Split rosters into home and away.
        split_roster_rows = {"home": [], "away": []}
        for row in self.roster_rows:
            team = "home" if row[self.team_ndx] == "1" else "away"
            split_roster_rows[team].append(row)
        # Parse each roster separately.
        return {k: roster.Roster.from_retrosheet(v) for k, v in split_roster_rows.items()}


class RetrosheetEventParser(object):
    """Parse a full set of event rows from a Retrosheet game file.

    Unfortunately, the way Retrosheet event files are set up, they require quite a bit of
    pre-processing before they can be parsed in a state-independent way. Most of this class
    is getting rid of state dependence.
    """

    # Index constants for parsing Retrosheet event records.
    event_type_ndx = 0
    batter_ndx = 3
    pitches_ndx = 5
    play_ndx = 6
    sub_ndx = 1
    comment_ndx = 1

    def __init__(self, rows, out_on_error=play.NEVER_ADVANCE):
        self.rows = copy.deepcopy(rows)
        self.out_on_error = out_on_error
        self.current_batter = None
        self.current_pitches = None
        self.mid_plate_sub = False
        self.current_subs = []
        self.events = []

        self.clean_rows()

    def clean_rows(self):
        """Translate all of the row records to a state-independent format."""
        self.rows = [self._remove_reviews(row) for row in self.rows]
        self._remove_duplicates()
        self.rows = [self._clean_row(row) for row in self.rows]

    def _remove_reviews(self, row):
        """Get rid of play events that correspond to reviews of plays."""
        # A review is a play with pitches, a final pitch of type N, and a play type of OA.
        if (row[self.event_type_ndx] == "play"
                and len(row[self.pitches_ndx]) > 0
                and row[self.pitches_ndx][-1] == "N"
                and row[self.play_ndx][:2] == "OA"):
            # Remove the "N" pitch from the set of pitches.
            row[self.pitches_ndx] = row[self.pitches_ndx][:-1]
            # Replace the OA label with NP.
            row[self.play_ndx] = "NP" + row[self.play_ndx][2:]
        return row

    def _remove_duplicates(self):
        """Remove obvious duplicate records from the set of rows."""
        duplicates_ndx = []
        last_play_ndx = None
        # Construct a list of duplicate indices.
        for ndx in range(len(self.rows)):
            if last_play_ndx and self._is_duplicate(self.rows[last_play_ndx], self.rows[ndx]):
                duplicates_ndx.append(ndx)
            if self.rows[ndx][self.event_type_ndx] == "play":
                last_play_ndx = ndx
        # Remove the duplicates. We reverse the order so we don't affect later indices by
        # deleting earlier rows.
        duplicates_ndx.reverse()
        for d in duplicates_ndx:
            self.rows.pop(d)

    def _is_duplicate(self, last_play, current_play):
        return (  # Is the row actually a play record?
                last_play[self.event_type_ndx] == current_play[self.event_type_ndx] == "play"
                # Are the pitches the same and not blank?
                and last_play[self.pitches_ndx] == current_play[self.pitches_ndx] != ""
                # Is the batter the same?
                and last_play[self.batter_ndx] == current_play[self.batter_ndx]
                # Is the play a no-play record in both cases?
                and last_play[self.play_ndx] == current_play[self.play_ndx] == "NP")

    def _clean_row(self, row):
        """Clean an event row so it can be independently parsed.

        The biggest challenge that raw Retrosheet row records pose is that they can
        replicate pitches. If a plate appearance is interrupted (by a base running play,
        substitution, or something else), the next record will include every pitch from
        the beginning of the plate appearance. Normally, these records can be identified
        by the fact that the same batter appears twice in a row, but mid-plate substitutions
        can muddy the picture a good bit.
        """
        if self._is_duplicate_sub(row):
            row[self.pitches_ndx] = ""
        is_fresh_mid_plate_sub = self._check_for_mid_plate_sub(row)

        # Keep a running list of substitutions during a mid-plate sub.
        if self.mid_plate_sub and row[self.event_type_ndx] == "sub":
            self.current_subs.append(row[self.sub_ndx])

        if row[self.event_type_ndx] == "play" and row[self.pitches_ndx] != "":
            original_pitches = row[self.pitches_ndx]
            if self.mid_plate_sub and not is_fresh_mid_plate_sub and row[self.play_ndx] != "NP":
                self._handle_mid_plate_sub(row)
            # If the batter is repeated, then get rid of the pitches that are repeated.
            if row[self.batter_ndx] == self.current_batter:
                row[self.pitches_ndx] = self._clean_pitches(row[self.pitches_ndx])
            # Update row-cleaning state.
            self.current_batter = row[self.batter_ndx]
            self.current_pitches = original_pitches
        return row

    def _is_duplicate_sub(self, row):
        """Determines if a substitution involves a single play record being duplicated."""
        return (row[self.event_type_ndx] == "play"
                and [self.batter_ndx] == self.current_batter
                and row[self.pitches_ndx] == self.current_pitches
                and len(row[self.pitches_ndx]) > 0)

    def _check_for_mid_plate_sub(self, row):
        """Determines if an event is a mid-plate-appearance substitution.

        Mid-plate-appearance substitutions are difficult because they confound the simplest
        way to check for multi-record plate appearances: look for the same batter at the
        plate for two or more play records in a play.

        Returns true only if the row is the first of a series describing a mid-plate substitution.
        """
        if self.mid_plate_sub:
            return False
        # All mid-plate substitutions are no-play records.
        if (row[self.event_type_ndx] == "play"
                and row[self.play_ndx] == "NP"):
            # A mid-plate sub after an event will repeat the batter without pitches.
            post_event_sub = (row[self.batter_ndx] == self.current_batter
                              and row[self.pitches_ndx] == "")
            # A mid-plate sub after a normal pitch will tag the play with NP.
            post_pitch_sub = len(row[self.pitches_ndx]) > 0
            self.mid_plate_sub = post_event_sub or post_pitch_sub
        else:
            self.mid_plate_sub = False
        return self.mid_plate_sub

    def _handle_mid_plate_sub(self, row):
        """Modify the row that's the second batter's portion of a mid-plate substitution."""
        if row[self.batter_ndx] in self.current_subs:
            # Force the value of self.current_batter so the normal cleaning logic will work.
            self.current_batter = row[self.batter_ndx]
        # Clear mid_plate_sub-related state.
        self.mid_plate_sub = False
        self.current_subs = []

    def _clean_pitches(self, new_pitches):
        """Given a pair of adjacent play records from the same at-bat, remove the pitches in
        the new record that were already in the old record."""
        if new_pitches == "":
            return new_pitches
        # Dots are markers for no-play events, so we can safely remove them.
        current_pitches_no_dots = self.current_pitches.replace(".", "")
        new_pitches_no_dots = new_pitches.replace(".", "")
        num_current_pitches = len(current_pitches_no_dots) if current_pitches_no_dots else 0
        return new_pitches_no_dots[num_current_pitches:]

    def parse(self):
        """Parse every row, and append the events they represent to self.events."""
        for row in self.rows:
            if row[self.event_type_ndx] == "play":
                # Play records are complex enough that they need yet another parser to
                # decipher them. They generally contain multiple events.
                self.events += RetrosheetPlayParser(row, self.out_on_error).parse()
            elif row[self.event_type_ndx] == "sub":
                self.events += [sub.Substitution.from_retrosheet(row)]
            elif row[self.event_type_ndx] in ["badj", "padj"]:
                self.events += [sub.HandednessAdjustment.from_retrosheet(row)]
            elif row[self.event_type_ndx] == "com":
                self.events += self._parse_comments(row)
            else:
                raise Exception("Unknown event type!")
        return self.events

    def _parse_comments(self, row):
        """Parse a comment row to see if it's describing an exotic event we need to model."""
        event = None
        comment = row[self.comment_ndx].lower()
        # When games are called early, they are marked by comments that almost invariably
        # start with "game".
        if comment[:5] == "$game" or comment[:4] == "game":
            event = play.GameCalled.from_retrosheet(row)
        # Once in a blue moon, a batter will get a walk on 3 balls. This is always marked
        # with a comment.
        elif ((comment[:5] == "$walk" and ("3" in comment or "three" in comment))
              or "3 balls" in comment
              or "three balls" in comment):
            # Our fix here is to insert a fictitious fourth ball.
            event = pitch.Pitch.from_retrosheet("B")
        return [event] if event else []


class RetrosheetPlayParser(object):
    """Parse a single play record from a Retrosheet game file.

    This class lives here instead of in sim.play because a Retrosheet play record doesn't
    have a logical, consistent mapping to events in the simulation -- it's just an
    artifact of the goofy data encoding decisions they made.
    """

    """Regex that specifies the complete set of legal Retrosheet pitches."""
    pitch_format = re.compile(r"""[*+>]?                    # pitch modifiers
                                  [123BCFHIKLMOPQRSTUVXY]   # pitch events
                               """, re.VERBOSE)
    play_comment = re.compile(r"!")

    pitches_ndx = 5
    play_ndx = 6

    def __init__(self, row, out_on_error=play.NEVER_ADVANCE):
        """Default constructor.

        Args:
            row: Row from a Retrosheet event file.
            out_on_error: Interpretation strategy for ambiguous advances.
        """
        self.pitches_text = row[self.pitches_ndx]
        self.play_text = re.sub(self.play_comment, "", row[self.play_ndx])
        self.events = []
        self.out_on_error = out_on_error

    def parse(self):
        """Parse the Retrosheet row into a list of events."""
        self.events += self._parse_pitches()
        new_play = self._parse_play()
        if new_play:
            self._tag_last_pitch()
            self.events += new_play
        return self.events

    def _parse_pitches(self):
        pitches = re.findall(self.pitch_format, self.pitches_text)
        return [pitch.Pitch.from_retrosheet(p) for p in pitches]

    def _parse_play(self):
        # Once again, a component of the play record is so complex, it deserves its own
        # (sub-sub-)parser.
        return RetrosheetPlayTextParser(self.play_text, self.out_on_error).parse()

    def _tag_last_pitch(self):
        """Tag the last pitch as having triggered a play.

        This is useful when the last event in the record is a base-running play. We'd like
        to know if, for example, a pitch led to a stolen base."""
        if self.events:
            self.events[-1].play_on_pitch = True


class RetrosheetPlayTextParser(object):
    """Parse the event description field of a Retrosheet play record."""

    """Some of the labels in the Retrosheet play field don't correspond to actual game
    events (they're really just redundant summaries of the event triggered by the last
    pitch thrown). In these cases, we ignore the play."""
    non_events = re.compile(r"((HP)|(K(([1-4]+)|(\+E2))?)|NP|(I?W))$")
    """Regex for hit location modifiers."""
    hit_location_re = re.compile("""B?     # if present, indicates a bunt
                                   [PFLG]  # trajectory of the ball:
                                           # Popup, Fly, Line, or Ground
                                   ([1-9]  # Single fielder designating location
                                    |(13)|(15)|(23)|(25)|(34)|(56)|(78)|(89))?
                                           # Legal pairs of fielders designating location
                                   L?      # Extreme fair territory in deep outfield
                                   ([SMD]|(MS)|(MD)|(XD))?
                                           # Distance modifiers
                                   [+-F]?$ # Foul indicator
                              """, re.VERBOSE)
    home_run_location_re = re.compile(r"(7|8|9|(78)|(89))[+-]?$")
    hit_modifier_re = re.compile(r"[-+]")
    arc_re = re.compile(r"B?[PLFG][+-]?$")
    error_re = re.compile(r"E[1-9]$")
    balk_re = re.compile(r"BK$")
    # Modifiers are denoted by slashes, but there are some slashes inside parentheses that
    # should be ignored.
    modifier_split = re.compile(r"(?:[^/(]|\([^)]*\))+")

    def __init__(self, text, out_on_error=play.NEVER_ADVANCE):
        """Default constructor.

        Args:
            text: Text of the play description from a Retrosheet event file.
            out_on_error: Interpretation strategy for ambiguous advances.
        """
        self.text = text
        self.out_on_error = out_on_error
        # The text can be split into three basic pieces: the play description (what
        # happened), the play modifier (most commonly, the trajectory of the batted ball),
        # and the advances (what happened to the baserunners).
        modifier_splits = re.findall(self.modifier_split, self.text.split(".")[0])
        self.description_text = modifier_splits[0]
        self.modifiers_text = modifier_splits[1:]
        self.advances_text = self.text.split(".")[1] if "." in self.text else None
        self.play = None

    def parse(self):
        """Parse the play description into at most one events."""
        if re.match(self.non_events, self.description_text):
            self._parse_non_event()
        elif re.match(self.balk_re, self.description_text):
            self.play = pitch.Balk()
        else:
            self._parse_full_play()
        return [self.play] if self.play else []

    def _parse_non_event(self):
        # Ordinarily, we don't do anything to process a non-event. However, occasionally an
        # advance will be attached to a non-event. In that case, we have to create a dummy
        # event to attach the advance information to.
        if self.advances_text and self._is_advances_text_interesting():
            self.play = play.BaseRunning.from_retrosheet("OA", self.out_on_error)
            self._parse_non_event_errors()
            self._parse_advances()

    def _is_advances_text_interesting(self):
        """Does the advance text on a non-event play contain something that changes the
        state of the game?"""
        if not self.advances_text:
            return False
        return ("E" in self.advances_text or self.description_text == "K23"
                or "X" in self.advances_text or "E" in self.description_text)

    def _parse_non_event_errors(self):
        """Add errors from a non-event's advances to the play."""
        error_texts = re.findall(self.error_re, self.advances_text)
        for error_text in error_texts:
            self._add_error(error_text)

    def _parse_full_play(self):
        self._parse_description()
        for modifier in self.modifiers_text:
            self._parse_modifier(modifier)
        self._parse_advances()

    def _parse_description(self):
        # We first try to parse the play description as if it were a batted ball. If it
        # won't parse, it will return None, and we try parsing it as a baserunning play.
        self.play = play.BattedBall.from_retrosheet(self.description_text, self.out_on_error)
        if not self.play:
            self.play = play.BaseRunning.from_retrosheet(self.description_text, self.out_on_error)

    def _parse_modifier(self, modifier):
        # There are many legal modifiers in the Retrosheet specification, but we're really
        # only interested in two types: hit locations (usually just arcs, such as fly or
        # ground), and errors committed by fielders.
        if re.match(self.error_re, modifier):
            self._add_error(modifier)
        # Home runs usually don't follow the regex pattern of all other hit locations.
        elif re.match(self.home_run_location_re, modifier):
            modifier = re.sub(self.hit_modifier_re, "", modifier)
            self.play.hit_location = play.HitLocation.from_retrosheet(location=modifier)
        elif re.match(self.hit_location_re, modifier) and modifier != "FL":
            self._parse_location(modifier)

    def _parse_location(self, location_text):
        # If we already know roughly where it landed (because of who fielded it), then we'll
        # just add the arc of the ball.
        if re.match(self.arc_re, location_text):
            if self.play.hit_location:
                self.play.hit_location.add_retrosheet_arc(location_text)
        # Otherwise, we'll add all of the information in the hit record.
        else:
            self.play.hit_location = play.HitLocation.from_retrosheet_modifier(location_text)

    def _add_error(self, error_text):
        fielder = int(error_text[1])  # Error_text will be of the form EX, where X is a digit
        if fielder not in self.play.errors:
            self.play.errors.append(fielder)

    def _parse_advances(self):
        if self.advances_text:
            self.play.advances.add_retrosheet_advances(self.advances_text)
