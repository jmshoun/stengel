from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import functools
import datetime

import progressbar
import numpy as np

from ..sim import game
from ..sim import player


class PitchDataGenerator(object):
    """Generate a NumPy array with data on individual pitches.

    The generated data is a two-dimensional array. Rows are pitches, and columns are
    variables. The complete list of variable names is in PitchDataGenerator.variable_names.
    """

    """List of all column names (in order) in the generated arrays."""
    variable_names = ["inning", "outs", "balls", "strikes", "score_away_team", "score_home_team",
                      "runner_on_first", "runner_on_second", "runner_on_third", "pitcher_id",
                      "pitch_count_game", "pitch_count_at_bat", "pickoff_count_game",
                      "pickoff_count_at_bat", "pitcher_age", "pitcher_mlb_tenure",
                      "pitcher_height", "pitcher_weight", "pitcher_bats", "pitcher_throws",
                      "batter_id", "batter_age", "batter_mlb_tenure", "batter_height",
                      "batter_weight", "batter_bats", "batter_throws", "start_speed", "end_speed",
                      "strike_zone_top", "strike_zone_bottom", "delta_x", "delta_z", "plate_x",
                      "plate_z", "start_x", "start_y", "start_z", "velocity_x", "velocity_y",
                      "velocity_z", "accel_x", "accel_y", "accel_z", "break_y", "break_angle",
                      "break_length", "spin_direction", "spin_rate", "pitch_outcome"]

    def __init__(self, database, first_date="1900/01/01", last_date="9999/12/31"):
        """Default constructor.

        Args:
            database: database object with Game and PlayerInfo records.
            first_date: First date of games to generate data from, as "YYYY/MM/DD".
            last_date: Last date of games to generate data from, as "YYYY/MM/DD".
        """
        self.database = database
        self.players = player.Players()
        self.first_date = first_date
        self.last_date = last_date
        self.pitcher_data = []
        self.game_records = []
        self.player_info = {}
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
        # Convert data from list of 1-D array to 2-D array
        self.pitcher_data = np.array(self.pitcher_data)
        return self.pitcher_data

    def _get_game_records(self):
        self.game_records = self.database.games.find({
            "metadata.game_date": {"$gte": self.first_date, "$lte": self.last_date}
        })

    def _add_game_pitches(self, game_record):
        current_game = game.Game.from_dict(game_record, self.players)
        # Process initial calls
        current_game.apply_box_score_events()
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
        self.pitcher_data.append(state)

    def _complete_state(self, current_game, pitch):
        game_status = current_game.game_status
        game_state = self._game_status_state(game_status)
        pitcher_state = self._pitcher_state(game_status)
        pitcher_info = self._pitcher_info(game_status)
        batter_state = self._batter_state(game_status)
        batter_info = self._batter_info(game_status)
        pitch_info = self._pitch_state(pitch)
        pitch_response = self._pitch_response(pitch)
        return functools.reduce(np.append, [game_state, pitcher_state, pitcher_info, batter_state,
                                            batter_info,  pitch_info, pitch_response])

    def _batter_state(self, game_status):
        return np.array([self._get_batter_id(game_status.batter)])

    def _batter_info(self, game_status):
        batter_info = self._get_player_info(game_status.batter)
        return self._player_info_to_array(batter_info, game_status)

    def _pitcher_info(self, game_status):
        pitcher_info = self._get_player_info(game_status.pitcher)
        return self._player_info_to_array(pitcher_info, game_status)

    def _player_info_to_array(self, info, game_status):
        return np.array([info.age(game_status.game_date), info.mlb_tenure(game_status.game_date),
                         info.height, info.weight,
                         self._handedness_to_int(info.bats),
                         self._handedness_to_int(info.throws)])

    def _get_player_info(self, player_id):
        if player_id not in self.player_info:
            player_record = self.database.player_info.find_one({"id_": player_id})
            self.player_info[player_id] = player.PlayerInfo.from_dict(player_record)
        return self.player_info[player_id]

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

    def _pitcher_state(self, game_status):
        pitcher_obj = self.players.pitchers[game_status.pitcher]
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

    @staticmethod
    def _handedness_to_int(handedness):
        # Mnemonic: the choice of positive for right is the same as the number line.
        if handedness == "Right":
            return 1
        elif handedness == "Left":
            return -1
        else:
            return 0