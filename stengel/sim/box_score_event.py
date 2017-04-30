class BoxScoreEvent(object):
    """Represent a single event that will become part of a "box-score" summary.

    Most traditional performance metrics for players (like ERA, batting averages, RBIs, and
    so on) are based on counts of events that are at a higher level of abstraction than the
    events in Stengel Games. In order to construct these metrics, we need a way of tracking
    these meta-events. Our solution is to create a lightweight class for each meta-event,
    all of which derive from this superclass. The GameStatus class generates meta-events as
    it processes events, which it then passes to the Players object for tabulation.

    The set of box score events and Stengel Game events is not mutually exclusive -- for
    example, BoxScoreEvent Pitches and Pickoffs are at roughly the same level of abstraction
    as Pitch events. However, they serve different purposes. Pitch events contain lots of
    metadata about how the pitch was thrown and are used for simulating outcomes for a pitch;
    BoxScoreEvent pitches are a simple signal to a Pitcher object to increase the pitch
    count.

    Attributes:
        name: Brief name of the event.
        pitcher: string: The Retrosheet player ID of the pitcher involved. None if no pitcher
            is involved.
        batter: string: The Retrosheet player ID of the batter involved. None if no batter
            is involved.
        runner: string: The Retrosheet player ID of the runner involved. In some cases, may
            be the same as batter. None if no batter is involved.
        fielders: list: A list of Retrosheet player IDs of the fielders involved. Empty list
            if not fielders are involved.
        date: datetime.date: The date the event happened.
        decrement: Whether to decrement the count of the event in question (in essence, cancel
            the event). A few events (notably plate appearance) are easier to occasionally
            decrement than to generate only in those circumstances where they are warranted.
    """
    def __init__(self, name, pitcher=None, batter=None, runner=None, fielders=None,
                 date=None, decrement=False):
        self.name = name
        self.pitcher = pitcher
        self.batter = batter
        self.runner = runner
        self.fielders = fielders if fielders else []
        self.date = date
        self.decrement = decrement


class CallPitcher(BoxScoreEvent):
    """A pitcher being called into the game.

    Includes a pitcher in the starting lineup at the very beginning of a game.
    """
    def __init__(self, pitcher, date):
        super(CallPitcher, self).__init__("call_pitcher", pitcher=pitcher, date=date)


class PlateAppearance(BoxScoreEvent):
    def __init__(self, pitcher, batter, decrement=False):
        super(PlateAppearance, self).__init__("plate_appearance", pitcher=pitcher, batter=batter,
                                              decrement=decrement)


class Pitch(BoxScoreEvent):
    def __init__(self, pitcher):
        super(Pitch, self).__init__("pitch", pitcher=pitcher)


class Pickoff(BoxScoreEvent):
    def __init__(self, pitcher, runner):
        super(Pickoff, self).__init__("pickoff", pitcher=pitcher, runner=runner)


class HitByPitch(BoxScoreEvent):
    def __init__(self, pitcher, batter):
        super(HitByPitch, self).__init__("hit_by_pitch", pitcher=pitcher, batter=batter)


class Balk(BoxScoreEvent):
    def __init__(self, pitcher):
        super(Balk, self).__init__("balk", pitcher=pitcher)


class Strikeout(BoxScoreEvent):
    def __init__(self, pitcher, batter):
        super(Strikeout, self).__init__("strikeout", pitcher=pitcher, batter=batter)


class Walk(BoxScoreEvent):
    def __init__(self, pitcher, batter):
        super(Walk, self).__init__("walk", pitcher=pitcher, batter=batter)
