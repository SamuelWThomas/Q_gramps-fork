# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2002 Bruce J. DeGrasse
# Copyright (C) 2000-2007 Donald N. Allingham
# Copyright (C) 2007-2012 Brian G. Matherly
# Copyright (C) 2008      James Friedmann <jfriedmannj@gmail.com>
# Copyright (C) 2009      Benny Malengier <benny.malengier@gramps-project.org>
# Copyright (C) 2010      Jakim Friant
# Copyright (C) 2010      Vlada Perić <vlada.peric@gmail.com>
# Copyright (C) 2011      Tim G L Lyons
# Copyright (C) 2013-2014 Paul Franklin
# Copyright (C) 2014      Gerald Kunzmann <g.kunzmann@arcor.de>
# Copyright (C) 2017      Robert Carnell <bertcarnell_at_gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

"""Reports/Text Reports/Detailed Ancestral Report"""

# ------------------------------------------------------------------------
#
# standard python modules
#
# ------------------------------------------------------------------------
import codecs
import csv
import math
import os
import re
import shutil
from functools import partial
from itertools import islice

import latex_helper

# ------------------------------------------------------------------------
#
# Gramps modules
#
# ------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.display.name import displayer as _nd
from gramps.gen.display.place import displayer as _pd
from gramps.gen.errors import ReportError
from gramps.gen.lib import EventRoleType, EventType, FamilyRelType, NoteType, Person
from gramps.gen.plug.docgen import (
    FONT_SANS_SERIF,
    FONT_SERIF,
    INDEX_TYPE_TOC,
    PARA_ALIGN_CENTER,
    FontStyle,
    IndexMark,
    ParagraphStyle,
)
from gramps.gen.plug.menu import BooleanOption, FilterOption, NumberOption, PersonOption
from gramps.gen.plug.report import (
    Bibliography,
    MenuReportOptions,
    Report,
    endnotes,
    stdoptions,
    utils,
)
from gramps.gen.proxy import CacheProxyDb
from gramps.gen.utils.alive import probably_alive
from gramps.gen.utils.db import get_participant_from_event
from gramps.gen.utils.file import create_checksum, media_path_full
from gramps.plugins.docgen.latexdoc import *
from gramps.plugins.lib.libnarrate import Narrator
from gramps.plugins.textreport.customnarrator import (
    FORMAT_LATEX,
    FORMAT_MARKDOWN,
    FORMAT_NORMALTEXT,
    CustomNarrator,
)

_ = glocale.translation.gettext

# ---------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------
#
# Constants
#
# ------------------------------------------------------------------------
EMPTY_ENTRY = "_____________"


