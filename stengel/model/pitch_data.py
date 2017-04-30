import functools

import progressbar
import numpy as np

from ..sim import game
from ..sim import player


class PitchData(object):
    """Represent data on a set of individual pitches in a format suitable for modeling
    with Tensorflow.

    Attributes:
        pitch_data: 2D NumPy float array of pitch-level predictors.
        pitcher_ids: 1D NumPy int array of pitcher IDs for each pitch.
        batter_ids: 1D NumPy int array of batter IDs for each pitch.
        pitch_outcomes: 1D NumPy int array of outcomes for each pitch.
        batters: List of Retrosheet IDs that correspond to each batter ID.
        pitchers: List of Retrosheet IDs that correspond to each pitcher ID.
        pitch_density: Optional; dicionary with keys of pitcher Retrosheet IDs and values of
            1D NumPy float arrays with a representation of that pitcher's distribution of
            pitch types thrown.
        batch_index: The index that the next batch should start with.
        reached_end: Whether the end of the data was reached on the previous batch.
        num_observations: The number of observations in the data set.
        shuffle_each_epoch: Whether the data should be randomly shuffled after each training
            epoch.
    """

    """List of all of the column names (in order) in pitch_data."""
    variable_names = ["inning", "outs", "balls", "strikes", "score_away_team", "score_home_team",
                      "runner_on_first", "runner_on_second", "runner_on_third", "pitch_count_game",
                      "pitch_count_at_bat", "pickoff_count_game", "pickoff_count_at_bat",
                      "pitcher_age", "pitcher_mlb_tenure", "pitcher_height", "pitcher_weight",
                      "pitcher_bats", "pitcher_throws", "batter_age", "batter_mlb_tenure",
                      "batter_height", "batter_weight", "batter_bats", "batter_throws",
                      "start_speed", "end_speed", "strike_zone_top", "strike_zone_bottom",
                      "delta_x", "delta_z", "plate_x", "plate_z", "start_x", "start_y", "start_z",
                      "velocity_x", "velocity_y", "velocity_z", "accel_x", "accel_y", "accel_z",
                      "break_y", "break_angle", "break_length", "spin_direction", "spin_rate"]

    def __init__(self, pitch_data=None, pitcher_ids=None, batter_ids=None, pitch_outcomes=None,
                 batters=None, pitchers=None, pitch_density=None, shuffle_each_epoch=True):
        """Default constructor."""
        self.pitch_data = [] if pitch_data is None else pitch_data
        self.pitcher_ids = [] if pitcher_ids is None else pitcher_ids
        self.batter_ids = [] if batter_ids is None else batter_ids
        self.pitch_outcomes = [] if pitch_outcomes is None else pitch_outcomes
        self.batters = [] if batters is None else batters
        self.pitchers = [] if pitchers is None else pitchers
        self.pitch_density = pitch_density
        # TODO: Add validation that first four elements are all the same length
        self.batch_index = 0
        self.reached_end = False
        self.num_observations = None if self.pitch_outcomes == [] else self.pitch_outcomes.shape[0]
        self.shuffle_each_epoch = shuffle_each_epoch

    def pitches_per_pitcher(self):
        """Return a list with each element the number of pitches thrown by the corresponding
        pitcher_id."""
        result = [0] * len(self.pitchers)
        for pitcher_id in self.pitcher_ids.tolist():
            result[pitcher_id] += 1
        return result

    def filter_rows(self, filter_, reassign_ids=True, in_place=False):
        """Filter the dataset row-wise.

        Inputs:
            filter_: NumPy array of bools or ints with the rows to be retained.
            reassign_ids: Whether to reassign pitcher and batter IDs to remove unused IDs.
            in_place: Whether to perform the filtering in-place.
        Returns:
            A filtered copy of the data set.
        """
        result = self if in_place else PitchData(pitchers=self.pitchers, batters=self.batters,
                                                 pitch_density=self.pitch_density)
        result.pitch_data = self.pitch_data[filter_, :]
        result.pitcher_ids = self.pitcher_ids[filter_]
        result.batter_ids = self.batter_ids[filter_]
        result.pitch_outcomes = self.pitch_outcomes[filter_]
        result.num_observations = result.pitch_outcomes.shape[0]
        if reassign_ids:
            result = self._reassign_ids(result)
        return result

    def _reassign_ids(self, result):
        result.batter_ids, result.batters, _ = \
            self._compress_players(result.batter_ids, self.batters)
        result.pitcher_ids, result.pitchers, result.pitch_density = \
            self._compress_players(result.pitcher_ids, self.pitchers, self.pitch_density)
        return result

    def filter_by_pitcher_id(self, ids, reassign_ids=True, in_place=False):
        """Filter the dataset by pitcher_id."""
        filter_list = [pitcher_id in ids for pitcher_id in self.pitcher_ids.tolist()]
        filter_ = np.array(filter_list)
        return self.filter_rows(filter_, reassign_ids, in_place)

    def filter_nulls(self, reassign_ids=True, in_place=False):
        """Filter rows with any nulls/NaNs in pitch_data."""
        nulls = np.isnan(self.pitch_data).any(axis=1)
        return self.filter_rows(~nulls, reassign_ids, in_place)

    @classmethod
    def _compress_players(cls, player_ids, players, density=None):
        unique_player_ids = np.unique(player_ids)
        players = cls._drop_unused_players(players, unique_player_ids)
        player_ids = cls._remap_player_ids(player_ids, unique_player_ids)
        if density is not None:
            density = density[unique_player_ids, :]
        return player_ids, players, density

    @staticmethod
    def _drop_unused_players(players, unique_player_ids):
        return [player_ for id_, player_ in enumerate(players)
                if id_ in unique_player_ids]

    @staticmethod
    def _remap_player_ids(player_ids, unique_player_ids):
        id_map = {id_: i for i, id_ in enumerate(unique_player_ids)}
        return np.array([id_map[id_] for id_ in player_ids], dtype="int32")

    def get_batch(self, batch_size):
        """Return a dict with the next batch_size observations in self, in a format ready
        for ingestion by a Tensorflow model."""
        batch_start, batch_end = self.batch_index, self.batch_index + batch_size
        pitcher_ids = self.pitcher_ids[batch_start:batch_end]
        batch_data = {"pitch_data:0": self.pitch_data[batch_start:batch_end, :],
                      "batter_ids:0": self.batter_ids[batch_start:batch_end],
                      "pitcher_ids:0": pitcher_ids,
                      "pitch_outcomes:0": self.pitch_outcomes[batch_start:batch_end]}
        if self.pitch_density is not None:
            batch_data["pitch_density:0"] = self.pitch_density[pitcher_ids, :]
        self._update_batch_index(batch_size)
        return batch_data

    def _update_batch_index(self, batch_size):
        self.batch_index += batch_size
        if self.batch_index + batch_size > self.num_observations:
            self.batch_index = 0
            self.reached_end = True
            if self.shuffle_each_epoch:
                self.shuffle()

    def has_reached_end(self):
        result = self.reached_end
        self.reached_end = False
        return result

    def reset_batch_index(self):
        self.reached_end = False
        self.batch_index = 0

    def shuffle(self, random_seed=None):
        """Randomly permute the data.

        Inputs:
            random_seed: Random seed to use when permuting.
        """
        if random_seed:
            np.random.seed(random_seed)
        new_order = np.random.permutation(self.num_observations)
        self.pitch_data = self.pitch_data[new_order, :]
        self.batter_ids = self.batter_ids[new_order]
        self.pitcher_ids = self.pitcher_ids[new_order]
        self.pitch_outcomes = self.pitch_outcomes[new_order]

    def as_dict(self):
        """Return a dictionary representation of the object."""
        return {"pitch_data": self.pitch_data, "pitch_outcomes": self.pitch_outcomes,
                "batter_ids": self.batter_ids, "pitcher_ids": self.pitcher_ids,
                "batters": self.batters, "pitchers": self.pitchers,
                "pitch_density": self.pitch_density,
                "shuffle_each_epoch": self.shuffle_each_epoch}

    @classmethod
    def from_dict(cls, dict_):
        """Constructor from a dictionary representation."""
        return cls(**dict_)


