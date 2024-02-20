# start with:
# python3 -m debugpy --listen 5678 --wait-for-client createnewbook.py -O test -a book -p name=FamV-short -u
import os
import shutil
import sys
import tempfile
from typing import Any, Dict, List

import gramps.grampsapp as app
from gramps.cli.plug import CommandLineReport, cl_book, cl_report
from gramps.gen.config import config
from gramps.gen.const import HOME_DIR, PLUGINS_DIR, USER_PLUGINS
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
from gramps.plugins.textreport.latex_helper import get_filename


def extract_key_value_pairs(
    filename: str, marker_start="%{", marker_end="}"
) -> Dict[str, Dict[str, Any]]:
    """Extracts key-value pairs from a text file

    Args:
        filename (str): A utf-8 encoded filename to extract key/value pairs from
        marker_start (str, optional): Marker for the start of key/value pairs. Defaults to "%{".
        marker_end (str, optional): Marker for the end of key/value pairs. Defaults to "}".

    Returns:
        Dict[Dict[str,Any]]: returns a Dictionary of Dictionaries that contain the tag/value pairs in lower case
    """
    result = {}

    with open(filename, encoding="utf-8") as file:
        for line in file:
            dictionary = get_key_value_pair(line, marker_start, marker_end)
            # only append the dictionary if it has a least a GrID:
            if "grid" in dictionary:
                result[dictionary["grid"]] = dictionary
    return result


def get_key_value_pair(line: str, marker_start="%{", marker_end="}"):
    delimiters = [", ", "; ", "/ ", "/", ",", ";", " "]
    dictionary = {}
    line = line.strip()
    for delimiter in delimiters:
        line = line.replace(delimiter, ",")
    if line.startswith(marker_start) and line.endswith(marker_end):
        line = line[2:-1]
        pairs = line.split(",")
        for pair in pairs:
            key_value = pair.strip().split("=")
            key = key_value[0].strip().lower()
            value = key_value[1].strip().lower()
            # Convert specific tag values to boolean
            if value in ["true", "yes", "y"]:
                value = True
            if value in ["false", "no", "n"]:
                value = False
            dictionary[key] = value
    return dictionary


def write_subfile_info(db, tex_file: str):
    # Create a temporary file to store the modified content
    temp_file_path = tempfile.mkstemp()[1]

    with open(tex_file, "r") as input_file, open(temp_file_path, "w") as temp_file:
        previous_line = ""
        for line in input_file:
            line_ = line.strip()
            d = get_key_value_pair(previous_line)
            if d and "grid" in d.keys() and d["grid"] != "":
                person = db.get_person_from_gramps_id(d["grid"].upper())
                direction = d.get("direction", "down")
                filename = os.path.basename(
                    get_filename(person, "latex-" + direction, "", "", "", "")
                )
                if line_.startswith("\subfile{"):
                    temp_file.write("\subfile{" + filename + "}\n")
                else: 
                    temp_file.write("\subfile{" + filename + "}\n")
                    temp_file.write(line + "\n")
            else:
                temp_file.write(line_ + "\n")

            previous_line = line_

    # Replace the original file with the temporary file
    shutil.copyfile(temp_file_path, tex_file)


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

