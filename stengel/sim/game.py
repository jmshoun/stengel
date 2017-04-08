from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import os
import xml.etree.ElementTree as ET
import copy

from . import game_status
from . import metadata
from . import roster
from . import play
from . import sub
from . import pitch


class Game(object):
    """Represent a baseball game in sufficient detail to reconstruct it, pitch-by-pitch.

    Attributes:
        metadata: GameMetadata object with game metadata.
        events: List of game event objects.
        initial_rosters: Dict with rosters at the start of the game for each team.
        players: Players object.
        game_status: GameStatus object with the current state of the game.
    """
    def __init__(self, rosters, metadata_=metadata.GameMetadata(), events=[], players=None):
        """Default constructor."""
        self.metadata = metadata_
        self.events = events
        self._current_event_ndx = 0
        self.initial_rosters = rosters
        self.players = players
        self.game_status = game_status.GameStatus(copy.deepcopy(rosters), players)
        if self.players:
            self.players.update_pitcher(self.game_status.home_pitcher(), "call",
                                        self.metadata.game_date)
            self.players.update_pitcher(self.game_status.away_pitcher(), "call",
                                        self.metadata.game_date)

    def as_dict(self):
        """Return a dictionary representation of the game."""
        return {"metadata": self.metadata.as_dict(),
                "rosters": {"home": self.initial_rosters["home"].as_dict(),
                            "away": self.initial_rosters["away"].as_dict()},
                "events": [e.as_dict() for e in self.events]}

    def reset(self):
        """Reset the status of the game to as it was before the first pitch was thrown."""
        self.game_status = game_status.GameStatus(copy.deepcopy(self.initial_rosters))
        self._current_event_ndx = 0

    def __str__(self):
        return str(self.game_status)

    def update(self, database):
        """Update the representation of the game in a database.

        Args:
            database: Database in which to update the game record.
        """
        database.games.update({"metadata.id_": self.metadata.id_}, self.as_dict())

    def next_event(self):
        """Return the next event in the game, chronologically."""
        return self.events[self._current_event_ndx]

    def apply_next_event(self):
        """Apply the next event to the current game status."""
        self.apply_event(self.next_event())
        self._current_event_ndx += 1

    def apply_event(self, event):
        """Apply a supplied event to the current game status."""
        getattr(self.game_status, event.event_type)(event)
        if self.players:
            self._update_pitcher(event)

    def verify_ending(self):
        """Check if the game ends immediately after the last play."""
        self._fast_forward_to_penultimate_play()
        if self.game_status.game_over:
            # Game shouldn't be over quite yet!
            self.reset()
            return False

        self.apply_next_event()
        game_over = self.game_status.game_over
        self.reset()
        return game_over

    def _fast_forward_to_penultimate_play(self):
        if self._current_event_ndx > 0:
            self.reset()
        num_events = len(self.events)
        for _ in range(num_events - 1):
            self.apply_next_event()

    @classmethod
    def from_dict(cls, dict_, players=None):
        """Constructor from a dictionary representation of the object."""
        rosters = {"home": roster.Roster.from_dict(dict_["rosters"]["home"]),
                   "away": roster.Roster.from_dict(dict_["rosters"]["away"])}
        metadata_ = metadata.GameMetadata.from_dict(dict_["metadata"])
        events = []
        for event_dict in dict_["events"]:
            event_type = event_dict["event_type"]
            event = getattr(cls, "_from_dict_" + event_type)(event_dict)
            events.append(event)

        return cls(rosters=rosters, metadata_=metadata_, events=events, players=players)

    @staticmethod
    def _from_dict_pitch(dict_):
        return pitch.Pitch.from_dict(dict_)

    @staticmethod
    def _from_dict_base_running(dict_):
        return play.BaseRunning.from_dict(dict_)

    @staticmethod
    def _from_dict_batted_ball(dict_):
        return play.BattedBall.from_dict(dict_)

    @staticmethod
    def _from_dict_substitution(dict_):
        return sub.Substitution.from_dict(dict_)

    @staticmethod
    def _from_dict_handedness_adjustment(dict_):
        return sub.HandednessAdjustment.from_dict(dict_)

    @staticmethod
    def _from_dict_game_called(dict_):
        return play.GameCalled.from_dict(dict_)

    def _update_pitcher(self, event):
        if event.event_type == "pitch":
            if event.event_type == "pickoff":
                self.players.update_pitcher(self.game_status.pitcher, "pickoff")
            elif event.threw:
                self.players.update_pitcher(self.game_status.pitcher, "pitch")
        elif event.event_type == "substitution" and event.fielding == roster.PITCHER:
            self.players.update_pitcher(event.player_id, "call", self.metadata.game_date)
