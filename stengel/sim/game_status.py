from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

from . import bases
from . import roster


class GameStatus(object):
    """Represents the current status of a baseball game.

    Attributes:
        rosters: Dict with structure {"home": [home team roster], "away": [away team roster]}.
        players: Players object.
        inning: Current inning.
        team_at_bat: Team currently at bat; either "home" or "away".
        team_fielding: Team current fielding; either "home" or "away".
        score: Dict with structure {"home": [home team score], "away": [away team score]}.
        outs: Current outs.
        bases: Bases object with current status of players on base.
        balls: Current count of balls.
        strikes: Current count of strikes.
        game_over: Boolean; whether the game is over.
        last_batter_charged: Dict with keys "home" and "away"; for each team, whether the last
            batter at the plate was charged with a plate appearance.
        batter: Batter currently at the plate.
        pitcher: Pitcher currently on the mound.
    """
    def __init__(self, rosters, players=None):
        """Default constructor.

        Args:
            rosters: Dict with keys "home" and "away"; values are Roster objects with the
                respective team rosters.
            players: Players object.
        """
        self.rosters = rosters
        self.players = players
        self.inning = 1
        self.team_at_bat = "away"
        self.team_fielding = "home"

        self.score = {"home": 0,
                      "away": 0}
        self.outs = 0
        self.bases = bases.Bases()
        self.balls = 0
        self.strikes = 0
        self.game_over = False
        self.last_batter_charged = {"home": True,
                                    "away": True}

        self._update_plate_matchup()

    def __str__(self):
        """Stringification/pretty printing method."""
        return ("Inning: {}         At Bat:  {}\n".format(self.inning, self.team_at_bat)
                + "Score:  {}-{}\n".format(self.score["away"], self.score["home"])
                + "Outs:   {}         Count:   {}-{}\n".format(self.outs, self.balls, self.strikes)
                + "Batter: {}  Pitcher: {}\n".format(self.batter, self.pitcher)
                + "Bases:  {}\n".format(self.bases.bases)
                + "Game Over: {}".format(self.game_over))

    # Methods to handle game events

    def substitution(self, event):
        """Execute a substitution event."""
        old_player = self.rosters[event.team].substitute(event)
        new_player = event.player_id
        if old_player != new_player:
            self._replace_old_player(old_player, new_player)

    def handedness_adjustment(self, event):
        """Execute a handedness adjustment event."""
        pass

    def game_called(self, event):
        """Execute a game_called event."""
        self.game_over = True

    def batted_ball(self, event):
        """Execute a batted_ball event."""
        self._update_bases(event.advances)
        if not event.advances.batter == bases.STILL_ACTIVE:
            self._next_batter()

    def base_running(self, event):
        """Execute a base_running event."""
        self._update_bases(event.advances)
        if event.advances.batter == bases.STILL_ACTIVE:
            self._update_batter()
        else:
            self._next_batter()

    def pitch(self, event):
        """Execute a pitch event."""
        getattr(self, event.pitch_event)()
        if not event.play_on_pitch:
            self._update_batter()

    # Methods to handle specific types of pitches

    def foul(self):
        """Process a foul ball event."""
        if self.strikes < 2:
            self.strikes += 1

    def strike(self):
        """Process a strike event."""
        self.strikes += 1

    def foul_bunt(self):
        """Process a foul bunt event."""
        self.strikes += 1

    def ball(self):
        """Process a ball event."""
        self.balls += 1

    def hit_by_pitch(self):
        """Process a hit_by_pitch event."""
        self.score[self.team_at_bat] += self.bases.walk(self.batter)
        self.game_over = self._home_team_won()
        self._next_batter()

    def balk(self):
        """Process a balk event."""
        self.score[self.team_at_bat] += self.bases.balk()
        self.game_over = self._home_team_won()

    def contact(self):
        """Process a contact event."""
        # Empty because all of the interesting information is contained in the batted_ball
        # event that will immediately follow.
        pass

    def pickoff(self):
        # Empty because if there's any interesting outcome from the pickoff, it will be in
        # a base_running event that will immediately follow.
        pass

    # Getter methods

    def bases_vector(self):
        """Return a vector of 1s and 0s representing whether a runner is on each base."""
        return [int(bool(base)) for base in self.bases.bases]

    def home_pitcher(self):
        """Return the home team's current pitcher."""
        return self.rosters["home"].fielding[roster.PITCHER]

    def away_pitcher(self):
        """Return the away team's current pitcher."""
        return self.rosters["away"].fielding[roster.PITCHER]

    # Support methods

    def _replace_old_player(self, old_player, new_player):
        self.bases.substitute(old_player, new_player)
        self._update_plate_matchup()

    def _update_plate_matchup(self):
        self.batter = self.rosters[self.team_at_bat].current_batter()
        self.pitcher = self.rosters[self.team_fielding].current_pitcher()

    def _update_batter(self):
        if self.strikes == 3:
            self._strikeout()
        elif self.balls == 4:
            self._walk()
        elif self.outs >= 3:
            # If we're over three outs not because of the batter (i.e., a runner caught
            # stealing, the batter isn't charged with a plate appearance.
            self.last_batter_charged[self.team_at_bat] = False
            self._next_batter()

    def _strikeout(self):
        self.outs += 1
        self._next_batter()

    def _walk(self):
        self.score[self.team_at_bat] += self.bases.walk(self.batter)
        self.game_over = self._home_team_won()
        self._next_batter()

    def _update_bases(self, advances):
        runs_scored, outs_made = self.bases.hit(self.batter, advances)
        self.score[self.team_at_bat] += runs_scored
        self.outs += outs_made
        self.game_over = self._home_team_won()

    def _next_batter(self):
        self.balls = 0
        self.strikes = 0
        if self.players:
            self.players.update_pitcher(self.pitcher, "next_batter")

        if self._is_half_inning_over():
            self._switch_sides()
        if self.last_batter_charged[self.team_at_bat]:
            self.rosters[self.team_at_bat].move_to_next_batter()
        else:
            self.last_batter_charged[self.team_at_bat] = True
        self._update_plate_matchup()

    def _switch_sides(self):
        self.team_at_bat, self.team_fielding = self.team_fielding, self.team_at_bat
        self.bases.switch_sides()
        self._update_plate_matchup()

        self.outs = 0
        if self.team_at_bat == "away":
            self.inning += 1
        self.game_over = self._home_team_won() or self._away_team_won()

    def _is_half_inning_over(self):
        return self.outs >= 3

    def _home_team_won(self):
        return (self.inning >= 9 and self.team_at_bat == "home"
                and self.score["home"] > self.score["away"])

    def _away_team_won(self):
        return (self.inning > 9 and self.team_at_bat == "away"
                and self.score["away"] > self.score["home"])