# from gramps.cli.grampscli import startcli

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
name = options_str_dict.pop("name", None)  # "FamV-short" # Book Name
tex_file = "C:\\Users\\andreas.quentin\\OneDrive\\Documents\\Ahnenblatt\\07 Latex\\00-Maindoc-test.tex"
maindoc = extract_key_value_pairs(tex_file)

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
        err_msg = "Failed to make '%s' report."
        try:
            for rpt, name in rptlist:
                if newpage:
                    doc.page_break()
                newpage = 1
                # rpt.begin_report()
                # rpt.write_report()
            doc.close()
        except ReportError as msg:
            (msg1, msg2) = msg.messages()
            print(err_msg % name, file=sys.stderr)  # which report has the error?
            print(msg1, file=sys.stderr)
            if msg2:
                print(msg2, file=sys.stderr)
    else:
        print("Creating a temporary new book with name: " + name)
        from gramps.gen.const import CUSTOM_FILTERS
        from gramps.gen.filters import (
            FilterList,
            GenericFilterFactory,
            reload_custom_filters,
        )
        from gramps.gen.filters.rules import Rule
        from gramps.gen.filters.rules.person import IsLessThanNthGenerationAncestorOf
        from gramps.gen.filters.rules.person.isdescendantfamilyofinlessthannthgeneration import (
            IsDescendantFamilyOfInLessThanNthGeneration,
        )

        filterdb = FilterList(CUSTOM_FILTERS)
        filterdb.load()
        filters = filterdb.get_filters("Person")
        filter_dict = filterdb.get_filters_dict(namespace="Person")

        newbookname = "temp-" + name
        # generate filters:
        filters_generated = []
        i = 0
        for person, person_options in maindoc.items():
            # look for value of direction, default to down:
            direction = person_options.get("direction", "down")
            # TODO: look for more parameters

            new_filter = GenericFilterFactory("Person")()
            filter_name = newbookname + "-" + person + "-" + direction
            if filter_name in filter_dict:
                filters.remove(filter_dict[filter_name])
            new_filter.set_name(filter_name)
            new_filter.set_comment("new")

            for ruleid in range(i):
                id, params = list(maindoc.items())[ruleid]
                if params.get("direction", "down") == "down":
                    # labels = [_("ID:"), _("Number of generations:"), _("Inclusive:"), _("Exclude:")]
                    rule = IsDescendantFamilyOfInLessThanNthGeneration(
                        arg=[
                            id.upper(),
                            str(int(params.get("generations", "3")) - 1),
                            "1",
                            "",
                        ],
                        use_regex=False,
                    )
                elif params.get("direction", "down") == "up":
                    # labels = [ _('ID:'), _('Number of generations:') ]
                    rule = IsLessThanNthGenerationAncestorOf(
                        arg=[id.upper(), str(int(params.get("generations", "3")) - 0)],
                        use_regex=False,
                    )
                new_filter.add_rule(rule)
            i = i + 1
            new_filter.set_invert(True)
            new_filter.set_logical_op("or")
            filterdb.add("Person", new_filter)
            filters_generated.append(filter_name)
        filterdb.save()
        reload_custom_filters()
        # new FilterList object to prevent reading from previous cache.
        filterdb = FilterList(CUSTOM_FILTERS)
        filterdb.load()
        filters = filterdb.get_filters("Person")
        filter_dict = filterdb.get_filters_dict(namespace="Person")
        # temporyry filters are created, reloading done,
        # for filter cleanup see below
        # creating the book:
        from gramps.gen.plug.report import Book, BookItem

        book = Book()
        book.set_name("temp-" + newbookname)
        book.set_dbname(handler.dbstate.db.get_dbid())  # not: db.get_dbname()

        # prerequisites for CLI reports:
        clr = CommandLineReport(
            handler.dbstate.db, name, CATEGORY_BOOK, ReportOptions, options_str_dict
        )

        doc = clr.format(
            None,
            PaperStyle(
                clr.paper, clr.orien, clr.marginl, clr.marginr, clr.margint, clr.marginb
            ),
        )
        doc.filename = os.path.join(HOME_DIR)
        user = User()
        rptlist = []
        selected_style = StyleSheet()

        #  book items:
        filter_offset = 6  # offset by the number of regular filters
        for person, person_options in maindoc.items():
            direction = person_options.get("direction", "down")
            generations = int(person_options.get("generations", "3"))
            if direction == "down":
                book_item = BookItem(handler.dbstate.db, "LaTeX-Report-down")
            else:
                book_item = BookItem(handler.dbstate.db, "LaTeX-Report-up")

            new_opt_dict = book_item.option_class.handler.options_dict
            new_opt_dict["pid"] = person.upper()
            new_opt_dict["filter"] = (
                filters.index(filter_dict[newbookname + "-" + person + "-" + direction])
                + filter_offset
            )
            new_opt_dict["numbering"] = "Henry"
            new_opt_dict["structure"] = "by generation"
            new_opt_dict["gen"] = generations
            new_opt_dict["inc_id"] = int(person_options.get("ids", False))
            new_opt_dict["latex_format_output"] = person_options.get("format_output", False)
            new_opt_dict["create_trees"] = person_options.get("trees", False)
            new_opt_dict["name_format"] = 1
            new_opt_dict["place_format"] = -1
            new_opt_dict["incl_private"] = person_options.get("private", False)
            new_opt_dict["living_people"] = 99
            new_opt_dict["years_past_death"] = 0
            new_opt_dict["trans"] = "de"
            new_opt_dict["date_format"] = 7
            new_opt_dict["inctags"] = person_options.get("tags", False)
            new_opt_dict["verbose"] = person_options.get("parentage", True)
            new_opt_dict["fulldates"] = True
            new_opt_dict["computeage"] = True
            new_opt_dict["usecall"] = False
            new_opt_dict["listc"] = True
            new_opt_dict["listc_spouses"] = False
            new_opt_dict["incmates"] = True
            new_opt_dict["incmateref"] = False
            new_opt_dict["incevents"] = False
            new_opt_dict["desref"] = True
            new_opt_dict["incphotos"] = person_options.get("pictures", False)
            new_opt_dict["incnotes"] = person_options.get("notes", True)
            new_opt_dict["incsources"] = False
            new_opt_dict["incsrcnotes"] = False
            new_opt_dict["incattrs"] = False
            new_opt_dict["incaddresses"] = False
            new_opt_dict["incnames"] = False
            new_opt_dict["incssign"] = True
            new_opt_dict["repdate"] = False
            new_opt_dict["incpaths"] = False
            new_opt_dict["repplace"] = False

            menu = book_item.option_class.menu
            for optname in new_opt_dict:
                menu_option = menu.get_option_by_name(optname)
                if menu_option:
                    menu_option.set_value(new_opt_dict[optname])

            book_item.option_class.set_document(doc)
            report_class = book_item.get_write_item()
            obj = (
                write_book_item(
                    handler.dbstate.db, report_class, book_item.option_class, user
                ),
                book_item.get_translated_name(),
            )
            if obj:
                append_styles(selected_style, book_item)
                rptlist.append(obj)

            book.append_item(book_item)

        doc.set_style_sheet(selected_style)
        doc.open(clr.option_class.get_output())
        doc.init()
        newpage = 0
        err_msg = "Failed to make '%s' report."
        try:
            for rpt, name in rptlist:
                rpt.begin_report()
                rpt.write_report()
                ...
            doc.close()
        except ReportError as msg:
            (msg1, msg2) = msg.messages()
            print(err_msg % name, file=sys.stderr)  # which report has the error?
            print(msg1, file=sys.stderr)
            if msg2:
                print(msg2, file=sys.stderr)

        clean_book_and_filters = False
        
        book_list.set_book(newbookname, book)
        if not clean_book_and_filters: book_list.save()
        book.clear()
        if clean_book_and_filters:
            # clean up generated filters (filter cleanup):
            for filter_generated in filters_generated:
                filters.remove(filter_dict[filter_generated])
        filterdb.save()
        write_subfile_info(dbstate.db, tex_file)

else:
    msg = ("Book name not given. " "Please use one of %(donottranslate)s=bookname.") % {
        "donottranslate": "[-p|--options] name"
    }

    print(("%s\n Available names are:") % msg, file=sys.stderr)
    for name in sorted(book_list.get_book_names()):
        print("   %s" % name, file=sys.stderr)

handler.cleanup()


if handler.dbstate.is_open():
    handler.dbstate.db.close()
sys.exit(0)