class PitchDataGenerator(object):
    def __init__(self, database):
        self.pitch_data = []
        self.pitcher_ids = []
        self.batter_ids = []
        self.pitch_outcomes = []
        self.batters = []
        self.pitchers = []

        self.database = database
        self.game_records = []
        self.players = player.Players()
        self.player_info = {}

    def generate_data(self, first_date, last_date):
        self._get_game_records(first_date, last_date)
        self._add_pitches_from_records()
        self._convert_data_types()
        return PitchData(self.pitch_data, self.pitcher_ids, self.batter_ids, self.pitch_outcomes,
                         self.batters, self.pitchers)

    def _get_game_records(self, first_date, last_date):
        self.game_records = self.database.games.find({
            "metadata.game_date": {"$gte": first_date, "$lte": last_date}
        })

    def _add_pitches_from_records(self):
        num_games = self.game_records.count()
        with progressbar.ProgressBar(max_value=num_games) as bar:
            game_number = 0
            for game_record in self.game_records:
                bar.update(game_number)
                self._add_game_pitches(game_record)
                game_number += 1

    def _convert_data_types(self):
        self.batter_ids = np.array(self.batter_ids, dtype="int32")
        self.pitcher_ids = np.array(self.pitcher_ids, dtype="int32")
        self.pitch_outcomes = np.array(self.pitch_outcomes, dtype="int32")
        self.pitch_data = np.array(self.pitch_data)

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
        # We're not doing any modeling when PitchFx data is missing.
        if not pitch.pitch_fx:
            return

        self._add_pitcher_id(current_game.game_status.pitcher)
        self._add_batter_id(current_game.game_status.batter)
        self._add_pitch_data(current_game, pitch)
        self._add_pitch_outcome(pitch)

    def _add_pitcher_id(self, pitcher):
        if pitcher in self.pitchers:
            pitcher_id = self.pitchers.index(pitcher)
        else:
            self.pitchers.append(pitcher)
            pitcher_id = len(self.pitchers) - 1
        self.pitcher_ids.append(pitcher_id)

    def _add_batter_id(self, batter):
        if batter in self.batters:
            batter_id = self.batters.index(batter)
        else:
            self.batters.append(batter)
            batter_id = len(self.batters) - 1
        self.batter_ids.append(batter_id)

    def _add_pitch_data(self, current_game, pitch):
        game_status = current_game.game_status
        game_state = self._game_status_state(game_status)
        pitcher_state = self._pitcher_state(game_status)
        pitcher_info = self._pitcher_info(game_status)
        batter_info = self._batter_info(game_status)
        pitch_info = self._pitch_info(pitch)
        full_state = functools.reduce(np.append, [game_state, pitcher_state, pitcher_info,
                                                  batter_info, pitch_info])
        self.pitch_data.append(full_state)

    def _add_pitch_outcome(self, pitch):
        # Mnemonic: outcomes are ordered by how close they were to yielding fair contact.
        if pitch.pitch_event in ["ball", "hit by pitch"]:
            outcome = 0
        elif pitch.pitch_event == "strike":
            outcome = 2 if pitch.swung else 1
        elif pitch.pitch_event in ["foul", "foul bunt"]:
            outcome = 3
        else:
            outcome = 4
        self.pitch_outcomes.append(outcome)

    @staticmethod
    def _game_status_state(game_status):
        return np.array([game_status.inning, game_status.outs, game_status.balls,
                         game_status.strikes, game_status.score["away"], game_status.score["home"]]
                        + game_status.bases_vector(),
                        dtype="float32")

    def _pitcher_state(self, game_status):
        pitcher_obj = self.players.pitchers[game_status.pitcher]
        return np.array([pitcher_obj.pitch_count_game, pitcher_obj.pitch_count_at_bat,
                         pitcher_obj.pickoff_count_game, pitcher_obj.pickoff_count_at_bat],
                        dtype="float32")

    def _pitcher_info(self, game_status):
        pitcher_info = self._get_player_info(game_status.pitcher)
        return self._player_info_to_array(pitcher_info, game_status)

    def _batter_info(self, game_status):
        batter_info = self._get_player_info(game_status.batter)
        return self._player_info_to_array(batter_info, game_status)

    @staticmethod
    def _pitch_info(pitch):
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
                         pitch.pitch_fx.spin_rate], dtype="float32")

    def _get_player_info(self, player_id):
        if player_id not in self.player_info:
            player_record = self.database.player_info.find_one({"id_": player_id})
            self.player_info[player_id] = player.PlayerInfo.from_dict(player_record)
        return self.player_info[player_id]

    def _player_info_to_array(self, info, game_status):
        return np.array([info.age(game_status.game_date), info.mlb_tenure(game_status.game_date),
                         info.height, info.weight,
                         self._handedness_to_int(info.bats),
                         self._handedness_to_int(info.throws)], dtype="float32")

    @staticmethod
    def _handedness_to_int(handedness):
        # Mnemonic: the choice of positive for right is the same as the number line.
        if handedness == "Right":
            return 1
        elif handedness == "Left":
            return -1
        else:
            return 0