# ------------------------------------------------------------------------
#
# DetAncestorReport
#
# ------------------------------------------------------------------------
class LatexUpReport(Report):
    """the Detailed Ancestor Report"""

    def __init__(self, database, options, user):
        """
        Create the DetAncestorReport object that produces the report.

        The arguments are:

        database        - the Gramps database instance
        options         - instance of the Options class for this report
        user            - a gen.user.User() instance

        This report needs the following parameters (class variables)
        that come in the options class.

        gen           - Maximum number of generations to include.
        inc_id        - Whether to include Gramps IDs
        pagebgg       - Whether to include page breaks between generations.
        pageben       - Whether to include page break before End Notes.
        firstName     - Whether to use first names instead of pronouns.
        fulldate      - Whether to use full dates instead of just year.
        listchildren  - Whether to list children.
        list_children_spouses - Whether to list the spouses of the children
        includenotes  - Whether to include notes.
        incattrs      - Whether to include attributes
        blankplace    - Whether to replace missing Places with ___________.
        blankDate     - Whether to replace missing Dates with ___________.
        calcageflag   - Whether to compute age.
        dupperson     - Whether to omit duplicate ancestors
                            (e.g. when distant cousins marry).
        verbose       - Whether to use complete sentences
        childref      - Whether to add descendant references in child list.
        addimages     - Whether to include images.
        pid           - The Gramps ID of the center person for the report.
        name_format   - Preferred format to display names
        other_events  - Whether to include other events.
        incl_private  - Whether to include private data
        living_people - How to handle living people
        years_past_death - Consider as living this many years after death
        """
        Report.__init__(self, database, options, user)

        self.map = {}
        self._user = user
        self.latex = [str]

        menu = options.menu
        get_option_by_name = menu.get_option_by_name
        get_value = lambda name: get_option_by_name(name).get_value()

        self.set_locale("de")
        self.__narrator = CustomNarrator(
            dbase=self.database,
            verbose=False,
            use_call_name=False,
            use_fulldate=True,
            empty_date="n/a",
            empty_place="",
            nlocale=self._locale,
            format=FORMAT_LATEX,
        )

        stdoptions.run_date_format_option(self, menu)
        stdoptions.run_private_data_option(self, menu)
        stdoptions.run_living_people_option(self, menu, self._locale)
        self.database = CacheProxyDb(self.database)
        self._db = self.database

        self.max_generations = get_value("gen")
        self.create_trees = get_value("create_trees")
        self.fulldate = get_value("fulldates")
        self.listchildren = get_value("listc")
        self.list_children_spouses = get_value("listc_spouses")
        self.inc_notes = get_value("incnotes")
        # TODO: Inc_mates als Option?
        self.inc_mates = True
        self.calcageflag = get_value("computeage")
        self.dupperson = get_value("omitda")
        self.verbose = get_value("verbose")
        self.childref = get_value("desref")
        self.addimages = get_value("incphotos")
        self.inc_tags = get_value("inc_tags")
        self.inc_tag = {
            key: value
            for key, value in options.options_dict.items()
            if key.startswith("inctag_")
        }
        self.inc_names = get_value("incnames")
        self.inc_events = get_value("incevents")
        self.other_events = get_value("incotherevents")
        self.inc_addr = get_value("incaddresses")
        self.inc_sources = get_value("incsources")
        self.inc_srcnotes = get_value("incsrcnotes")
        self.inc_attrs = get_value("incattrs")
        self.initial_sosa = get_value("initial_sosa")
        self.want_ids = get_value("inc_id")
        self.latex_format_output = get_value("latex_format_output")

        pid = get_value("pid")
        self.center_person = self._db.get_person_from_gramps_id(pid)
        if self.center_person is None:
            raise ReportError(_("Person %s is not in the Database") % pid)

        filter_option = options.menu.get_option_by_name("filter")
        self.filter = filter_option.get_filter()

        stdoptions.run_name_format_option(self, menu)
        self._nd = self._name_display

        self.place_format = menu.get_option_by_name("place_format").get_value()

        self.gen_handles = {}
        self.prev_gen_handles = {}

        self.bibli = Bibliography(Bibliography.MODE_DATE | Bibliography.MODE_PAGE)

    def apply_filter(self, person_handle, index):
        """recurse up through the generations"""
        if (not person_handle) or (index >= 2**self.max_generations):
            return
        self.map[index] = person_handle

        person = self._db.get_person_from_handle(person_handle)
        family_handle = person.get_main_parents_family_handle()
        if family_handle:
            family = self._db.get_family_from_handle(family_handle)
            self.apply_filter(family.get_father_handle(), index * 2)
            self.apply_filter(family.get_mother_handle(), (index * 2) + 1)

    def write_report(self):
        self.apply_filter(self.center_person.get_handle(), 1)

        # Apply additional filter as selected:
        if self.filter:
            self.filtered_subset = self.filter.apply(self._db, user=self._user)

        name = self._nd.display_name(self.center_person.get_primary_name())
        if not name:
            name = self._("Unknown")

        generation = 0

        for key in sorted(self.map):
            if generation == 0 or key >= 2**generation:
                text = self._("Generation %d") % (generation + 1)
                self.latex.append("\\generation{" + text + "}")
                generation += 1
                if self.childref:
                    self.prev_gen_handles = self.gen_handles.copy()
                    self.gen_handles.clear()

            person_handle = self.map[key]
            person = self._db.get_person_from_handle(person_handle)
            self.gen_handles[person_handle] = key

            dupperson = self.write_person(key)
            if dupperson == 0:  # Is this a duplicate ind record
                if self.listchildren or self.inc_events:
                    for family_handle in person.get_family_handle_list():
                        family = self._db.get_family_from_handle(family_handle)
                        mother_handle = family.get_mother_handle()
                        if (
                            mother_handle is None
                            or mother_handle not in iter(self.map.values())
                            or person.get_gender() == Person.FEMALE
                        ):
                            # The second test above also covers the 1. person's
                            # mate, which is not an ancestor and as such is not
                            # included in the self.map dictionary
                            if self.listchildren:
                                self.write_children(family)
                            if self.inc_events:
                                self.write_family_events(family)

                # ---------------------------------------------------------------------------------------------------

        if self.inc_sources:
            if self.pgbrkenotes:
                self.doc.page_break()
            # it ignores language set for Note type (use locale)
            endnotes.write_endnotes(
                self.bibli,
                self._db,
                self.doc,
                printnotes=self.inc_srcnotes,
                elocale=self._locale,
            )

        # Determine filename
        if self.doc._backend.filename:
            dir = os.path.dirname(self.doc._backend.filename)  # Stand-alone report
        else:
            dir = os.path.dirname(self.doc.filename)  # Report is part of a book
        filename = latex_helper.get_filename(
            self.center_person, "latex-up", "", "tex", dir, ""
        )
        # Write LaTeX Output to file:
        latex_helper.write_output_to_file(filename, self.latex)
        self.latex = []

        # Format file using latexindent:
        if self.latex_format_output:
            latex_helper.format_with_latexindent(filename)

    def append_bio_facts(self, person_data):
        biography = latex_helper.get_latex_biography(
            person_data, "kekule", self.want_ids
        )
        self.latex.append(biography)

    def _get_s_s(self, key):
        """returns Sosa-Stradonitz (a.k.a. Kekule or Ahnentafel) number"""
        generation = int(math.floor(math.log(key, 2)))  # 0
        gen_start = pow(2, generation)  # 1
        new_gen_start = self.initial_sosa * gen_start  # 3
        return new_gen_start + (key - gen_start)  # 3+0

    def write_person(self, key):
        """Output birth, death, parentage, marriage and notes information"""

        person_data = latex_helper.get_empty_indiviudal()

        person_handle = self.map[key]
        person = self._db.get_person_from_handle(person_handle)
        self.__narrator.set_subject(person)

        person_data["kekule"] = str(self._get_s_s(key))
        self.write_person_info(person, person_data)

        if self.dupperson:
            # Check for duplicate record (result of distant cousins marrying)
            for dkey in sorted(self.map):
                if dkey >= key:
                    break
                if self.map[key] == self.map[dkey]:
                    indiv = self._db.get_person_from_handle(self.map[key])
                    name = self._name_display.display(indiv)
                    if not name:
                        name = self._("Unknown")

                    indiv_sosa = self._get_s_s(key)
                    dublette = self._db.get_person_from_handle(self.map[dkey])
                    dublette_sosa = self._get_s_s(dkey)
                    text = "\\kekule{" + str(indiv_sosa) + "} =\enskip{}"
                    text += "\hyperref[" + latex_helper.get_latex_id(dublette) + "]{"
                    text += "\kekule{" + str(dublette_sosa) + "}" + name
                    text += (
                        "}\seitenzahlpunkte{"
                        + latex_helper.get_latex_id(dublette)
                        + "}"
                    )
                    self.latex.append(text + " " + "\n\n")

                    return 1  # Duplicate person

        if not key % 2 or key == 1:
            # latex_helper.write_marriage(
            #    self._db, self.__narrator, self._name_display, person, person_data
            # )
            # TODO: Hochzeiten werden bei beiden Partnern ausgegeben, etwas redundant...
            ...

        partners = []
        if key == 1:
            if self.inc_mates:
                letter = lambda n: chr(ord("a") + n) if 0 <= n <= 25 else ""
                partner_nr = 0
                for family_handle in person.get_family_handle_list():
                    family = self._db.get_family_from_handle(family_handle)
                    person_data_mate = latex_helper.get_empty_indiviudal()
                    person_data_mate["kekule"] = person_data["kekule"] + letter(
                        partner_nr
                    )
                    person_data_mate["partner"] = person
                    self.__write_mate(person, person_data_mate)
                    partners.append(person_data_mate)
                    partner_nr += 1

        self.append_bio_facts(person_data)
        for partner in partners:
            self.append_bio_facts(partner)

        return 0  # Not duplicate person

    def write_person_info(self, person: Person, person_data):
        """write out all the person's information"""
        name = self._name_display.display(person)
        if not name:
            name = self._("Unknown")
        self.__narrator.set_subject(person)

        # Name:
        person_data["displayname"] = name
        surnames = person.primary_name.surname_list
        if len(surnames) > 0:
            person_data["alias"] = surnames[0].prefix
            person_data["nachname"] = surnames[0].surname
        person_data["vornamen"] = person.primary_name.first_name
        person_data["rufname"] = person.primary_name.call
        person_data["spitzname"] = person.primary_name.nick
        person_data["titel"] = latex_helper.transform_abbreviations(
            person.primary_name.title
        )
        person_data["suffix"] = person.primary_name.suffix

        # is filtered out?
        if self.filter and self.filtered_subset:
            if not person.get_handle() in self.filtered_subset:
                person_data["filtered"] = self.filter.get_name()

        # IDs
        person_data["GrID"] = str(person.get_gramps_id())
        person_data["ID"] = latex_helper.get_latex_id(person)

        # Determine working directory:
        if self.doc._backend.filename:
            dir = os.path.dirname(self.doc._backend.filename)  # Stand-alone report
        else:
            dir = os.path.dirname(self.doc.filename)  # Report is part of a book

        # Trees
        if self.create_trees and not person_data["filtered"]:
            person_data["trees"] = ""
            trees = [
                latex_helper.tree_create(attr.get_value(), self._db, person, dir)
                for attr in person.get_attribute_list()
                if str(attr.get_type()) == "create_tree"
            ]
            for i, filename in enumerate(trees):
                if (
                    filename != ""
                ):  # filename will be '' if the tree definition was incorrect
                    filename_rel = os.path.relpath(filename, dir)
                    pattern = r"i\d{4}-(.*?)(?=-|\.)"  # Regular expression pattern to match "i" followed by 4 digits, and capture everything before the last period or dash
                    match = re.search(pattern, filename)
                    if match:
                        tree_type = match.group(1)
                        if tree_type.startswith("up"):
                            tree_type_text = "Vorfahrenbaum"
                        elif tree_type.startswith("down"):
                            tree_type_text = "Nachfahrenbaum"
                        elif tree_type.startswith("sand"):
                            tree_type_text = "Verwandtschaftsbaum"
                        else:
                            tree_type_text = "Stammbaum"
                    caption = tree_type_text + " " + person_data["displayname"]
                    # TODO: set the person's index in the caption and mark it with a * in the index
                    # caption += "\index[ind]{"+person_data["ID"]+"}"
                    label = os.path.split(filename)[1][:-6]
                    if len(trees) > 1 and i == 0:
                        person_data["treelinks"] += "Stammbäume: "
                    person_data[
                        "treelinks"
                    ] += f"\\treelink{{tree:{label}}}{{{tree_type_text}}}"
                    if i < (len(trees) - 1):
                        person_data["treelinks"] += ", "
                    hashtag = "#"
                    # level size sets the width od a node, node size the height!
                    person_data[
                        "trees"
                    ] += f"""\\begin{{tree*}}[p]
            \\centering
            %%\\resizebox{{\\textwidth}}{{!}}{{
            \\tikzsetnextfilename{{{filename_rel}}} 
            \\begin{{tikzpicture}}
            \\genealogytree[
                processing=database,
                template=database traditional,
                database format=short,
                timeflow=right,
                pref code={{\\rufname{{{hashtag}1}}}},
                surn code={{\\nachname{{{hashtag}1}}}},
                nick code={{\\spitzname{{{hashtag}1}}}},
                profession code={{}},
                list separators={{\\newline}}{{ }}{{}}{{}},
                place text={{\\newline}}{{}},
                name code={{\\gtrPrintSex~\\gtrDBname}},
                date format=yyyy,
                level size=30mm,
                node size from=8mm to 15mm,
                box={{valign=center}},
            ]{{
                input{{{filename_rel}}}
            }}
        \\end{{tikzpicture}}
        %}}
        \\caption[{caption}]{{{caption}}}
        \\label{{tree:{label}}}
    \\end{{tree*}}\n\n"""

        # Occupation:
        event_refs = person.get_primary_event_ref_list()
        events = [
            event
            for event in [self._db.get_event_from_handle(ref.ref) for ref in event_refs]
            if event.get_type() == EventType(EventType.OCCUPATION)
        ]
        if len(events) > 0:
            events.sort(key=lambda x: x.get_date_object())
            occupation = events[-1].get_description()
            if occupation:
                person_data["beruf"] = latex_helper.transform_abbreviations(occupation)

        # Tags:
        if self.inc_tags:
            tag_list = person.get_tag_list()
            vertical_adj = 13
            tag_no = 0
            if self.want_ids and len(tag_list) > 0:
                tag_no = 1
            for tag_handle in tag_list:
                tag = self.database.get_tag_from_handle(tag_handle)
                tag_opt = "inctag_" + tag.name
                if tag_opt in self.inc_tag and self.inc_tag[tag_opt]:
                    color = tag.color[-6:]
                    color_name = f"col_{tag.name}"
                    person_data["tags"] += "\\renewcommand*{\\marginnotevadjust}{"
                    person_data["tags"] += str(vertical_adj * tag_no)
                    person_data["tags"] += "pt}"
                    person_data[
                        "tags"
                    ] += f"\\definecolor{{{color_name}}}{{HTML}}{{{color}}}"
                    person_data[
                        "tags"
                    ] += f"\\tcbset{{doc marginnote={{colframe={color_name}!50!white,colback={color_name}!5!white,halign=center}}}}"
                    person_data[
                        "tags"
                    ] += f"\\tcbdocmarginnote{{\\textcolor{{{color_name}}}{{"
                    person_data["tags"] += tag.name
                    person_data["tags"] += "}}"
                    tag_no += 1
            person_data["tags"] += "\\renewcommand*{\\marginnotevadjust}{0pt}"

        # Pictures:
        photos = person.get_media_list()
        max_pics = 1
        # Check for an "pictures" attribute, the value of which determines the number of pics to include
        for attr in person.get_attribute_list():
            if str(attr.get_type()) == "pictures":
                max_pics = max(max_pics, int(attr.get_value()))
        if self.addimages and len(photos) > 0:
            for photo in islice(photos, max_pics):
                object_handle = photo.get_reference_handle()
                media = self._db.get_media_from_handle(object_handle)
                mime_type = media.get_mime_type()
                if mime_type and mime_type.startswith("image"):
                    filename = media_path_full(self._db, media.get_path())
                    # set caption:
                    caption = media.get_description()
                    if latex_helper.normalize_string(
                        caption
                    ) in latex_helper.normalize_string(
                        filename
                    ):  # caption is filename, replace by person's name
                        caption = (
                            person_data["titel"]
                            + " "
                            + person_data["vornamen"]
                            + " "
                            + person_data["nachname"]
                            + " "
                            + person_data["suffix"]
                        )
                        caption = caption.strip()

                    # set filename
                    checksum = media.get_checksum()
                    if not checksum:
                        checksum = create_checksum(filename)
                        media.set_checksum(checksum)
                    filename_new_short = os.path.basename(
                        latex_helper.get_filename(
                            person, "", str(checksum), "", dir, "pics"
                        )
                    )
                    filename_new = os.path.join(
                        dir, "pics", filename_new_short + ".jpg"
                    )
                    if not os.path.exists(filename_new):
                        os.makedirs(os.path.dirname(filename_new), exist_ok=True)
                    # set label:
                    label = "pic-" + filename_new_short

                    if os.path.exists(filename):
                        shutil.copy(filename, filename_new)
                        latex_image = ""
                        latex_image += "\\IfFileExists{%s}{\n" % latexescape(
                            "pics/" + filename_new_short + ".jpg"
                        )
                        latex_image += "\\begin{figure}[t] \n"
                        latex_image += "\\centering \n"
                        latex_image += (
                            "\\includegraphics[width=1\\linewidth]{%s} \n"
                            % latexescape("pics/" + filename_new_short)
                        )
                        latex_image += "\\caption[%s]{%s} \n" % (caption, caption)
                        latex_image += "\\label{fig:%s} \n" % label
                        latex_image += "\\end{figure}\n"
                        latex_image += (
                            "}{\\typeout{Image source file not found %s}}"
                            % latexescape("pics/" + filename_new_short)
                            + "\n"
                        )
                        person_data["picture"] += latex_image

        # Ortsliste
        # TODO: Ortsliste not implemented yet.

        # born:
        person_data["geboren"] = latex_helper.transform_abbreviations(
            self.__narrator.get_born_string()
        )

        # baptised / christened:
        text = self.__narrator.get_baptised_string()
        if not text:
            text = self.__narrator.get_christened_string()
        person_data["getauft"] = latex_helper.transform_abbreviations(text)

        # Write Death and/or Burial text only if not probably alive
        if not probably_alive(person, self.database):
            person_data["gestorben"] = latex_helper.transform_abbreviations(
                self.__narrator.get_died_string(self.calcageflag)
            )
            person_data["begraben"] = latex_helper.transform_abbreviations(
                self.__narrator.get_buried_string()
            )

        # Parents:
        if self.verbose:
            latex_helper.write_parents(self._db, person, person_data)

        # Partners:
        if not "partner" in person_data or person_data["partner"] == None:
            latex_helper.write_marriage(
                self._db, self.__narrator, self._name_display, person, person_data
            )

        # Notes:
        notelist = person.get_note_list()
        if len(notelist) > 0 and self.inc_notes:
            note_counter = 0
            for notehandle in notelist:
                note = self._db.get_note_from_handle(notehandle)
                person_data["notitzen"] += latex_helper.format_note(
                    note.get_styledtext()
                )
                note_counter += 1
                if note_counter < len(notelist):
                    person_data["notitzen"] += "\\\\\r"

    def write_children(self, family):
        """
        List children.
        :param family: Family
        :return:
        """

        if not family.get_child_ref_list():
            return

        mother_handle = family.get_mother_handle()
        if mother_handle:
            mother = self._db.get_person_from_handle(mother_handle)
            mother_name = self._nd.display(mother)
            if not mother_name:
                mother_name = self._("Unknown")
        else:
            mother_name = self._("Unknown")

        father_handle = family.get_father_handle()
        if father_handle:
            father = self._db.get_person_from_handle(father_handle)
            father_name = self._nd.display(father)
            if not father_name:
                father_name = self._("Unknown")
        else:
            father_name = self._("Unknown")

        self.doc.start_paragraph("DAR-ChildTitle")
        self.doc.write_text(
            self._("Children of %(mother_name)s and %(father_name)s")
            % {"father_name": father_name, "mother_name": mother_name}
        )
        self.doc.end_paragraph()

        cnt = 1
        for child_ref in family.get_child_ref_list():
            child_handle = child_ref.ref
            child = self._db.get_person_from_handle(child_handle)
            child_name = self._nd.display(child)
            if not child_name:
                child_name = self._("Unknown")
            child_mark = utils.get_person_mark(self._db, child)

            if self.childref and self.prev_gen_handles.get(child_handle):
                value = int(self.prev_gen_handles.get(child_handle))
                child_name += " [%d]" % self._get_s_s(value)

            self.doc.start_paragraph("DAR-ChildList", utils.roman(cnt).lower() + ".")
            cnt += 1

            self.__narrator.set_subject(child)
            if child_name:
                self.doc.write_text("%s. " % child_name, child_mark)
                if self.want_ids:
                    self.doc.write_text("(%s) " % child.get_gramps_id())
            self.doc.write_text_citation(
                self.__narrator.get_born_string()
                or self.__narrator.get_christened_string()
                or self.__narrator.get_baptised_string()
            )
            # Write Death and/or Burial text only if not probably alive
            if not probably_alive(child, self.database):
                self.doc.write_text_citation(
                    self.__narrator.get_died_string()
                    or self.__narrator.get_buried_string()
                )
            # if the list_children_spouses option is selected:
            if self.list_children_spouses:
                # get the family of the child that contains the spouse
                # of the child.  There may be more than one spouse for each
                # child
                family_handle_list = child.get_family_handle_list()
                # for the first spouse, this is true.
                # For subsequent spouses, make it false
                is_first_family = True
                for family_handle in family_handle_list:
                    child_family = self.database.get_family_from_handle(family_handle)
                    self.doc.write_text_citation(
                        self.__narrator.get_married_string(
                            child_family, is_first_family, self._name_display
                        )
                    )
                    is_first_family = False
            self.doc.end_paragraph()

    def write_family_events(self, family):
        """write the family events"""

        if not family.get_event_ref_list():
            return

        mother_handle = family.get_mother_handle()
        if mother_handle:
            mother = self._db.get_person_from_handle(mother_handle)
            mother_name = self._nd.display(mother)
            if not mother_name:
                mother_name = self._("Unknown")
        else:
            mother_name = self._("Unknown")

        father_handle = family.get_father_handle()
        if father_handle:
            father = self._db.get_person_from_handle(father_handle)
            father_name = self._nd.display(father)
            if not father_name:
                father_name = self._("Unknown")
        else:
            father_name = self._("Unknown")

        first = True
        for event_ref in family.get_event_ref_list():
            if first:
                self.doc.start_paragraph("DAR-MoreHeader")
                self.doc.write_text(
                    self._("More about %(mother_name)s and %(father_name)s:")
                    % {"mother_name": mother_name, "father_name": father_name}
                )
                self.doc.end_paragraph()
                first = False
            self.write_event(event_ref)

    def __write_mate(self, person, person_data):
        """Output birth, death, parentage, marriage and notes information"""
        ind = None
        has_info = False

        for family_handle in person.get_family_handle_list():
            family = self._db.get_family_from_handle(family_handle)
            ind_handle = None
            if person.get_gender() == Person.MALE:
                ind_handle = family.get_mother_handle()
            else:
                ind_handle = family.get_father_handle()
            if ind_handle:
                ind = self._db.get_person_from_handle(ind_handle)

                for event_ref in ind.get_primary_event_ref_list():
                    event = self._db.get_event_from_handle(event_ref.ref)
                    if event:
                        etype = event.get_type()
                        if (
                            etype == EventType.BAPTISM
                            or etype == EventType.BURIAL
                            or etype == EventType.BIRTH
                            or etype == EventType.DEATH
                        ):
                            has_info = True
                            break
                if not has_info:
                    family_handle = ind.get_main_parents_family_handle()
                    if family_handle:
                        fam = self._db.get_family_from_handle(family_handle)
                        if fam.get_mother_handle() or fam.get_father_handle():
                            has_info = True
                            break

            if has_info:
                self.write_person_info(ind, person_data)

                # self.doc.start_paragraph("DAR-MoreHeader")

                # plist = ind.get_media_list()

                # if self.addimages and len(plist) > 0:
                #     photo = plist[0]
                #     utils.insert_image(self._db, self.doc, photo, self._user)

                # name = self._nd.display(ind)
                # if not name:
                #     name = self._("Unknown")
                # mark = utils.get_person_mark(self._db, ind)

                # if family.get_relationship() == FamilyRelType.MARRIED:
                #     self.doc.write_text(self._("Spouse: %s") % name, mark)
                # else:
                #     self.doc.write_text(self._("Relationship with: %s") % name, mark)
                # if name[-1:] != ".":
                #     self.doc.write_text(".")
                # if self.want_ids:
                #     self.doc.write_text(" (%s)" % ind.get_gramps_id())
                # self.doc.write_text_citation(self.endnotes(ind))
                # self.doc.end_paragraph()

                # self.doc.start_paragraph("DAR-Entry")

                # self.__narrator.set_subject(ind)

                # text = self.__narrator.get_born_string()
                # if text:
                #     self.doc.write_text_citation(text)

                # text = self.__narrator.get_baptised_string()
                # if text:
                #     self.doc.write_text_citation(text)

                # text = self.__narrator.get_christened_string()
                # if text:
                #     self.doc.write_text_citation(text)

                # # Write Death and/or Burial text only if not probably alive
                # if not probably_alive(ind, self.database):
                #     text = self.__narrator.get_died_string(self.calcageflag)
                #     if text:
                #         self.doc.write_text_citation(text)

                #     text = self.__narrator.get_buried_string()
                #     if text:
                #         self.doc.write_text_citation(text)

                # latex_helper.write_parents(self._db, ind, person_data)

                # self.doc.end_paragraph()

    def endnotes(self, obj):
        """cite the endnotes for the object"""
        if not obj or not self.inc_sources:
            return ""

        txt = endnotes.cite_source(self.bibli, self._db, obj, self._locale)
        if txt:
            txt = "<super>" + txt + "</super>"
        return txt


