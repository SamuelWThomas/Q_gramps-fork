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
from gramps.gen.lib import Media
from gramps.gen.utils.file import media_path_full, relative_path, media_path
from gramps.gen.mime import get_type, is_image_type
from gramps.plugins.textreport.latex_helper import get_filename
from gramps.gen.db import DbTxn
from gramps.gen.lib.person import Person
from gramps.gen.lib.media import Media
import string
from gramps.gen.db import DbTxn
from gramps.gen.utils.file import media_path_full

alphabet = string.ascii_lowercase
handler.dbstate.db.disable_signals()
with DbTxn(msg="Rename imgs", grampsdb=handler.dbstate.db, batch=True) as trans:
    cursor = handler.dbstate.db.get_person_cursor()
    try:
        for handle, data in cursor:
            person = handler.dbstate.db.get_person_from_handle(handle)
            media_refs = person.get_media_list()
            media_count = len(media_refs)
            for index, media_ref in enumerate(media_refs):
                media_handle = media_ref.get_reference_handle()
                media = handler.dbstate.db.get_media_from_handle(media_handle)
                mime = media.get_mime_type()
                if is_image_type(mime):
                    media_path = media_path_full(handler.dbstate.db, media.get_path())
                    media_path = os.path.normpath(media_path)
                    base_name, file_extension = os.path.splitext(media_path)
                    file_extension = file_extension.lstrip(".")
                    directory = os.path.dirname(base_name + file_extension)
                    if media_count > 1:
                        suffix = alphabet[index]
                    else:
                        suffix = ""
                    filename_new = get_filename(
                        person, "img", suffix, file_extension, directory, ""
                    )
                    try:
                        os.rename(media_path, filename_new)
                        print(f"File renamed from {media_path} to {filename_new} successfully.")
                    except OSError as e:
                        print(f"Error renaming file: {e}")

                    media.set_path(filename_new)
                    handler.dbstate.db.commit_media(media, trans)
    except:
        pass

handler.dbstate.db.enable_signals()
handler.dbstate.db.request_rebuild()


cursor.close()


handler.cleanup()


if handler.dbstate.is_open():
    handler.dbstate.db.close()
sys.exit(0)
