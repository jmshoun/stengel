from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

"""Static module-level variables enumerating possible batter states after a pitch.

FIRST_, SECOND_, and THIRD_BASE correspond with their indices in Bases.bases. HOME_PLATE is 3
to preserve the natural ordering of homer > triple; OUT and STILL_ACTIVE were assigned their
values so that the values reflect a natural ordering of outcomes from bad to good (from the
batter's perspective).
"""
OUT = -2
STILL_ACTIVE = -1    # I.e., the plate appearance is not over.
FIRST_BASE = 0
SECOND_BASE = 1
THIRD_BASE = 2
HOME_PLATE = 3


class Bases(object):
    """Track the state of the bases within a baseball game.

    Instance variables:
        bases: A 3-vector, with each value either a Retrosheet player ID (representing the
            player on base), or None (the base is empty).
    """
    def __init__(self):
        """Default constructor."""
        self.bases = [None] * 3

    def hit(self, batter, advance):
        """Update the state of the bases to reflect a hit or base running play.

        Arguments:
            batter: A Retrosheet player ID.
            advance: An Advance object.
        Returns:
            A 2-tuple with the number of runs scored and outs made, respectively.
        """
        runs_and_outs = RunsAndOuts()
        # Iterate through bases in reverse order to avoid overwriting runners on later bases
        # with advancing runners.
        for base in [THIRD_BASE, SECOND_BASE, FIRST_BASE]:
            runs_and_outs += self._move_base_runner(base, advance.runners[base])
        # Iterate through again to catch any (extremely rare) retrograde baserunning.
        for base in [THIRD_BASE, SECOND_BASE, FIRST_BASE]:
            runs_and_outs += self._move_base_runner(base, advance.runners[base], reverse=True)

        runs_and_outs += self._move_runner(batter, advance.batter)
        return runs_and_outs.runs, runs_and_outs.outs

    def _move_base_runner(self, start_base, end_base, reverse=False):
        # Some baserunning moves are retrograde. These are processed iff reverse=True.
        runner = self.bases[start_base]
        reverse_motion = FIRST_BASE <= end_base < start_base
        if runner and end_base is not None and reverse_motion == reverse:
            self.bases[start_base] = None
            return self._move_runner(runner, end_base)
        else:
            return RunsAndOuts()

    def _move_runner(self, runner, end_base):
        if end_base == HOME_PLATE:
            return RunsAndOuts(runs=1)
        elif end_base == OUT:
            return RunsAndOuts(outs=1)
        elif end_base == STILL_ACTIVE:
            return RunsAndOuts()
        else:
            self.bases[end_base] = runner
            return RunsAndOuts()

    def walk(self, batter):
        """Update the state of bases to reflect a walk.

        Arguments:
            batter: A Retrosheet player ID representing the batter who was walked.
        Returns:
            The number of runs forced in by the walk.
        """
        return self._attempt_advance(batter, FIRST_BASE)

    def _attempt_advance(self, runner, end_base):
        # If the destination base is occupied, we have to force the next runner ahead.
        if self.bases[end_base]:
            return self._force_advance(runner, end_base)
        else:
            self.bases[end_base] = runner
            return 0

    def _force_advance(self, runner, end_base):
        if end_base == THIRD_BASE:
            self.bases[end_base] = runner
            # Runner at third scores
            return 1
        else:
            displaced_runner = self.bases[end_base]
            self.bases[end_base] = runner
            return self._attempt_advance(displaced_runner, end_base + 1)

    def balk(self):
        """Update the state of bases to reflect a balk.

        The function doesn't accept any arguments because the batter remains at bat after
        a balk -- only runners on base are advanced.

        Returns:
            The number of runs forced in by the balk.
        """
        status = RunsAndOuts()
        for base in [THIRD_BASE, SECOND_BASE, FIRST_BASE]:
            status += self._move_base_runner(base, base + 1)
        return status.runs

    def substitute(self, old_player, new_player):
        """Handle a pinch-running substitution.

        Args:
            old_player: Retrosheet ID of the player leaving the game.
            new_player: Retrosheet ID of the player entering the game.
        """
        for base in [FIRST_BASE, SECOND_BASE, THIRD_BASE]:
            if self.bases[base] == old_player:
                self.bases[base] = new_player

    def switch_sides(self):
        """Update the state of the bases at the end of a half-inning."""
        self.bases = [None] * 3


class RunsAndOuts(object):
    """Track state of runs and outs while updating Bases.

    This is basically just a named 2-vector with addition overloaded, but it goes a long
    way towards helping the code in bases read cleanly.
    """
    def __init__(self, runs=0, outs=0):
        """Default constructor."""
        self.runs = runs
        self.outs = outs

    def __add__(self, other):
        """Overloading addition with the usual behavior."""
        self.runs += other.runs
        self.outs += other.outs
        return self
