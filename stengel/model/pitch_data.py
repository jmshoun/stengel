from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import functools

import progressbar
import numpy as np

from ..sim import game
from ..sim import player


class PitchDataGenerator(object):
    """Generate a set of NumPy arrays with data on individual pitches.

    The generated data is a dictionary of arrays. THe keys are pitchers, and the values are
    NumPy arrays. Within each array, rows are pitches, and columns are variables.
    """
    def __init__(self, database, first_date="1900/01/01", last_date="9999/12/31"):
        """Default constructor.

        Args:
            database: database object with Game records.
            first_date: First date of games to generate data from, as "YYYY/MM/DD".
            last_date: Last date of games to generate data from, as "YYYY/MM/DD".
        """
        self.database = database
        self.players = player.Players()
        self.first_date = first_date
        self.last_date = last_date
        self.pitcher_data = {}
        self.game_records = []
        self.batters = ["No Batter"]
        self.pitchers = ["No Pitcher"]

    def generate_data(self):
        """Generate pitch data from the game records in the database."""
        self._get_game_records()
        num_games = self.game_records.count()
        with progressbar.ProgressBar(max_value=num_games) as bar:
            game_number = 0
            for game_record in self.game_records:
                bar.update(game_number)
                self._add_game_pitches(game_record)
                game_number += 1
        return self.pitcher_data

    def _get_game_records(self):
        self.game_records = self.database.games.find({
            "metadata.game_date": {"$gte": self.first_date, "$lte": self.last_date}
        })

    def _add_game_pitches(self, game_record):
        current_game = game.Game.from_dict(game_record, self.players)
        while not current_game.game_status.game_over:
            event = current_game.next_event()
            if event.event_type == "pitch" and not event.intentional:
                self._add_game_pitch(current_game, event)
            current_game.apply_next_event()

    def _add_game_pitch(self, current_game, pitch):
        # Don't add a row if we don't have any PitchFx data.
        if not pitch.pitch_fx:
            return
        state = self._complete_state(current_game, pitch)
        pitcher = current_game.game_status.pitcher
        if pitcher not in self.pitcher_data:
            self.pitcher_data[pitcher] = []
        self.pitcher_data[pitcher].append(state)

    def _complete_state(self, current_game, pitch):
        game_status = current_game.game_status
        game_info = self._game_status_state(game_status)
        pitcher_info = self._pitcher_state(game_status.pitcher)
        batter_info = self._batter_state(game_status)
        pitch_info = self._pitch_state(pitch)
        pitch_response = self._pitch_response(pitch)
        return functools.reduce(np.append, [game_info, batter_info,
                                            pitcher_info, pitch_info, pitch_response])

    def _batter_state(self, game_status):
        return np.array([self._get_batter_id(game_status.batter)])

    @staticmethod
    def _pitch_state(pitch):
        return np.array([pitch.pitch_fx.start_speed, pitch.pitch_fx.end_speed,
                         pitch.pitch_fx.strike_zone_top, pitch.pitch_fx.strike_zone_bottom,
                         pitch.pitch_fx.delta_x, pitch.pitch_fx.delta_z,
                         pitch.pitch_fx.plate_x, pitch.pitch_fx.plate_z,
                         pitch.pitch_fx.start_x, pitch.pitch_fx.start_y, pitch.pitch_fx.start_z,
                         pitch.pitch_fx.velocity_x, pitch.pitch_fx.velocity_y,
                         pitch.pitch_fx.velocity_z, pitch.pitch_fx.accel_x,
                         pitch.pitch_fx.accel_y, pitch.pitch_fx.accel_z,
                         pitch.pitch_fx.break_y, pitch.pitch_fx.break_angle,
                         pitch.pitch_fx.break_length, pitch.pitch_fx.spin_direction,
                         pitch.pitch_fx.spin_rate])

    @staticmethod
    def _pitch_response(pitch):
        if pitch.pitch_event in ["ball", "hit by pitch"]:
            response = 1
        elif pitch.pitch_event == "strike":
            if not pitch.swung:
                response = 2
            else:
                response = 3
        elif pitch.pitch_event in ["foul", "foul bunt"]:
            response = 4
        else:
            response = 5
        return np.array([response])

    @staticmethod
    def _game_status_state(game_status):
        return np.array([game_status.inning, game_status.outs, game_status.balls,
                         game_status.strikes, game_status.score["away"], game_status.score["home"]]
                        + game_status.bases_vector())

    def _pitcher_state(self, pitcher):
        pitcher_obj = self.players.pitchers[pitcher]
        return np.array([self._get_pitcher_id(pitcher_obj),
                         pitcher_obj.pitch_count_game, pitcher_obj.pitch_count_at_bat,
                         pitcher_obj.pickoff_count_game, pitcher_obj.pickoff_count_at_bat])

    def _get_pitcher_id(self, pitcher):
        if pitcher in self.pitchers:
            return self.pitchers.index(pitcher)
        else:
            self.pitchers.append(pitcher)
            return len(self.pitchers) - 1

    def _get_batter_id(self, batter):
        if batter in self.batters:
            return self.batters.index(batter)
        else:
            self.batters.append(batter)
            return len(self.batters) - 1
