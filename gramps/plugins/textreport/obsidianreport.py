# ------------------------------------------------------------------------
#
# standard python modules
#
# ------------------------------------------------------------------------
import os
import re

# ------------------------------------------------------------------------
#
# Gramps modules
#
# ------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale

_ = glocale.translation.gettext
from gramps.gen.lib import Person
from gramps.gen.plug.report import Report
from gramps.gen.plug.report import utils
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.plug.report import stdoptions
from gramps.gen.utils.file import media_path_full
from gramps.gen.datehandler import get_date
from gramps.gen.proxy import CacheProxyDb
from gramps.gen.plug.menu import DestinationOption, StringOption
from gramps.gen.plug import docgen
from gramps.gen.plug.docgen import (
    IndexMark,
    FontStyle,
    ParagraphStyle,
    FONT_SANS_SERIF,
    FONT_SERIF,
    INDEX_TYPE_TOC,
    PARA_ALIGN_CENTER,
)
from gramps.gen.display.place import displayer as _pd
from gramps.gen.display.name import displayer as _nd
from gramps.gen.lib import EventType, EventRoleType
from gramps.plugins.lib.libnarrate import Narrator
from gramps.gen.utils.grampslocale import GrampsLocale
from gramps.plugins.textreport.customnarrator import (
    CustomNarrator,
    FORMAT_NORMALTEXT,
    FORMAT_LATEX,
    FORMAT_MARKDOWN,
)


class ObsidianReportOptions(MenuReportOptions):
    def __init__(self, name, database):

        MenuReportOptions.__init__(self, name, database)

    def add_menu_options(self, menu):
        category_name = _("Obsidian Report Options")

        report_destination = DestinationOption("Destination:", "")
        report_destination.set_directory_entry(True)
        menu.add_option(category_name, "Destination", report_destination)

        frontmatter_tags = StringOption(
            "Frontmatter Tags:", "Genealogy, Person, Obsidian-Report"
        )
        menu.add_option(category_name, "Frontmatter Tags", frontmatter_tags)

        MenuReportOptions.load_previous_values(self)

    def make_default_style(self, default_style):
        font = FontStyle()
        font.set_size(16)
        font.set_type_face(FONT_SANS_SERIF)
        font.set_bold(1)
        para = ParagraphStyle()
        para.set_header_level(1)
        para.set_bottom_border(1)
        para.set_top_margin(utils.pt2cm(3))
        para.set_bottom_margin(utils.pt2cm(3))
        para.set_font(font)
        para.set_alignment(PARA_ALIGN_CENTER)
        para.set_description(_("The style used for the title."))
        default_style.add_paragraph_style("SR-Title", para)

        font = FontStyle()
        font.set_size(12)
        font.set_bold(True)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_top_margin(0)
        para.set_description(_("The style used for second level headings."))
        default_style.add_paragraph_style("SR-Heading", para)

        font = FontStyle()
        font.set_size(12)
        para = ParagraphStyle()
        para.set(first_indent=-0.75, lmargin=0.75)
        para.set_font(font)
        para.set_top_margin(utils.pt2cm(3))
        para.set_bottom_margin(utils.pt2cm(3))
        para.set_description(_("The basic style used for the text display."))
        default_style.add_paragraph_style("SR-Normal", para)


