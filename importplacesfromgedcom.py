def search_place_info(file_path, place_name):
    with open(file_path, "r", encoding="utf-8") as file:
        gedcom_data = file.read()

    places = gedcom_data.split("@")
    for i in range(1, len(places), 2):
        place_identifier = places[i]
        place_info = places[i + 1].split("\n")

        # Retrieve information for the current place
        name = ""
        note_lines = []
        web_address = ""
        latitude = ""
        longitude = ""
        gov_id = ""
        append_to_note = False

        for line in place_info:
            if line.startswith("1 NAME"):
                name = line.split(" ", 2)[2]
            elif line.startswith("1 NOTE"):
                append_to_note = True
                note_lines.append(line.split(" ", 2)[2])
            elif append_to_note and line.startswith("2 CONT"):
                note_lines[-1] += " " + line[7:]
            elif append_to_note and line.startswith("2 CONC"):
                note_lines[-1] += line[7:]
            elif line.startswith("1 SOUR"):
                web_address = line.split(" ", 2)[2]
            elif line.startswith("2 LATI"):
                latitude = line.split(" ", 2)[2]
            elif line.startswith("2 LONG"):
                longitude = line.split(" ", 2)[2]
            elif line.startswith("1 _GOV"):
                gov_id = line.split(" ", 2)[2]

        # Check if the current place matches the desired place_name
        if name.lower() == place_name.lower():
            note = " ".join(note_lines)
            return {
                "note": note,
                "website": web_address,
                "latitude": latitude,
                "longitude": longitude,
                "gov_id": gov_id,
            }

    return None


def usage():
    gedcom_file_path = "C:\\Users\\andreas.quentin\\downloads\\places.ged"
    place_name_to_search = "kjkj"

    result = search_place_info(gedcom_file_path, place_name_to_search)
    if result is not None:
        print("Note:", result["note"])
        print("Website:", result["website"])
        print("Latitude:", result["latitude"])
        print("Longitude:", result["longitude"])
        print("GOV-ID:", result["gov_id"])
    else:
        print("No matching place found.")


# start with:
# python3 -m debugpy --listen 5678 --wait-for-client importplacesfromgedcom.py -O test -u
import os
import sys

import gramps.grampsapp as app
from gramps.cli.plug import CommandLineReport, cl_book, cl_report
from gramps.gen.config import config
from gramps.gen.const import PLUGINS_DIR, USER_PLUGINS, HOME_DIR
from gramps.gen.constfunc import get_env_var, win
from gramps.gen.db.dbconst import DBBACKEND
from gramps.gen.db.exceptions import (
    DbConnectionError,
    DbPythonError,
    DbSupportedError,
    DbUpgradeRequiredError,
    DbVersionError,
)
from gramps.gen.db.utils import make_database
from gramps.gen.dbstate import DbState
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.errors import DbError, FilterError, ReportError
from gramps.gen.filters import reload_custom_filters
from gramps.gen.plug import BasePluginManager
from gramps.gen.plug.docgen import (
    PAPER_LANDSCAPE,
    PAPER_PORTRAIT,
    PaperStyle,
    StyleSheet,
    StyleSheetList,
    graphdoc,
    treedoc,
)
from gramps.gen.plug.report import (
    CATEGORY_BOOK,
    CATEGORY_CODE,
    CATEGORY_DRAW,
    CATEGORY_GRAPHVIZ,
    CATEGORY_TEXT,
    CATEGORY_TREE,
    BookList,
    ReportOptions,
    append_styles,
)
from gramps.gen.recentfiles import recent_files
from gramps.gen.utils.config import get_researcher

if "GRAMPS_RESOURCES" not in os.environ:
    resource_path, filename = os.path.split(os.path.abspath(__file__))
    resource_path, dirname = os.path.split(resource_path)
    os.environ["GRAMPS_RESOURCES"] = resource_path

app.build_user_paths()

from gramps.cli.argparser import ArgParser

argv_copy = sys.argv[:]
argpars = ArgParser(argv_copy)

# On windows the fontconfig handler is a better choice
if win() and ("PANGOCAIRO_BACKEND" not in os.environ):
    os.environ["PANGOCAIRO_BACKEND"] = "fontconfig"

from gramps.cli.grampscli import startcli

error = []
# startcli(error, argpars)
dbstate = DbState()

# we need a manager for the CLI session
from gramps.cli.user import User

user = User(auto_accept=argpars.auto_accept, quiet=argpars.quiet)

from gramps.cli.grampscli import CLIManager

climanager = CLIManager(dbstate, True, user)

# load the plugins
climanager.do_reg_plugins(dbstate, uistate=None)
reload_custom_filters()

# handle the arguments
from gramps.cli.arghandler import ArgHandler, _split_options

handler = ArgHandler(dbstate, argpars, climanager)

# handler.handle_args_cli()
# __open_action()
try:
    handler.smgr.open_activate(handler.open, handler.username, handler.password)
    print(("Opened successfully!"), file=sys.stderr)
except:
    print(("Error opening the file."), file=sys.stderr)
    print(("Exiting..."), file=sys.stderr)
    sys.exit(1)


pmgr = BasePluginManager.get_instance()
user = User()

from gramps.gen.lib.note import Note, NoteType
from gramps.gen.lib.url import Url, UrlType
from gramps.gen.db import DbTxn
import time
gedcom_file_path = "C:\\Users\\andreas.quentin\\downloads\\places.ged"
now = time.time()
cursor = handler.dbstate.db.get_place_cursor()
data = next(cursor)
while data:
    (handle, val) = data
    place = handler.dbstate.db.get_place_from_handle(handle)
    place_name_obj = place.get_name()
    place_name = place_name_obj.get_value()

    result = search_place_info(gedcom_file_path, place_name)
    if result is not None:
        note_text = result["note"]
        website = result["website"]
        lat = result["latitude"]
        long = result["longitude"]
        govid = result["gov_id"]

        if govid != "": place.set_code(govid)

        if note_text != "":
            note = Note(note_text)
            note.set_change_time(now)
            note.set_type(NoteType.PLACE)
            with DbTxn("Add Note",handler.dbstate.db) as trans:
                    handler.dbstate.db.add_note(note, trans)
            note_handle = note.get_handle()
            place.add_note(note_handle)

        if website != "":
            url = Url()
            url.set_path(website)
            url.set_type(UrlType.WEB_HOME)
            url.set_description("Eintrag im GenWiki")
            place.add_url(url)

        if govid != "" or note != "" or website != "":
            with DbTxn("Edit Place (%s)" % place_name,handler.dbstate.db) as trans:
                        handler.dbstate.db.commit_place(place, trans)

    data = next(cursor)
cursor.close()


handler.cleanup()


if handler.dbstate.is_open():
    handler.dbstate.db.close()
sys.exit(0)