# ------------------------------------------------------------------------
#
# DetAncestorOptions
#
# ------------------------------------------------------------------------
class LatexUpOptions(MenuReportOptions):
    """
    Defines options and provides handling interface.
    """

    def __init__(self, name, dbase):
        self.__db = dbase
        self.__pid = None
        self.__filter = None
        self._nf = None
        MenuReportOptions.__init__(self, name, dbase)

    def get_subject(self):
        """Return a string that describes the subject of the report."""
        gid = self.__pid.get_value()
        person = self.__db.get_person_from_gramps_id(gid)
        return _nd.display(person)

    def __update_filters(self):
        """
        Update the filter list based on the selected person
        """
        gid = self.__pid.get_value()
        person = self.__db.get_person_from_gramps_id(gid)
        nfv = self._nf.get_value()
        filter_list = utils.get_person_filters(
            person, include_single=True, name_format=nfv
        )
        self.__filter.set_filters(filter_list)

    def __filter_changed(self):
        """
        Handle filter change. If the filter is not specific to a person,
        disable the person option
        """
        filter_value = self.__filter.get_value()
        if filter_value == 1:  # "Entire Database" (as "include_single=True")
            self.__pid.set_available(False)
        else:
            # The other filters need a center person (assume custom ones too)
            self.__pid.set_available(True)

    def __activate_tag_list(self):
        include = self._tag_option.get_value()
        inc_tag = {
            key: value
            for key, value in self.options_dict.items()
            if key.startswith("inctag_")
        }
        for key in inc_tag:
            self.menu.get_option_by_name(key).set_available(include)

    def add_menu_options(self, menu):
        """
        Add Menu Options
        """
        from functools import partial

        # Report Options
        category = _("Report Options")
        add_option = partial(menu.add_option, category)

        self.__filter = FilterOption(_("Filter"), 0)
        self.__filter.set_help(_("Select the filter to be applied to the report."))
        add_option("filter", self.__filter)
        self.__filter.connect("value-changed", self.__filter_changed)

        self.__pid = PersonOption(_("Center Person"))
        self.__pid.set_help(_("The center person for the report"))
        add_option("pid", self.__pid)
        self.__pid.connect("value-changed", self.__update_filters)

        start_number = NumberOption(_("Sosa-Stradonitz number"), 1, 1, 16384)
        start_number.set_help(_("The Sosa-Stradonitz number of the central person."))
        add_option("initial_sosa", start_number)

        gen = NumberOption(_("Generations"), 10, 1, 100)
        gen.set_help(_("The number of generations to include in the report"))
        add_option("gen", gen)

        stdoptions.add_gramps_id_option(menu, category)

        format_output_file = BooleanOption(_("Format Latex Output file"), False)
        format_output_file.set_help(
            _("Whether to format the Latex Output file with latexindent.")
        )
        add_option("latex_format_output", format_output_file)

        create_trees = BooleanOption(_("(Re-) create all trees"), False)
        create_trees.set_help(
            _("Whether to update or create all trees in this report.")
        )
        add_option("create_trees", create_trees)

        category = _("Report Options (2)")
        add_option = partial(menu.add_option, category)

        self._nf = stdoptions.add_name_format_option(menu, category)
        self._nf.connect("value-changed", self.__update_filters)
        self.__update_filters()

        stdoptions.add_place_format_option(menu, category)

        stdoptions.add_private_data_option(menu, category)

        stdoptions.add_living_people_option(menu, category)

        locale_opt = stdoptions.add_localization_option(menu, category)

        stdoptions.add_date_format_option(menu, category, locale_opt)

        # Tags

        stdoptions.add_tags_option(menu, "Tags")
        self._tag_option = self.menu.get_option_by_name("inc_tags")
        self._tag_option.connect("value-changed", self.__activate_tag_list)
        add_option = partial(menu.add_option, _("Tags"))

        tags = set()  # collect all tags that are attached to a person
        for person_handle, pers in self.__db.get_person_cursor():
            person = self.__db.get_person_from_handle(person_handle)
            for tag_handle in person.get_tag_list():
                tag = self.__db.get_tag_from_handle(tag_handle)
                tags.add(tag.get_name())
        for tag in tags:
            inctags = BooleanOption("Include: " + tag, False)
            inctags.set_help(_("Whether to include tags in the margin notes."))
            add_option("inctag_" + tag, inctags)
        self.__activate_tag_list()

        # Content

        addopt = partial(menu.add_option, _("Content"))

        verbose = BooleanOption(_("Use complete sentences"), True)
        verbose.set_help(_("Whether to use complete sentences or succinct language."))
        addopt("verbose", verbose)

        fulldates = BooleanOption(_("Use full dates instead of only the year"), True)
        fulldates.set_help(_("Whether to use full dates instead of just year."))
        addopt("fulldates", fulldates)

        computeage = BooleanOption(_("Compute death age"), True)
        computeage.set_help(_("Whether to compute a person's age at death."))
        addopt("computeage", computeage)

        omitda = BooleanOption(_("Omit duplicate ancestors"), True)
        omitda.set_help(_("Whether to omit duplicate ancestors."))
        addopt("omitda", omitda)

        usecall = BooleanOption(_("Use callname for common name"), False)
        usecall.set_help(_("Whether to use the call name as the first name."))
        addopt("usecall", usecall)

        # What to include

        addopt = partial(menu.add_option, _("Include"))

        listc = BooleanOption(_("Include children"), True)
        listc.set_help(_("Whether to list children."))
        addopt("listc", listc)

        listc_spouses = BooleanOption(_("Include spouses of children"), False)
        listc_spouses.set_help(_("Whether to list the spouses of the children."))
        addopt("listc_spouses", listc_spouses)

        incevents = BooleanOption(_("Include events"), False)
        incevents.set_help(_("Whether to include events."))
        addopt("incevents", incevents)

        incotherevents = BooleanOption(_("Include other events"), False)
        incotherevents.set_help(
            _("Whether to include other events " "people participated in.")
        )
        addopt("incotherevents", incotherevents)

        desref = BooleanOption(_("Include descendant reference in child list"), True)
        desref.set_help(_("Whether to add descendant references in child list."))
        addopt("desref", desref)

        incphotos = BooleanOption(_("Include Photo/Images from Gallery"), False)
        incphotos.set_help(_("Whether to include images."))
        addopt("incphotos", incphotos)

        addopt = partial(menu.add_option, _("Include (2)"))

        incnotes = BooleanOption(_("Include notes"), True)
        incnotes.set_help(_("Whether to include notes."))
        addopt("incnotes", incnotes)

        incsources = BooleanOption(_("Include sources"), False)
        incsources.set_help(_("Whether to include source references."))
        addopt("incsources", incsources)

        incsrcnotes = BooleanOption(_("Include sources notes"), False)
        incsrcnotes.set_help(
            _(
                "Whether to include source notes in the "
                "Endnotes section. Only works if Include sources is selected."
            )
        )
        addopt("incsrcnotes", incsrcnotes)

        incattrs = BooleanOption(_("Include attributes"), False)
        incattrs.set_help(_("Whether to include attributes."))
        addopt("incattrs", incattrs)

        incaddresses = BooleanOption(_("Include addresses"), False)
        incaddresses.set_help(_("Whether to include addresses."))
        addopt("incaddresses", incaddresses)

        incnames = BooleanOption(_("Include alternative names"), False)
        incnames.set_help(_("Whether to include other names."))
        addopt("incnames", incnames)

        # How to handle missing information
        addopt = partial(menu.add_option, _("Missing information"))

        repplace = BooleanOption(_("Replace missing places with ______"), False)
        repplace.set_help(_("Whether to replace missing Places with blanks."))
        addopt("repplace", repplace)

        repdate = BooleanOption(_("Replace missing dates with ______"), False)
        repdate.set_help(_("Whether to replace missing Dates with blanks."))
        addopt("repdate", repdate)

    def make_default_style(self, default_style):
        """Make the default output style for the Detailed Ancestral Report"""
        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=16, bold=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_header_level(1)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_alignment(PARA_ALIGN_CENTER)
        para.set_description(_("The style used for the title."))
        default_style.add_paragraph_style("DAR-Title", para)

        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=14, italic=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_header_level(2)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_("The style used for the generation header."))
        default_style.add_paragraph_style("DAR-Generation", para)

        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=10, italic=0, bold=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_left_margin(1.0)  # in centimeters
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_("The style used for the children list title."))
        default_style.add_paragraph_style("DAR-ChildTitle", para)

        font = FontStyle()
        font.set(size=10)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(first_indent=-0.75, lmargin=1.75)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_("The style used for the text related to the children."))
        default_style.add_paragraph_style("DAR-ChildList", para)

        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=10, italic=0, bold=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(first_indent=0.0, lmargin=1.0)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_("The style used for the note header."))
        default_style.add_paragraph_style("DAR-NoteHeader", para)

        para = ParagraphStyle()
        para.set(lmargin=1.0)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_("The basic style used for the text display."))
        default_style.add_paragraph_style("DAR-Entry", para)

        para = ParagraphStyle()
        para.set(first_indent=-1.0, lmargin=1.0)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_("The style used for first level headings."))
        default_style.add_paragraph_style("DAR-First-Entry", para)

        font = FontStyle()
        font.set(size=10, face=FONT_SANS_SERIF, bold=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(first_indent=0.0, lmargin=1.0)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_("The style used for second level headings."))
        default_style.add_paragraph_style("DAR-MoreHeader", para)

        font = FontStyle()
        font.set(face=FONT_SERIF, size=10)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(first_indent=0.0, lmargin=1.0)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_("The style used for details."))
        default_style.add_paragraph_style("DAR-MoreDetails", para)

        endnotes.add_endnote_styles(default_style)
