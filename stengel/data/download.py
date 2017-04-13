from __future__ import (absolute_import, division,
                        print_function, unicode_literals)

import os
import zipfile
import time
import math
import random
import socket

from six.moves import urllib
import bs4


def create_directory_if_needed(directory):
    """Creates the specified directory if it doesn't already exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)


def is_connected(test_connection=("www.google.com", 80)):
    """Test if an internet connection is active and available.

    Args:
        test_connection: URL and port of the site to try to reach. Default is Google.
    """
    try:
        socket.create_connection(test_connection)
        return True
    except OSError:
        pass
    return False


def metered_delay(mean, sd):
    """Decorator to add a stochastic delay to a function call.

    Args:
        mean: Mean delay, in log(seconds).
        sd: Standard deviation of delay, in log(seconds).
    Returns:
        Evaluates the decorated function after a random delay chosen from a lognormal
        distribution with the given parameters.
    """
    if sd <= 0:
        raise ValueError("sd must be strictly positive.")

    def wrap(func):
        def wrapped_func(*args, **kwargs):
            delay_time = math.exp(random.gauss(mean, sd))
            time.sleep(delay_time)
            return func(*args, **kwargs)
        return wrapped_func
    return wrap


@metered_delay(-0.2, 0.2)
def gameday_pitches(game_, destination_root="data/gameday"):
    """Download the MLB GameDay PitchFx data associated with a given game.

    Args:
        game_: A Game object.
        destination_root: Root of the path to save the GameDay file in.
    Returns:
        Saves the PitchFx data file inside
        [destination_root]/[year_of_game]/[retrosheet_id].xml.
    """

    year, month, day = game_.metadata.year_month_day()
    destination_path = os.path.join(destination_root, "pitches", year)
    create_directory_if_needed(destination_path)

    source_url = game_.metadata.gameday_url() + "/inning/inning_all.xml"
    destination_file = os.path.join(destination_path, game_.metadata.id_ + ".xml")
    urllib.request.urlretrieve(source_url, destination_file)


def retrosheet_players(destination_root="data/retrosheet"):
    """Download basic information on every player in the Retrosheet database.

    Retrosheet.org has an html page that contains a CSV with the first name, last name,
    Retrosheet identifier, and MLB debut of every player in the database.

    Args:
        destination_root: Root of the path to save the file in.
    Returns:
        The name of the file that was created. Saves the Retrosheet file in 
        [destination_root]/player_ids.csv.
    """
    source_site = "http://www.retrosheet.org/retroID.htm"
    # There are a couple of blank lines at the top of the file that we want to ignore.
    num_junk_rows = 2

    create_directory_if_needed(destination_root)
    source_page = urllib.request.urlopen(source_site).read()
    source_soup = bs4.BeautifulSoup(source_page, "lxml")
    # The data is on an html page with a bunch of other cruft; the actual data is inside the
    # only <pre> tag in the page.
    source_data = source_soup.pre.string
    source_lines = source_data.split("\n")[num_junk_rows:]

    destination_path = os.path.join(destination_root, "player_ids.csv")
    with open(destination_path, "w") as outfile:
        for line in source_lines:
            outfile.write(line + "\n")
    return destination_path


@metered_delay(-0.8, 0.2)
def retrosheet_player(player_id, destination_root="data/retrosheet"):
    """Download detailed information about a single player in the Retrosheet database.

    In addition to the basic identifiers and information in the file downloaded by
    retrosheet_players, there is also a page with detailed information about every single
    player in the Retrosheet database. This function downloads the Retrosheet page for a
    single player.

    Args:
        player_id: Retrosheet ID of the player record to download.
        destination_root: Root of the path to save the file in.
    Returns:
        The name of the file that was created. Saves the Retrosheet file in
        [destination_root]/players/[player_id].html.
    """
    source_root = "http://www.retrosheet.org/boxesetc"
    last_initial = player_id[0].upper()
    source_url = source_root + "/{}/P{}.htm".format(last_initial, player_id)

    destination_path = os.path.join(destination_root, "players")
    create_directory_if_needed(destination_path)
    destination_file = os.path.join(destination_path, player_id + ".html")
    urllib.request.urlretrieve(source_url, destination_file)
    return destination_file


def retrosheet_season(year, destination_root="data/retrosheet"):
    """Download a full season of Retrosheet game files.

    The season file is available as a zip archive; the archive is automatically unzipped
    and the uncompressed files are saved in the specified folder.

    Args:
        year: Year of the season to download.
        destination_root: Root of the path to save the files in.
    Side Effects:
        Saves all of the files in [destination_root]/[year].
    """
    source_site = "http://www.retrosheet.org/events/"
    destination_path = os.path.join(destination_root, str(year))
    create_directory_if_needed(destination_path)
    
    season_file = "{:1}eve.zip".format(year)
    season_url = source_site + season_file
    destination_file = os.path.join(destination_path, season_file)
    urllib.request.urlretrieve(season_url, destination_file)
    
    with zipfile.ZipFile(destination_file) as season_zip:
        season_zip.extractall(destination_path)
    os.remove(destination_file)
