# start with:
# python3 -m debugpy --listen 5678 --wait-for-client createbook.py -O test -a book -p name=FamV-short,show=all -u
import os
import sys

import gramps.grampsapp as app
from gramps.cli.plug import CommandLineReport, cl_book, cl_report
from gramps.gen.config import config
from gramps.gen.const import PLUGINS_DIR, USER_PLUGINS
from gramps.gen.constfunc import get_env_var, win
from gramps.gen.db.dbconst import DBBACKEND
from gramps.gen.db.exceptions import (DbConnectionError, DbPythonError,
                                      DbSupportedError, DbUpgradeRequiredError,
                                      DbVersionError)
from gramps.gen.db.utils import make_database
from gramps.gen.dbstate import DbState
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.errors import DbError, FilterError, ReportError
from gramps.gen.filters import reload_custom_filters
from gramps.gen.plug import BasePluginManager
from gramps.gen.plug.docgen import (PAPER_LANDSCAPE, PAPER_PORTRAIT,
                                    PaperStyle, StyleSheet, StyleSheetList,
                                    graphdoc, treedoc)
from gramps.gen.plug.report import (CATEGORY_BOOK, CATEGORY_CODE,
                                    CATEGORY_DRAW, CATEGORY_GRAPHVIZ,
                                    CATEGORY_TEXT, CATEGORY_TREE, BookList,
                                    ReportOptions, append_styles)
from gramps.gen.recentfiles import recent_files
from gramps.gen.utils.config import get_researcher


def write_book_item(database, report_class, options, user):
    """Write the report using options set.
    All user dialog has already been handled and the output file opened."""
    try:
        return report_class(database, options, user)
    except ReportError as msg:
        (msg1, msg2) = msg.messages()
        print("ReportError", msg1, msg2, file=sys.stderr)
    except FilterError as msg:
        (msg1, msg2) = msg.messages()
        print("FilterError", msg1, msg2, file=sys.stderr)
    except:
        # LOG.error("Failed to write book item.", exc_info=True)
        ...
    return None


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
action, op_string = handler.actions[0]
# self.cl_action(action, op_string) #hanlder
pmgr = BasePluginManager.get_instance()
options_str_dict = _split_options(op_string)
name = name = options_str_dict.pop("name", None)  # "FamV-short" # Book Name
book_list = BookList("books.xml", dbstate.db)
if name:
    if name in book_list.get_book_names():
        # cl_book(handler.dbstate.db, name, book_list.get_book(name),options_str_dict)
        clr = CommandLineReport(
            handler.dbstate.db, name, CATEGORY_BOOK, ReportOptions, options_str_dict
        )

        doc = clr.format(
            None,
            PaperStyle(
                clr.paper, clr.orien, clr.marginl, clr.marginr, clr.margint, clr.marginb
            ),
        )
        user = User()
        rptlist = []
        selected_style = StyleSheet()
        book = book_list.get_book(name)
        for item in book.get_item_list():
            # The option values were loaded magically by the book parser.
            # But they still need to be applied to the menu options.
            opt_dict = item.option_class.options_dict
            menu = item.option_class.menu
            for optname in opt_dict:
                menu_option = menu.get_option_by_name(optname)
                if menu_option:
                    menu_option.set_value(opt_dict[optname])

            item.option_class.set_document(doc)
            report_class = item.get_write_item()
            obj = (
                write_book_item(
                    handler.dbstate.db, report_class, item.option_class, user
                ),
                item.get_translated_name(),
            )
            if obj:
                append_styles(selected_style, item)
                rptlist.append(obj)

        doc.set_style_sheet(selected_style)
        doc.open(clr.option_class.get_output())
        doc.init()
        newpage = 0
        err_msg = ("Failed to make '%s' report.")
        try:
            for rpt, name in rptlist:
                if newpage:
                    doc.page_break()
                newpage = 1
                #rpt.begin_report()
                #rpt.write_report()
            doc.close()
        except ReportError as msg:
            (msg1, msg2) = msg.messages()
            print(err_msg % name, file=sys.stderr)  # which report has the error?
            print(msg1, file=sys.stderr)
            if msg2:
                print(msg2, file=sys.stderr)

        # return
    msg = ("Unknown book name.")
else:
    msg = (
        "Book name not given. " "Please use one of %(donottranslate)s=bookname."
    ) % {"donottranslate": "[-p|--options] name"}

    print(("%s\n Available names are:") % msg, file=sys.stderr)
    for name in sorted(book_list.get_book_names()):
        print("   %s" % name, file=sys.stderr)


handler.cleanup()


if handler.dbstate.is_open():
    handler.dbstate.db.close()
sys.exit(0)