class ObsidianReport(Report):
    def __init__(self, database, options_class, user):

        Report.__init__(self, database, options_class, user)
        self.database = CacheProxyDb(self.database)

        self.set_locale("DE")

        self.__narrator = CustomNarrator(
            dbase=self.database,
            verbose=False,
            use_call_name=False,
            use_fulldate=True,
            empty_date="n/a",
            empty_place="",
            nlocale=self._locale,
            format=FORMAT_MARKDOWN,
        )

        menu_option_report_destination = self.options_class.menu.get_option_by_name(
            "Destination"
        )
        self.report_destination = menu_option_report_destination.get_value()

        menu_option_frontmatter_tags = self.options_class.menu.get_option_by_name(
            "Frontmatter Tags"
        )
        self.frontmatter_tags = menu_option_frontmatter_tags.get_value()
        self.frontmatter_tags = self.frontmatter_tags.replace(" ", "").split(",")

        self.gender_value_map = {
            Person.MALE: "M",
            Person.FEMALE: "F",
            Person.UNKNOWN: "?",
        }

        self.family_relationship_map = {
            0: "verheiratet",
            1: "unverheiratet",
            2: "standesamtlich",
            3: "unbekannt",
            4: "andere",
        }

    def write_report(self):

        with self.database.get_person_cursor() as cursor:
            for handle, pers in cursor:
                individual_aq = {
                    "ID": "",
                    "GrID": "",
                    "geschlecht": "",
                    "picture": "",
                    "displayname": "",
                    "nachname": "",
                    "vornamen": "",
                    "rufname": "",
                    "spitzname": "",
                    "titel": "",
                    "alias": "",
                    "suffix": "",
                    "geboren": "",
                    "getauft": "",
                    "gestorben": "",
                    "begraben": "",
                    "familie": "",
                    "notitzen": "",
                    "beruf": "",
                    "abstammung": "",
                    "mutter": "",
                    "vater": "",
                }

                person = self.database.get_person_from_handle(handle)
                self.__narrator.set_subject(person)

                name = _nd.display(person)
                individual_aq["displayname"] = name

                surnames = person.primary_name.surname_list
                if len(surnames) > 0:
                    individual_aq["alias"] = surnames[0].prefix
                    individual_aq["nachname"] = surnames[0].surname
                individual_aq["vornamen"] = person.primary_name.first_name
                individual_aq["rufname"] = person.primary_name.call
                individual_aq["spitzname"] = person.primary_name.nick
                individual_aq["titel"] = person.primary_name.title
                individual_aq["suffix"] = person.primary_name.suffix

                individual_aq["geschlecht"] = self.gender_value_map[person.get_gender()]

                event_refs = person.get_primary_event_ref_list()
                events = [
                    event
                    for event in [
                        self.database.get_event_from_handle(ref.ref)
                        for ref in event_refs
                    ]
                    if event.get_type() == EventType(EventType.OCCUPATION)
                ]
                if len(events) > 0:
                    events.sort(key=lambda x: x.get_date_object())
                    occupation = events[-1].get_description()
                    if occupation:
                        individual_aq["beruf"] = occupation
                individual_aq["GrID"] = str(person.get_gramps_id())
                individual_aq["ID"] = person.get_latex_id()

                text = self.__narrator.get_born_string()
                individual_aq["geboren"] = text if text else ""

                text = self.__narrator.get_baptised_string()
                individual_aq["getauft"] = text if text else ""

                if individual_aq["getauft"] == "":
                    text = self.__narrator.get_christened_string()
                    individual_aq["getauft"] = text if text else ""

                text = self.__narrator.get_died_string(include_age=True)
                individual_aq["gestorben"] = text if text else ""

                text = self.__narrator.get_buried_string()
                individual_aq["begraben"] = text if text else ""

                # Family (Parents)========================================
                family_handle = person.get_main_parents_family_handle()
                if family_handle:
                    family = self.database.get_family_from_handle(family_handle)
                    mother_handle = family.get_mother_handle()
                    father_handle = family.get_father_handle()
                    if mother_handle:
                        mother = self.database.get_person_from_handle(mother_handle)
                        individual_aq["mutter"] = (
                            "[[" + self.determine_filename(mother, False) + "]]"
                        )
                    if father_handle:
                        father = self.database.get_person_from_handle(father_handle)
                        individual_aq["vater"] = (
                            "[[" + self.determine_filename(father, False) + "]]"
                        )
                # ========================================================

                # Family (Partners)=======================================
                partner = ""
                for family_handle in person.get_family_handle_list():
                    family = self.database.get_family_from_handle(family_handle)
                    spouse_handle = utils.find_spouse(person, family)
                    if spouse_handle:
                        spouse = self.database.get_person_from_handle(spouse_handle)

                        mdate = ""
                        place = ""
                        event = utils.find_marriage(self.database, family)
                        if event:
                            mdate = self._locale.get_date(event.get_date_object())
                            place_handle = event.get_place_handle()
                            if place_handle:
                                place_obj = self.database.get_place_from_handle(
                                    place_handle
                                )
                                place = _pd.display_event(self.database, event, fmt=-1)
                        relationship = family.get_relationship()

                        partner += (
                            "1. [[" + self.determine_filename(spouse, False) + "]]"
                        )
                        if mdate or place or relationship:
                            partner += " ("
                            partner += (
                                (
                                    self.family_relationship_map[relationship.value]
                                    + ": "
                                )
                                if relationship
                                else ""
                            )
                            partner += (mdate + " ") if mdate else ""
                            partner += ("in [[" + place + "]]") if place else ""
                            partner += ")"
                        partner += "\n"

                    kinder = family.get_child_ref_list()
                    if len(kinder) > 0:
                        for kind_ref in kinder:
                            child_handle = kind_ref.ref
                            kind = self.database.get_person_from_handle(child_handle)
                            partner += (
                                "    1. [["
                                + self.determine_filename(kind, False)
                                + "]]\n"
                            )

                individual_aq["familie"] = partner
                # ========================================================

                notelist = person.get_note_list()
                if len(notelist) > 0:
                    note_counter = 0
                    for notehandle in notelist:
                        note = self.database.get_note_from_handle(notehandle)
                        note_text = str(note.get())
                        individual_aq["notitzen"] += self.note_to_markdown(note_text)
                        note_counter += 1
                        if note_counter < len(notelist):
                            individual_aq["notitzen"] += "\\\\\r"

                # Pictures================================================
                # ========================================================

                # find file(s) that match the person's Gramps-ID
                file_search = ["(" + individual_aq["GrID"] + ")"]
                file_dir_list = os.listdir(self.report_destination)
                file_list = [
                    nm for ps in file_search for nm in file_dir_list if ps in nm
                ]
                filename = ""
                designated_filename = self.determine_filename(person, True)
                if len(file_list) == 1:
                    # md-file with correct Gramps-ID exists
                    filename = file_list[0]
                    # check if this filename still matches the determined filename of the person
                    if filename != designated_filename:
                        # rename file
                        os.rename(
                            self.complete_filename_with_path(filename),
                            self.complete_filename_with_path(designated_filename),
                        )
                        filename = designated_filename

                elif len(file_list) == 0:
                    # file does not exist --> create
                    try:
                        open(
                            self.complete_filename_with_path(designated_filename), "a"
                        ).close()
                        filename = designated_filename
                    except:
                        pass
                else:
                    # multiple files with the same ID exist
                    # --> confusion!
                    print(
                        f"There are multiple files with the Gramps-ID {individual_aq['GrID']}"
                    )
                    continue

                break
                # write to file
                self.write_output_to_file(
                    self.complete_filename_with_path(filename), individual_aq
                )

    def note_to_markdown(self, text: str):
        text = re.sub(r" \.", ".", text)  # remove space before dot
        text = re.sub("„", '"', text)  # lower typog. quote
        text = re.sub("“", '"', text)  # upper typog. quote
        text = re.sub("”", '"', text)  # upper typog. quote
        text = re.sub("–", "--", text)  # replace a long hyphen by two normal hyphens
        text = re.sub("—", "--", text)  # long hyphens—
        text = re.sub(
            r"([0-9]{2})([0-9]{2}) ??-+? ??([0-9]{2})([^0-9]+)", r"\1\2--\1\3\4", text
        )  # 1941-42 --> 1941--1942
        text = re.sub(r"(?P<digit>\d),5", r"\g<digit>1/2", text)  # ,5 -> 1/2
        text = re.sub(r"(?P<digit>\d),25", r"\g<digit>1/4", text)  # ,25 -> 1/4
        # text = re.sub(r"[1]/([234])([^0-9])", r"\\nicefrac{1}{\1}\2", text) #make fraction
        text = re.sub(r" {2,}", " ", text)  # double space
        text = re.sub(r" {1,}([.,?!])", r"\1", text)  # spaces before punctuation marks
        text = re.sub(r"\(= (.*?)\)", r"(= \1)", text)  # protected space after "="
        text = re.sub(" - ", " -- ", text)  # long hyphens
        text = re.sub(r"(\d) [-–] (\d)", r"\1--\2", text)  # 2000 - 2001 --> 2000--2001
        text = re.sub(r"(\d)[-–](\d)", r"\1--\2", text)  # 2000-2001 --> 2000--2001
        text = re.sub(r"(\d) -- (\d)", r"\1--\2", text)  # 2000 -- 2001 --> 2000--2001
        # format dates:
        text = re.sub(
            r"([0-9]+)\.([0-9]+)\.([\d]{4})", r"[[\3-\2-\1]]", text
        )  # formats dates for Latex' DateTime2
        # compile markups:
        text = re.sub(r"\_(.*?)\_", r"^[\1]", text)  # _.._ will be treated as footnote
        text = re.sub(
            r"\#(.*?)\#", r"### \1", text
        )  # #..# will be treated as subsubheading
        text = re.sub(r"@(.*?)@", r"*\1*", text)  # @..@ will be formatted as italic

        text = re.sub(r"[\r\n]+", "\\r\\n", text, 0, re.MULTILINE)  # delete emtpy lines

        return text

    def determine_filename(self, person: Person, extension: bool) -> str:
        nachname = person.get_nachname()
        if not nachname or nachname == "..." or nachname == "?":
            nachname = "UNBEKANNT"
        vorname = person.get_primary_name().get_first_name()
        if not vorname or vorname == "..." or vorname == "?":
            gender = self.gender_value_map[person.get_gender()]
            vorname = "UNBEKANNT-" + gender
        nickname = person.get_nick_name()
        if nickname:
            nickname = f" ({nickname})"
        gramps_id = person.get_gramps_id()
        filename = nachname + ", " + vorname + nickname + " (" + gramps_id + ")"
        filename = re.sub(r"[\*\"\#\\\/\<\>\:\|\?\=\^\[\]\.]", "", filename)
        if extension:
            filename = filename + ".md"
        return filename

    def complete_filename_with_path(self, filename: str) -> str:
        complete_filename = os.path.join(self.report_destination, filename)
        return complete_filename

    def write_output_to_file(self, filename: str, content: dict):
        IDENTIFIER = r"%%Everything above this line will be refreshed automatically, do not change this line {Y8kp13Ma}%%"
        TAG_LINE = "tags: ["
        try:
            research_notes = ""
            tags_existing = []
            # read the file lines
            with open(filename, "r", encoding="UTF-8") as fr:
                lines = fr.readlines()
                research_notes_section = False
                for line in lines:
                    if research_notes_section:
                        research_notes += line
                    else:
                        if line.strip("\n") == IDENTIFIER:
                            research_notes_section = True
                            research_notes += line
                        if line.strip("\n").startswith(TAG_LINE):
                            tags_existing = (
                                line.strip("\n")
                                .replace(TAG_LINE, "")
                                .replace(" ", "")
                                .replace("]", "")
                                .split(",")
                            )

            tags_all = list(set(self.frontmatter_tags + tags_existing))
            tags_all.sort()
            tags_all = ", ".join(tags_all)
            # write the file lines except the start_key until the stop_key
            with open(filename, "w", encoding="UTF-8") as fw:
                frontmatter = (
                    f"---\n"
                    f"tags: [{tags_all}]\n"
                    f"aliases: []\n"
                    f"born: \n"
                    f"died: \n"
                    f'gender: {content["geschlecht"]}\n'
                    f'ID: { content["GrID"] }\n'
                    f"---\n\n"
                )
                fw.write(frontmatter)

                fw.write(
                    "# Informationen\n"
                    "## Biografische Daten\n"
                    f'- Geschlecht: {content["geschlecht"]}\n'
                    f'- {content["geboren"]}\n'
                    f'- {content["getauft"]}\n'
                    f'- {content["gestorben"]}\n'
                    f'- {content["begraben"]}\n'
                    f'- Beruf: {content["beruf"]}\n'
                    "\n"
                )

                fw.write(
                    "## Name\n"
                    f'- Geburtsname: {content["nachname"]}\n'
                    f'- Vornamen: {content["vornamen"]}\n'
                    f'- Rufname: {content["rufname"]}\n'
                    f'- Spitzname: {content["spitzname"]}\n'
                    f'- Titel: {content["titel"]}\n'
                    f'- Alias: {content["alias"]}\n'
                    f'- Suffix: {content["suffix"]}\n'
                    "\n"
                )

                fw.write(
                    "## Familie\n"
                    f'- Mutter: {content["mutter"]}\n'
                    f'- Vater: {content["vater"]}\n'
                    "\n"
                )

                fw.write("## Partnerschaft\n" f'{content["familie"]}' "\n")

                fw.write("## Biografie\n" f'{content["notitzen"]}\n\n')

                fw.write("# Research Notes\n")
                if not research_notes_section:
                    # No exisitng research notes found, add identifier
                    fw.write(IDENTIFIER + "\n")
                fw.write(research_notes)
        except RuntimeError as ex:
            print(f"erase error:\n\t{ex}")

        return
