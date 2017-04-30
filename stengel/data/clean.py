import os
import sys
import glob
import fileinput
import xml.etree.ElementTree as ET


def replace_line(game_id, old_line, new_line, data_root="data"):
    """Replace a single line in a Retrosheet game record.

    There are a few extremely unusual events in the Retrosheet game records. Rather than
    extend the parser to handle these outliers, it's easier to edit the game records.

    Args:
        game_id: Retrosheet game ID of the game record to modify.
        old_line: The exact contents of the line in the game record to replace (no newline).
        new_line: The new contents of the line in the game record.
        data_root: Path to the root of the project data directory.
    Returns:
        bool: Whether the line was successfully replaced.
    """
    game_file = _retrosheet_filename(game_id, data_root)
    if not game_file:
        return False

    in_game = False
    replaced = False
    # The Retrosheet game files all have DOS line endings, thus the \r\ns everywhere.
    id_line = "id," + game_id + "\r\n"
    for line in fileinput.input(game_file, inplace=1):
        if line == id_line:
            in_game = True
        if in_game and not replaced and line == (old_line + "\r\n"):
            line = new_line + "\r\n"
            replaced = True
        sys.stdout.write(line)
    return replaced


def _retrosheet_filename(game_id, data_root):
    """Find the Retrosheet event file associated with a specific game id."""
    # game id is TTTYYYYMMDDN.
    team = game_id[:3]
    year = game_id[3:7]
    file_pattern = year + team + ".EV*"
    file_path = os.path.join(data_root, "retrosheet", year, file_pattern)
    file_matches = glob.glob(file_path)
    return file_matches[0] if len(file_matches) else None


def remove_pitch(game_id, pitch_id, data_root="data"):
    """Remove a specific pitch from an MLB Gameday file.

    Args:
        game_id: Retrosheet id of the game.
        pitch_id: GameDay id of the pitch to remove.
        data_root: Path to the root of the project data directory.
    Returns:
        bool: Whether the pitch was successfully removed.
    """
    pitch_search = ".//pitch[@id='{}']".format(pitch_id)
    return _remove_gameday_object(game_id, pitch_search, data_root)


def remove_at_bat(game_id, at_bat_number, data_root="data"):
    """Remove a specific at-bat (plate appearance) from an MLB Gameday file.

    Args:
        game_id: Retrosheet id of the game.
        at_bat_number: Number of the at-bat to remove.
        data_root: Path to the root of the project data directory.
    Returns:
        bool: Whether the at-bat was successfully removed.
    """
    at_bat_search = ".//atbat[@num='{}']".format(at_bat_number)
    return _remove_gameday_object(game_id, at_bat_search, data_root)


def _remove_gameday_object(game_id, object_search, data_root):
    """Generic function for removing an object from a GameDay XML tree."""
    game_file = _gameday_pitch_filename(game_id, data_root)
    # If the file doesn't exist, we're done.
    if not game_file:
        return False

    gameday_tree = ET.parse(game_file)
    object_parent_search = object_search + "/.."
    target_object = gameday_tree.find(object_search)
    # If the target object isn't in the parse tree, we're done.
    if not target_object:
        return False

    target_parent = gameday_tree.find(object_parent_search)
    target_parent.remove(target_object)
    gameday_tree.write(game_file)
    return True


def _gameday_pitch_filename(game_id, data_root):
    """Get the filename of the GameDay PitchFx file associated with a given Retrosheet game_id."""
    year = game_id[3:7]
    filename = os.path.join(data_root, "gameday", "pitches", year, game_id + ".xml")
    return filename if os.path.exists(filename) else None
