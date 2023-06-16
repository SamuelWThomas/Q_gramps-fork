# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2002 Bruce J. DeGrasse
# Copyright (C) 2000-2007 Donald N. Allingham
# Copyright (C) 2007-2012 Brian G. Matherly
# Copyright (C) 2007      Robert Cawley  <rjc@cawley.id.au>
# Copyright (C) 2008-2009 James Friedmann <jfriedmannj@gmail.com>
# Copyright (C) 2009      Benny Malengier <benny.malengier@gramps-project.org>
# Copyright (C) 2010      Jakim Friant
# Copyright (C) 2010      Vlada Perić <vlada.peric@gmail.com>
# Copyright (C) 2011      Matt Keenan <matt.keenan@gmail.com>
# Copyright (C) 2011      Tim G L Lyons
# Copyright (C) 2012      lcc <lcc@6zap.com>
# Copyright (C) 2013-2014 Paul Franklin
# Copyright (C) 2015      Craig J. Anderson
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

"""Reports/Text Reports/Detailed Descendant Report"""

# ------------------------------------------------------------------------
#
# standard python modules
#
# ------------------------------------------------------------------------
from functools import partial

# ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
import math
import codecs
import os
import shutil
import re
import csv
from gramps.gen.lib import EventType, EventRoleType
from gramps.gen.utils.file import media_path_full, create_checksum
from gramps.plugins.docgen.latexdoc import *
from gramps.plugins.textreport.customnarrator import (
    CustomNarrator,
    FORMAT_NORMALTEXT,
    FORMAT_LATEX,
    FORMAT_MARKDOWN,
)
import latex_helper

# ---------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------
#
# Gramps modules
#
# ------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale

_ = glocale.translation.gettext
from gramps.gen.errors import ReportError
from gramps.gen.lib import FamilyRelType, Person, NoteType
from gramps.gen.utils.alive import probably_alive
from gramps.gen.plug.menu import (
    BooleanOption,
    FilterOption,
    BooleanListOption,
    NumberOption,
    PersonOption,
    EnumeratedListOption,
)
from gramps.gen.plug.docgen import (
    IndexMark,
    FontStyle,
    ParagraphStyle,
    FONT_SANS_SERIF,
    FONT_SERIF,
    INDEX_TYPE_TOC,
    PARA_ALIGN_CENTER,
)
from gramps.gen.plug.report import Report, Bibliography
from gramps.gen.plug.report import endnotes
from gramps.gen.plug.report import utils
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.plug.report import stdoptions
from gramps.plugins.lib.libnarrate import Narrator
from gramps.gen.display.place import displayer as _pd
from gramps.gen.display.name import displayer as _nd
from gramps.gen.proxy import CacheProxyDb

# ------------------------------------------------------------------------
#
# Constants
#
# ------------------------------------------------------------------------
EMPTY_ENTRY = "_____________"
HENRY = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# ------------------------------------------------------------------------
#
#
#
# ------------------------------------------------------------------------
class LatexDownReport(Report):
    """Detailed Descendant Report"""

    # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------

    ortsliste = {}
    # ---------------------------------------------------------------------------------------------------

    def __init__(self, database, options, user):
        """
        Create the DetDescendantReport object that produces the report.

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
        fulldates     - Whether to use full dates instead of just year.
        listc         - Whether to list children.
        list_children_spouses - Whether to list the spouses of the children
        incnotes      - Whether to include notes.
        usecall       - Whether to use the call name as the first name.
        repplace      - Whether to replace missing Places with ___________.
        repdate       - Whether to replace missing Dates with ___________.
        computeage    - Whether to compute age.
        verbose       - Whether to use complete sentences.
        numbering     - The descendancy numbering system to be utilized.
        desref        - Whether to add descendant references in child list.
        incphotos     - Whether to include images.
        incnames      - Whether to include other names.
        incevents     - Whether to include events.
        incaddresses  - Whether to include addresses.
        incsrcnotes   - Whether to include source notes in the Endnotes
                            section. Only works if Include sources is selected.
        incmates      - Whether to include information about spouses
        incattrs      - Whether to include attributes
        incpaths      - Whether to include the path of descendancy
                            from the start-person to each descendant.
        incssign      - Whether to include a sign ('+') before the
                            descendant number in the child-list
                            to indicate a child has succession.
        pid           - The Gramps ID of the center person for the report.
        name_format   - Preferred format to display names
        incmateref    - Whether to print mate information or reference
        incl_private  - Whether to include private data
        living_people - How to handle living people
        years_past_death - Consider as living this many years after death
        structure     - How to structure the report
        latex_format_output - if the output file should be formatted using latexindent
        """
        Report.__init__(self, database, options, user)

        self.map = {}
        self._user = user

        self.latex_output_aq = [str]

        menu = options.menu
        get_option_by_name = menu.get_option_by_name
        get_value = lambda name: get_option_by_name(name).get_value()

        self.set_locale(get_value("trans"))

        stdoptions.run_date_format_option(self, menu)

        stdoptions.run_private_data_option(self, menu)
        stdoptions.run_living_people_option(self, menu, self._locale)
        self.database = CacheProxyDb(self.database)
        self._db = self.database

        self.max_generations = get_value("gen")
        self.create_trees = get_value("create_trees")
        # self.pgbrk = get_value("pagebbg")
        # self.pgbrkenotes = get_value("pageben")
        self.fulldate = get_value("fulldates")
        use_fulldate = self.fulldate
        self.listchildren = get_value("listc")
        self.list_children_spouses = get_value("listc_spouses")
        self.inc_notes = get_value("incnotes")
        use_call = get_value("usecall")
        blankplace = get_value("repplace")
        blankdate = get_value("repdate")
        self.calcageflag = get_value("computeage")
        self.verbose = get_value("verbose")
        self.numbering = get_value("numbering")
        self.childref = get_value("desref")
        self.addimages = get_value("incphotos")
        self.structure = get_value("structure")
        self.inc_tags = get_value("inctags")
        self.inc_names = get_value("incnames")
        self.inc_events = get_value("incevents")
        self.inc_addr = get_value("incaddresses")
        self.inc_sources = get_value("incsources")
        self.inc_srcnotes = get_value("incsrcnotes")
        self.inc_mates = get_value("incmates")
        self.inc_attrs = get_value("incattrs")
        self.inc_paths = get_value("incpaths")
        self.inc_ssign = get_value("incssign")
        self.inc_materef = get_value("incmateref")
        self.want_ids = get_value("inc_id")
        self.latex_format_output = get_value("latex_format_output")

        pid = get_value("pid")
        self.center_person = self._db.get_person_from_gramps_id(pid)
        if self.center_person is None:
            raise ReportError(_("Person %s is not in the Database") % pid)

        self.gen_handles = {}
        self.prev_gen_handles = {}
        self.gen_keys = []
        self.dnumber = {}
        self.dmates = {}
        self.numbers_printed = list()

        if blankdate:
            empty_date = EMPTY_ENTRY
        else:
            empty_date = ""

        if blankplace:
            empty_place = EMPTY_ENTRY
        else:
            empty_place = ""

        filter_option = options.menu.get_option_by_name("filter")
        self.filter = filter_option.get_filter()

        stdoptions.run_name_format_option(self, menu)

        self.place_format = menu.get_option_by_name("place_format").get_value()

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

        self.bibli = Bibliography(Bibliography.MODE_DATE | Bibliography.MODE_PAGE)

    def apply_henry_filter(self, person_handle, index, pid, cur_gen=1):
        """Filter for Henry numbering"""
        if (not person_handle) or (cur_gen > self.max_generations):
            return
        if person_handle in self.dnumber:
            if self.dnumber[person_handle] > pid:
                self.dnumber[person_handle] = pid
        else:
            self.dnumber[person_handle] = pid
        self.map[index] = person_handle

        if len(self.gen_keys) < cur_gen:
            self.gen_keys.append([index])
        else:
            self.gen_keys[cur_gen - 1].append(index)

        person = self._db.get_person_from_handle(person_handle)
        index = 0
        for family_handle in person.get_family_handle_list():
            family = self._db.get_family_from_handle(family_handle)
            for child_ref in family.get_child_ref_list():
                _ix = max(self.map)
                self.apply_henry_filter(
                    child_ref.ref, _ix + 1, pid + HENRY[index], cur_gen + 1
                )
                index += 1

    def apply_mhenry_filter(self, person_handle, index, pid, cur_gen=1):
        """Filter for Modified Henry numbering"""

        def mhenry():
            """convenience finction"""
            return str(index) if index < 10 else "(" + str(index) + ")"

        if (not person_handle) or (cur_gen > self.max_generations):
            return
        self.dnumber[person_handle] = pid
        self.map[index] = person_handle

        if len(self.gen_keys) < cur_gen:
            self.gen_keys.append([index])
        else:
            self.gen_keys[cur_gen - 1].append(index)

        person = self._db.get_person_from_handle(person_handle)
        index = 1
        for family_handle in person.get_family_handle_list():
            family = self._db.get_family_from_handle(family_handle)
            for child_ref in family.get_child_ref_list():
                _ix = max(self.map)
                self.apply_henry_filter(
                    child_ref.ref, _ix + 1, pid + mhenry(), cur_gen + 1
                )
                index += 1

    def apply_daboville_filter(self, person_handle, index, pid, cur_gen=1):
        """Filter for d'Aboville numbering"""
        if (not person_handle) or (cur_gen > self.max_generations):
            return
        self.dnumber[person_handle] = pid
        self.map[index] = person_handle

        if len(self.gen_keys) < cur_gen:
            self.gen_keys.append([index])
        else:
            self.gen_keys[cur_gen - 1].append(index)

        person = self._db.get_person_from_handle(person_handle)
        index = 1
        for family_handle in person.get_family_handle_list():
            family = self._db.get_family_from_handle(family_handle)
            for child_ref in family.get_child_ref_list():
                _ix = max(self.map)
                self.apply_daboville_filter(
                    child_ref.ref, _ix + 1, pid + "." + str(index), cur_gen + 1
                )
                index += 1

    def apply_mod_reg_filter_aux(self, person_handle, index, cur_gen=1):
        """Filter for Record-style (Modified Register) numbering"""
        if (not person_handle) or (cur_gen > self.max_generations):
            return
        self.map[index] = person_handle

        if len(self.gen_keys) < cur_gen:
            self.gen_keys.append([index])
        else:
            self.gen_keys[cur_gen - 1].append(index)

        person = self._db.get_person_from_handle(person_handle)

        for family_handle in person.get_family_handle_list():
            family = self._db.get_family_from_handle(family_handle)
            for child_ref in family.get_child_ref_list():
                _ix = max(self.map)
                self.apply_mod_reg_filter_aux(child_ref.ref, _ix + 1, cur_gen + 1)

    def apply_mod_reg_filter(self, person_handle):
        """Entry Filter for Record-style (Modified Register) numbering"""
        self.apply_mod_reg_filter_aux(person_handle, 1, 1)
        mod_reg_number = 1
        for keys in self.gen_keys:
            for key in keys:
                person_handle = self.map[key]
                if person_handle not in self.dnumber:
                    self.dnumber[person_handle] = mod_reg_number
                    mod_reg_number += 1

    def write_report(self):
        """
        This function is called by the report system and writes the report.
        """
        if self.numbering == "Henry":
            self.apply_henry_filter(self.center_person.get_handle(), 1, "1")
        elif self.numbering == "Modified Henry":
            self.apply_mhenry_filter(self.center_person.get_handle(), 1, "1")
        elif self.numbering == "d'Aboville":
            self.apply_daboville_filter(self.center_person.get_handle(), 1, "1")
        elif self.numbering == "Record (Modified Register)":
            self.apply_mod_reg_filter(self.center_person.get_handle())
        else:
            raise AttributeError("no such numbering: '%s'" % self.numbering)

        if self.filter:
            self.filtered_subset = self.filter.apply(self._db, user=self._user)

        name = self._name_display.display_name(self.center_person.get_primary_name())
        if not name:
            name = self._("Unknown")

        self.numbers_printed = list()

        if self.structure == "by generation":
            for generation, gen_keys in enumerate(self.gen_keys):
                text = self._("Generation %d") % (generation + 1)
                # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
                self.latex_output_aq.append("\\generation{" + text + "}")
                # ---------------------------------------------------------------------------------------------------
                if self.childref:
                    self.prev_gen_handles = self.gen_handles.copy()
                    self.gen_handles.clear()
                for key in gen_keys:
                    person_handle = self.map[key]
                    self.gen_handles[person_handle] = key
                    self.write_person(key)
        elif self.structure == "by lineage":
            for key in sorted(self.map):
                self.write_person(key)
        else:
            raise AttributeError("no such structure: '%s'" % self.structure)

        # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
        # Determine filename
        if self.doc._backend.filename:
            dir = os.path.dirname(self.doc._backend.filename) # Stand-alone report
        else:
            dir = os.path.dirname(self.doc.filename) # Report is part of a book
        filename = latex_helper.get_filename(
            self.center_person, "latex-desc", "", "tex", dir, ""
        )
        # Write LaTeX Output
        f = codecs.open(filename, "w+", encoding="utf-8")
        # write intro for using this file as a subfile in latex
        f.write(
            """\\documentclass[00-Maindoc]{subfiles}\n	
        \\begin{document}\n\n	
        """
        )
        for i in range(len(self.latex_output_aq) - 1):
            i = i + 1
            f.write(self.latex_output_aq[i])
        self.latex_output_aq = []

        # write outro
        f.write("\n\\end{document}")
        f.close()
        # Format file using latexindent
        if self.latex_format_output:
            latex_helper.format_with_latexindent(filename)

        # Write files for map generation
        # Coordinates with density information --> file.coord
        # ortsdetails[0] = lat, [1] = long, [2] = density
        # TODO: normalize densities
        # with open(
        #     output_path + "maps\\" + output_file_id + ".coord",
        #     "w",
        #     newline="",
        #     encoding="utf-8",
        # ) as f:
        #     writer = csv.writer(f)
        #     for ort, ortsdetails in self.ortsliste.items():
        #         writer.writerow(
        #             [str(ortsdetails[1]), str(ortsdetails[0]), str(ortsdetails[2])]
        #         )
        # # Coordinates with name information --> file.label
        # with open(
        #     output_path + "maps\\" + output_file_id + ".label",
        #     "w",
        #     newline="",
        #     encoding="utf-8",
        # ) as f:
        #     writer = csv.writer(f)
        #     for ort, ortsdetails in self.ortsliste.items():
        #         ort_length = ort.find(",")
        #         if ort_length > 0:
        #             ort = ort[0:ort_length]
        #         writer.writerow([str(ortsdetails[1]), str(ortsdetails[0]), ort])
        # self.ortsliste = {}
        # TODO: Calculate bounding box

    def append_bio_facts(self, individual_aq):
        biography = latex_helper.get_latex_biography(
            individual_aq, "henry", self.want_ids
        )
        self.latex_output_aq.append(biography)

    def write_person(self, key):
        """Output birth, death, parentage, marriage and notes information"""

        # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
        individual_aq = latex_helper.get_empty_indiviudal()
        # ---------------------------------------------------------------------------------------------------

        person_handle = self.map[key]
        person = self._db.get_person_from_handle(person_handle)

        val = self.dnumber[person_handle]

        if val in self.numbers_printed:
            return
        else:
            self.numbers_printed.append(val)

        # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
        individual_aq["kekule"] = val
        self.write_person_info(person, individual_aq)
        ehepartner = []
        # ---------------------------------------------------------------------------------------------------

        if (
            self.inc_mates
            or self.listchildren
            or self.inc_notes
            or self.inc_events
            or self.inc_attrs
        ):
            # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
            alphabet = ["a", "b", "c", "d", "e", "f", "g", "h"]
            partner_nr = 0
            # ---------------------------------------------------------------------------------------------------
            for family_handle in person.get_family_handle_list():
                family = self._db.get_family_from_handle(family_handle)
                if self.inc_mates:
                    # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
                    individual_aq_mate = latex_helper.get_empty_indiviudal()
                    individual_aq_mate["kekule"] = (
                        individual_aq["kekule"] + alphabet[partner_nr]
                    )
                    individual_aq_mate["partner"] = person
                    self.__write_mate(person, family, individual_aq_mate)
                    ehepartner.append(individual_aq_mate)
                    partner_nr += 1
                #     # ---------------------------------------------------------------------------------------------------
                #     # DELETED FOR Q-LATEX OUTPUT------------------------------------------------------------------------
                #     # self.__write_mate(person, family)
                #     # ---------------------------------------------------------------------------------------------------
                # if self.listchildren:
                #     self.__write_children(family)
                # if self.inc_notes:
                #     self.__write_family_notes(family)
                # first = True
                # if self.inc_events:
                #     first = self.__write_family_events(family)
                # if self.inc_attrs:
                #     self.__write_family_attrs(family, first)

        # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
        self.append_bio_facts(individual_aq)
        for gattin in ehepartner:
            self.append_bio_facts(gattin)
        # ---------------------------------------------------------------------------------------------------

    # def write_event(self, event_ref):
    # """write out the details of an event"""
    # text = ""
    # event = self._db.get_event_from_handle(event_ref.ref)

    # if self.fulldate:
    #     date = self._get_date(event.get_date_object())
    # else:
    #     date = event.get_date_object().get_year()

    # place = _pd.display_event(self._db, event, self.place_format)

    # self.doc.start_paragraph("DDR-MoreDetails")
    # event_name = self._get_type(event.get_type())
    # if date and place:
    #     # Translators: needed for Arabic, ignore otherwise
    #     text += self._("%(str1)s, %(str2)s") % {"str1": date, "str2": place}
    # elif date:
    #     text += "%s" % date
    # elif place:
    #     text += "%s" % self._(place)

    # if event.get_description():
    #     if text:
    #         text += ". "
    #     text += event.get_description()

    # text += self.endnotes(event)

    # if text:
    #     text += ". "

    # # Translators: needed for French, ignore otherwise
    # text = self._("%(str1)s: %(str2)s") % {"str1": self._(event_name), "str2": text}

    # self.doc.write_text_citation(text)

    # if self.inc_attrs:
    #     text = ""
    #     attr_list = event.get_attribute_list()[
    #         :
    #     ]  # we don't want to modify cached original
    #     attr_list.extend(event_ref.get_attribute_list())
    #     for attr in attr_list:
    #         if text:
    #             # Translators: needed for Arabic, ignore otherwise
    #             text += self._("; ")
    #         attr_name = attr.get_type().type2base()
    #         # Translators: needed for French, ignore otherwise
    #         text += self._("%(type)s: %(value)s%(endnotes)s") % {
    #             "type": self._(attr_name),
    #             "value": attr.get_value(),
    #             "endnotes": self.endnotes(attr),
    #         }
    #     text = " " + text
    #     self.doc.write_text_citation(text)

    # self.doc.end_paragraph()

    # if self.inc_notes:
    #     # if the event or event reference has a note attached to it,
    #     # get the text and format it correctly
    #     notelist = event.get_note_list()[
    #         :
    #     ]  # we don't want to modify cached original
    #     notelist.extend(event_ref.get_note_list())
    #     for notehandle in notelist:
    #         note = self._db.get_note_from_handle(notehandle)
    #         self.doc.write_styled_note(
    #             note.get_styledtext(),
    #             note.get_format(),
    #             "DDR-MoreDetails",
    #             contains_html=(note.get_type() == NoteType.HTML_CODE),
    #         )

    # CHANGED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
    def __write_parents(self, person, individual_aq):
        """write out the main parents of a person"""
        # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
        geschlecht = person.get_gender()  # Person.MALE / Person.FEMALE / Person.UNKNOWN
        if geschlecht == Person.MALE:
            geschlecht_text = "Sohn"
        elif geschlecht == Person.FEMALE:
            geschlecht_text = "Tochter"
        else:
            geschlecht_text = "Kind"
        # ---------------------------------------------------------------------------------------------------
        family_handle = person.get_main_parents_family_handle()
        if family_handle:
            family = self._db.get_family_from_handle(family_handle)
            mother_handle = family.get_mother_handle()
            father_handle = family.get_father_handle()
            if mother_handle:
                mother = self._db.get_person_from_handle(mother_handle)
                mother_name = self._name_display.display_name(mother.get_primary_name())
                # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
                mother_name = mother.primary_name.first_name + " "
                mother_spitzname = mother.primary_name.nick
                if mother_spitzname:
                    mother_name += "\\spitzname{" + mother_spitzname + "} "
                mother_name += latex_helper.get_nachname(mother)
                mother_name = mother_name.strip()
                mother_id = latex_helper.get_latex_id(mother)
                # ---------------------------------------------------------------------------------------------------
                mother_mark = utils.get_person_mark(self._db, mother)
            else:
                mother_name = ""
                mother_mark = ""
                # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
                mother_id = ""
                # ---------------------------------------------------------------------------------------------------
            if father_handle:
                father = self._db.get_person_from_handle(father_handle)
                father_name = self._name_display.display_name(father.get_primary_name())
                # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
                father_name = father.primary_name.first_name + " "
                father_spitzname = father.primary_name.nick
                if father_spitzname:
                    father_name += "\\spitzname{" + father_spitzname + "} "
                father_name += latex_helper.get_nachname(father)
                father_name = father_name.strip()
                father_id = latex_helper.get_latex_id(father)
                # ---------------------------------------------------------------------------------------------------
                father_mark = utils.get_person_mark(self._db, father)
            else:
                father_name = ""
                father_mark = ""
                # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
                father_id = ""
                # ---------------------------------------------------------------------------------------------------
            # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
            eltern_text = ""
            if mother_name or father_name:
                eltern_text = geschlecht_text + " "
                if mother_name:
                    eltern_text += (
                        "der \\hyperref["
                        + mother_id
                        + "]{"
                        + mother_name
                        + "}\seitenzahl{"
                        + mother_id
                        + "} "
                    )
                if mother_name and father_name:
                    eltern_text += "und "
                if father_name:
                    eltern_text += (
                        "des \\hyperref["
                        + father_id
                        + "]{"
                        + father_name
                        + "}\seitenzahl{"
                        + father_id
                        + "} "
                    )
                eltern_text = eltern_text.strip()
                eltern_text += ""
            individual_aq["abstammung"] = eltern_text
            # ---------------------------------------------------------------------------------------------------
            text = self.__narrator.get_child_string(father_name, mother_name)
            if text:
                self.doc.write_text(text)
                if father_mark:
                    self.doc.write_text("", father_mark)
                if mother_mark:
                    self.doc.write_text("", mother_mark)
        # ---------------------------------------------------------------------------------------------------

    # CHANGED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
    def write_marriage(self, person, individual_aq):
        """
        Output marriage sentence.
        """
        is_first = True
        # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
        hochzeit_nr = 0
        anzahl_hochzeiten = len(person.get_family_handle_list())
        # ---------------------------------------------------------------------------------------------------
        for family_handle in person.get_family_handle_list():
            family = self._db.get_family_from_handle(family_handle)
            spouse_handle = utils.find_spouse(person, family)
            spouse = ""
            if spouse_handle:
                spouse = self._db.get_person_from_handle(spouse_handle)
                spouse_mark = utils.get_person_mark(self._db, spouse)
            else:
                spouse_mark = None

            text = self.__narrator.get_married_string(
                family, is_first, self._name_display
            )
            if text:
                self.doc.write_text_citation(text, spouse_mark)
                # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
                text = latex_helper.transform_abbreviations(text)
                hochzeit_nr += 1
                if anzahl_hochzeiten > 1:
                    text = "\\circled{" + str(hochzeit_nr) + "}\\," + text

                kinder_text = ""
                kinder = family.get_child_ref_list()
                if len(kinder) > 0:
                    count = 1
                    for kind_ref in kinder:
                        child_handle = kind_ref.ref
                        kind = self._db.get_person_from_handle(child_handle)
                        kind_vorname = kind.primary_name.first_name
                        kind_spitzname = kind.primary_name.nick
                        kinder_text += (
                            "\\hyperref[" + latex_helper.get_latex_id(kind) + "]{"
                        )
                        if len(kinder) > 1:
                            kinder_text += "(" + str(count) + ")~"
                        kinder_text += kind_vorname
                        if kind_spitzname:
                            kinder_text += " \\spitzname{" + kind_spitzname + "}"
                        kinder_text += (
                            "}\seitenzahl{" + latex_helper.get_latex_id(kind) + "}"
                        )
                        if count < len(kinder):
                            kinder_text += ", "
                        if count == len(kinder):
                            kinder_text += ". "
                        count += 1
                if kinder_text:
                    if not spouse:
                        text += " Kinder: " + kinder_text
                    elif individual_aq["partner"] != spouse:
                        text += " Kinder: " + kinder_text
                    else:
                        text += " (Kinder:~$\\rightarrow$\\,Partner)"

                if hochzeit_nr < anzahl_hochzeiten:
                    text += "" + "\n\n"
                individual_aq["hochzeiten"] += text
                # ---------------------------------------------------------------------------------------------------
                if self.want_ids:
                    self.doc.write_text("(%s)" % family.get_gramps_id())
                is_first = False

    # ---------------------------------------------------------------------------------------------------

    # CHANGED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
    def __write_mate(self, person, family, individual_aq):
        """
        Write information about the person's spouse/mate.
        """
        if person.get_gender() == Person.MALE:
            mate_handle = family.get_mother_handle()
        else:
            mate_handle = family.get_father_handle()

        if mate_handle:
            mate = self._db.get_person_from_handle(mate_handle)

            self.doc.start_paragraph("DDR-MoreHeader")
            name = self._name_display.display(mate)
            if not name:
                name = self._("Unknown")
            mark = utils.get_person_mark(self._db, mate)
            if family.get_relationship() == FamilyRelType.MARRIED:
                self.doc.write_text(self._("Spouse: %s") % name, mark)
            else:
                self.doc.write_text(self._("Relationship with: %s") % name, mark)
            if name[-1:] != ".":
                self.doc.write_text(".")
            self.doc.write_text_citation(self.endnotes(mate))
            if self.want_ids:
                self.doc.write_text(" (%s)" % mate.get_gramps_id())
            self.doc.end_paragraph()

            if not self.inc_materef:
                # Don't want to just print reference
                self.write_person_info(mate, individual_aq)
            else:
                # Check to see if we've married a cousin
                if mate_handle in self.dnumber:
                    self.doc.start_paragraph("DDR-MoreDetails")
                    self.doc.write_text_citation(
                        self._("Ref: %(number)s. %(name)s")
                        % {"number": self.dnumber[mate_handle], "name": name}
                    )
                    self.doc.end_paragraph()
                else:
                    self.dmates[mate_handle] = person.get_handle()
                    # CHANGED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
                    self.write_person_info(mate, individual_aq)
                    # ---------------------------------------------------------------------------------------------------

    # ---------------------------------------------------------------------------------------------------

    def __get_mate_names(self, family):
        """get the names of the parents in a family"""
        mother_handle = family.get_mother_handle()
        if mother_handle:
            mother = self._db.get_person_from_handle(mother_handle)
            mother_name = self._name_display.display(mother)
            if not mother_name:
                mother_name = self._("Unknown")
        else:
            mother_name = self._("Unknown")

        father_handle = family.get_father_handle()
        if father_handle:
            father = self._db.get_person_from_handle(father_handle)
            father_name = self._name_display.display(father)
            if not father_name:
                father_name = self._("Unknown")
        else:
            father_name = self._("Unknown")

        return mother_name, father_name

    def __write_children(self, family):
        """
        List the children for the given family.
        :param family: Family
        :return:
        """
        if not family.get_child_ref_list():
            return

        mother_name, father_name = self.__get_mate_names(family)

        self.doc.start_paragraph("DDR-ChildTitle")
        self.doc.write_text(
            self._("Children of %(mother_name)s and %(father_name)s")
            % {"father_name": father_name, "mother_name": mother_name}
        )
        self.doc.end_paragraph()

        cnt = 1
        for child_ref in family.get_child_ref_list():
            child_handle = child_ref.ref
            child = self._db.get_person_from_handle(child_handle)
            child_name = self._name_display.display(child)
            if not child_name:
                child_name = self._("Unknown")
            child_mark = utils.get_person_mark(self._db, child)

            if self.childref and self.prev_gen_handles.get(child_handle):
                value = str(self.prev_gen_handles.get(child_handle))
                child_name += " [%s]" % value

            if self.inc_ssign:
                prefix = " "
                for family_handle in child.get_family_handle_list():
                    family = self._db.get_family_from_handle(family_handle)
                    if family.get_child_ref_list():
                        prefix = "+ "
                        break
            else:
                prefix = ""

            if child_handle in self.dnumber:
                self.doc.start_paragraph(
                    "DDR-ChildList",
                    prefix
                    + str(self.dnumber[child_handle])
                    + " "
                    + utils.roman(cnt).lower()
                    + ".",
                )
            else:
                self.doc.start_paragraph(
                    "DDR-ChildList", prefix + utils.roman(cnt).lower() + "."
                )
            cnt += 1

            self.doc.write_text("%s. " % child_name, child_mark)
            if self.want_ids:
                self.doc.write_text("(%s) " % child.get_gramps_id())
            self.__narrator.set_subject(child)
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

    def __write_family_notes(self, family):
        """
        Write the notes for the given family.
        """
        notelist = family.get_note_list()
        if len(notelist) > 0:
            mother_name, father_name = self.__get_mate_names(family)

            self.doc.start_paragraph("DDR-NoteHeader")
            self.doc.write_text(
                self._("Notes for %(mother_name)s and %(father_name)s:")
                % {"mother_name": mother_name, "father_name": father_name}
            )
            self.doc.end_paragraph()
            for notehandle in notelist:
                note = self._db.get_note_from_handle(notehandle)
                self.doc.write_styled_note(
                    note.get_styledtext(), note.get_format(), "DDR-Entry"
                )

    def __write_family_events(self, family):
        """
        List the events for the given family.
        """
        if not family.get_event_ref_list():
            return

        mother_name, father_name = self.__get_mate_names(family)

        first = True
        for event_ref in family.get_event_ref_list():
            if first:
                self.doc.start_paragraph("DDR-MoreHeader")
                self.doc.write_text(
                    self._("More about %(mother_name)s and %(father_name)s:")
                    % {"mother_name": mother_name, "father_name": father_name}
                )
                self.doc.end_paragraph()
                first = False
            self.write_event(event_ref)
        return first

    def __write_family_attrs(self, family, first):
        """
        List the attributes for the given family.
        """
        attrs = family.get_attribute_list()

        if first and attrs:
            mother_name, father_name = self.__get_mate_names(family)

            self.doc.start_paragraph("DDR-MoreHeader")
            self.doc.write_text(
                self._("More about %(mother_name)s and %(father_name)s:")
                % {"mother_name": mother_name, "father_name": father_name}
            )
            self.doc.end_paragraph()

        for attr in attrs:
            self.doc.start_paragraph("DDR-MoreDetails")
            attr_name = self._get_type(attr.get_type())
            text = self._("%(type)s: %(value)s%(endnotes)s") % {
                "type": self._(attr_name),
                "value": attr.get_value(),
                "endnotes": self.endnotes(attr),
            }
            self.doc.write_text_citation(text)
            self.doc.end_paragraph()

            if self.inc_notes:
                # if the attr or attr reference has a note attached to it,
                # get the text and format it correctly
                notelist = attr.get_note_list()
                for notehandle in notelist:
                    note = self._db.get_note_from_handle(notehandle)
                    self.doc.write_styled_note(
                        note.get_styledtext(), note.get_format(), "DDR-MoreDetails"
                    )

    # CHANGED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
    def write_person_info(self, person: Person, individual_aq):
        """write out all the person's information"""
        name = self._name_display.display(person)
        if not name:
            name = self._("Unknown")
        self.__narrator.set_subject(person)
        # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
        individual_aq["displayname"] = name
        surnames = person.primary_name.surname_list
        if len(surnames) > 0:
            individual_aq["alias"] = surnames[0].prefix
            individual_aq["nachname"] = surnames[0].surname
        individual_aq["vornamen"] = person.primary_name.first_name
        individual_aq["rufname"] = person.primary_name.call
        individual_aq["spitzname"] = person.primary_name.nick
        individual_aq["titel"] = latex_helper.transform_abbreviations(
            person.primary_name.title
        )
        individual_aq["suffix"] = person.primary_name.suffix

        if self.filter and self.filtered_subset:
            if not person.get_handle() in self.filtered_subset:
                individual_aq["filtered"] = self.filter.get_name()
        # IDs
        individual_aq["GrID"] = str(person.get_gramps_id())
        individual_aq["ID"] = latex_helper.get_latex_id(person)

        # Trees
        if self.create_trees and not individual_aq["filtered"]:
            if self.doc._backend.filename:
                dir = os.path.dirname(self.doc._backend.filename) # Stand-alone report
            else:
                dir = os.path.dirname(self.doc.filename) # Report is part of a book
            individual_aq["trees"] = ""
            trees = [
                latex_helper.tree_create(attr.get_value(), self._db, person, dir)
                for attr in person.get_attribute_list()
                if str(attr.get_type()) == "create_tree"
            ]
            for filename in trees:
                if filename != "": # filename will be '' if the tree definition was incorrect
                    filename_rel = os.path.relpath(filename, dir)
                    caption = "Stammbaum " + individual_aq["displayname"]
                    # TODO: set the person's index in the caption and mark it with a * in the index
                    # caption += "\index[ind]{"+individual_aq["ID"]+"}"
                    label = os.path.split(filename)[1][:-6]
                    individual_aq["treelinks"] += "$\\leftpitchfork$\\seitenzahl{tree:"+label+"} "
                    hashtag = "#"
                    # level size sets the width od a node, node size the height!
                    individual_aq[
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
                individual_aq["beruf"] = latex_helper.transform_abbreviations(
                    occupation
                )

        # Tags:
        if self.inc_tags:
            tag_list = person.get_tag_list()
            vertical_adj = 13
            tag_no = 0
            if self.want_ids and len(tag_list) > 0:
                tag_no = 1
            for tag_handle in tag_list:
                tag = self.database.get_tag_from_handle(tag_handle)
                color = tag.color[-6:]
                color_name = f"col_{tag.name}"
                individual_aq["tags"] += "\\renewcommand*{\\marginnotevadjust}{"
                individual_aq["tags"] += str(vertical_adj * tag_no)
                individual_aq["tags"] += "pt}"
                individual_aq[
                    "tags"
                ] += f"\\definecolor{{{color_name}}}{{HTML}}{{{color}}}"
                individual_aq[
                    "tags"
                ] += f"\\tcbset{{doc marginnote={{colframe={color_name}!50!white,colback={color_name}!5!white,halign=center}}}}"
                individual_aq[
                    "tags"
                ] += f"\\tcbdocmarginnote{{\\textcolor{{{color_name}}}{{"
                individual_aq["tags"] += tag.name
                individual_aq["tags"] += "}}"
                tag_no += 1
            individual_aq["tags"] += "\\renewcommand*{\\marginnotevadjust}{0pt}"

        # ---------------------------------------------------------------------------------------------------
        plist = person.get_media_list()
        # CHANGED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
        # if self.addimages and len(plist) > 0:
        if True and len(plist) > 0:
            photo = plist[0]
            # utils.insert_image(self._db, self.doc, photo, self._user)
            object_handle = photo.get_reference_handle()
            media = self._db.get_media_from_handle(object_handle)
            mime_type = media.get_mime_type()
            if mime_type and mime_type.startswith("image"):
                filename = media_path_full(self._db, media.get_path())
                caption = media.get_description()
                if latex_helper.normalize_string(
                    caption
                ) in latex_helper.normalize_string(
                    filename
                ):  # caption is filename, replace by person's name
                    caption = (
                        individual_aq["titel"]
                        + " "
                        + individual_aq["vornamen"]
                        + " "
                        + individual_aq["nachname"]
                        + " "
                        + individual_aq["suffix"]
                    )
                    caption = caption.strip()

                checksum = media.get_checksum()
                if not checksum:
                    checksum = create_checksum(filename)
                    media.set_checksum(checksum)
                filename_new_short = (
                    latex_helper.normalize_string(
                        individual_aq["nachname"] + individual_aq["vornamen"]
                    )
                    + "-"
                    + str(checksum)
                    + "-"
                    + individual_aq["GrID"]
                )
                label = "pic-" + filename_new_short
                filename_new = (
                    "C:\\Users\\andreas.quentin\\OneDrive\\Documents\\Ahnenblatt\\07 LaTeX\\pics\\"
                    + filename_new_short
                    + ".jpg"
                )
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
                    )
                    individual_aq["picture"] = latex_image
        # ---------------------------------------------------------------------------------------------------

        self.doc.start_paragraph("DDR-Entry")

        if not self.verbose:
            # CHANGED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
            self.__write_parents(person, individual_aq)
            # ---------------------------------------------------------------------------------------------------
        # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
        # Ortsliste
        bapt_ref = ""
        christ_ref = ""
        buried_ref = ""
        for event_ref in person.get_event_ref_list():
            event = self._db.get_event_from_handle(event_ref.ref)
            if event and event_ref.role.value == EventRoleType.PRIMARY:
                if event.type.value == EventType.BAPTISM:
                    bapt_ref = event_ref
                if event.type.value == EventType.CHRISTEN:
                    christ_ref = event_ref
                if event.type.value == EventType.BURIAL:
                    buried_ref = event_ref

        event_refs = [
            person.get_birth_ref(),
            bapt_ref,
            christ_ref,
            buried_ref,
            person.get_death_ref(),
        ]
        for event_ref in event_refs:
            if event_ref and event_ref.ref:
                event = self._db.get_event_from_handle(event_ref.ref)
                if event:
                    place_handle = event.get_place_handle()
                    if place_handle:
                        place = self._db.get_place_from_handle(place_handle)
                        place_text = _pd.display_event(
                            self._db, event, self.place_format
                        )
                        lat = (
                            place.get_latitude()
                        )  # formatted with leading cardinal direction (WESN)
                        lon = (
                            place.get_longitude()
                        )  # formatted with leading cardinal direction (WESN)
                        if lat and lon:
                            if not place_text in self.ortsliste:  # it's a new place
                                lat_card_direction = lat[0]
                                lon_card_direction = lon[0]
                                if lat_card_direction == "N":
                                    lat = lat[1:]
                                elif lat_card_direction == "S":
                                    lat = "-" + lat[1:]
                                if lon_card_direction == "E":
                                    lon = lon[1:]
                                elif lon_card_direction == "W":
                                    lon = "-" + lon[1:]

                                self.ortsliste[place_text] = [
                                    lat,
                                    lon,
                                    1,
                                ]  # add new place to list
                            else:
                                self.ortsliste[place_text][
                                    2
                                ] += 1  # it's a known place, just increase the counter
                            break
        # ---------------------------------------------------------------------------------------------------

        text = self.__narrator.get_born_string()
        if text:
            self.doc.write_text_citation(text)
            # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
            individual_aq["geboren"] = latex_helper.transform_abbreviations(text)
            # ---------------------------------------------------------------------------------------------------

        text = self.__narrator.get_baptised_string()
        if text:
            self.doc.write_text_citation(text)
            # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
            # TODO: prüfen, ob leer, und ansonsten get_christened_string() verwenden!
            individual_aq["getauft"] = latex_helper.transform_abbreviations(text)
            # ---------------------------------------------------------------------------------------------------

        text = self.__narrator.get_christened_string()
        if text:
            self.doc.write_text_citation(text)

        # Write Death and/or Burial text only if not probably alive
        if not probably_alive(person, self.database):
            text = self.__narrator.get_died_string(self.calcageflag)
            if text:
                self.doc.write_text_citation(text)
                # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
                individual_aq["gestorben"] = latex_helper.transform_abbreviations(text)
                # ---------------------------------------------------------------------------------------------------

            text = self.__narrator.get_buried_string()
            if text:
                self.doc.write_text_citation(text)
                # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
                individual_aq["begraben"] = latex_helper.transform_abbreviations(text)
                # ---------------------------------------------------------------------------------------------------

        # CHANGED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
        if self.verbose:
            self.__write_parents(person, individual_aq)
        if not "partner" in individual_aq or individual_aq["partner"] == None:
            self.write_marriage(person, individual_aq)
        # ---------------------------------------------------------------------------------------------------

        self.doc.end_paragraph()

        notelist = person.get_note_list()
        if len(notelist) > 0 and self.inc_notes:
            self.doc.start_paragraph("DDR-NoteHeader")
            # feature request 2356: avoid genitive form
            self.doc.write_text(self._("Notes for %s") % name)
            self.doc.end_paragraph()
            # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
            note_counter = 0
            # ---------------------------------------------------------------------------------------------------
            for notehandle in notelist:
                note = self._db.get_note_from_handle(notehandle)
                self.doc.write_styled_note(
                    note.get_styledtext(),
                    note.get_format(),
                    "DDR-Entry",
                    contains_html=(note.get_type() == NoteType.HTML_CODE),
                )
                # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
                individual_aq["notitzen"] += latex_helper.format_note(
                    note.get_styledtext()
                )
                note_counter += 1
                if note_counter < len(notelist):
                    individual_aq["notitzen"] += "\\\\\r"
                # ---------------------------------------------------------------------------------------------------

        first = True
        if self.inc_names:
            for alt_name in person.get_alternate_names():
                if first:
                    self.doc.start_paragraph("DDR-MoreHeader")
                    self.doc.write_text(
                        self._("More about %(person_name)s:") % {"person_name": name}
                    )
                    self.doc.end_paragraph()
                    first = False
                self.doc.start_paragraph("DDR-MoreDetails")
                atype = self._get_type(alt_name.get_type())
                aname = alt_name.get_regular_name()
                self.doc.write_text_citation(
                    self._("%(type)s: %(value)s%(endnotes)s")
                    % {
                        "type": self._(atype),
                        "value": aname,
                        "endnotes": self.endnotes(alt_name),
                    }
                )
                self.doc.end_paragraph()

        if self.inc_events:
            for event_ref in person.get_primary_event_ref_list():
                if first:
                    self.doc.start_paragraph("DDR-MoreHeader")
                    self.doc.write_text(
                        self._("More about %(person_name)s:") % {"person_name": name}
                    )
                    self.doc.end_paragraph()
                    first = 0

                self.write_event(event_ref)

        if self.inc_addr:
            for addr in person.get_address_list():
                if first:
                    self.doc.start_paragraph("DDR-MoreHeader")
                    self.doc.write_text(
                        self._("More about %(person_name)s:") % {"person_name": name}
                    )
                    self.doc.end_paragraph()
                    first = False
                self.doc.start_paragraph("DDR-MoreDetails")

                text = utils.get_address_str(addr)

                if self.fulldate:
                    date = self._get_date(addr.get_date_object())
                else:
                    date = addr.get_date_object().get_year()

                self.doc.write_text(self._("Address: "))
                if date:
                    # Translators: needed for Arabic, ignore otherwise
                    self.doc.write_text(self._("%s, ") % date)
                self.doc.write_text(text)
                self.doc.write_text_citation(self.endnotes(addr))
                self.doc.end_paragraph()

        if self.inc_attrs:
            attrs = person.get_attribute_list()
            if first and attrs:
                self.doc.start_paragraph("DDR-MoreHeader")
                self.doc.write_text(
                    self._("More about %(person_name)s:") % {"person_name": name}
                )
                self.doc.end_paragraph()
                first = False

            for attr in attrs:
                self.doc.start_paragraph("DDR-MoreDetails")
                attr_name = attr.get_type().type2base()
                # Translators: needed for French, ignore otherwise
                text = self._("%(type)s: %(value)s%(endnotes)s") % {
                    "type": self._(attr_name),
                    "value": attr.get_value(),
                    "endnotes": self.endnotes(attr),
                }
                self.doc.write_text_citation(text)
                self.doc.end_paragraph()

    # ---------------------------------------------------------------------------------------------------

    def endnotes(self, obj):
        """write out any endnotes/footnotes"""
        if not obj or not self.inc_sources:
            return ""

        txt = endnotes.cite_source(self.bibli, self._db, obj, self._locale)
        if txt:
            txt = "<super>" + txt + "</super>"
        return txt


# ------------------------------------------------------------------------
#
# DetDescendantOptions
#
# ------------------------------------------------------------------------
class LatexDownOptions(MenuReportOptions):

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

    def add_menu_options(self, menu):
        """
        Add options to the menu for the detailed descendant report.
        """

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

        numbering = EnumeratedListOption(_("Numbering system"), "Henry")
        numbering.set_items(
            [
                ("Henry", _("Henry numbering")),
                ("Modified Henry", _("Modified Henry numbering")),
                ("d'Aboville", _("d'Aboville numbering")),
                (
                    "Record (Modified Register)",
                    _("Record (Modified Register) numbering"),
                ),
            ]
        )
        numbering.set_help(_("The numbering system to be used"))
        add_option("numbering", numbering)

        structure = EnumeratedListOption(_("Report structure"), "by generation")
        structure.set_items(
            [
                ("by generation", _("show people by generations")),
                ("by lineage", _("show people by lineage")),
            ]
        )
        structure.set_help(_("How people are organized in the report"))
        add_option("structure", structure)

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

        # stdoptions.add_name_format_option(menu, category)
        self._nf = stdoptions.add_name_format_option(menu, category)
        self._nf.connect("value-changed", self.__update_filters)
        self.__update_filters()

        stdoptions.add_place_format_option(menu, category)

        stdoptions.add_private_data_option(menu, category)

        stdoptions.add_living_people_option(menu, category)

        locale_opt = stdoptions.add_localization_option(menu, category)

        stdoptions.add_date_format_option(menu, category, locale_opt)

        # Tags

        add_option = partial(menu.add_option, _("Tags"))
        inctags = BooleanOption(_("Include Tags"), False)
        inctags.set_help(_("Whether to include tags in the margin notes."))
        add_option("inctags", inctags)

        # Content

        add_option = partial(menu.add_option, _("Content"))

        verbose = BooleanOption(_("Use complete sentences"), True)
        verbose.set_help(_("Whether to use complete sentences or succinct language."))
        add_option("verbose", verbose)

        fulldates = BooleanOption(_("Use full dates instead of only the year"), True)
        fulldates.set_help(_("Whether to use full dates instead of just year."))
        add_option("fulldates", fulldates)

        computeage = BooleanOption(_("Compute death age"), True)
        computeage.set_help(_("Whether to compute a person's age at death."))
        add_option("computeage", computeage)

        usecall = BooleanOption(_("Use callname for common name"), False)
        usecall.set_help(_("Whether to use the call name as the first name."))
        add_option("usecall", usecall)

        # What to include

        add_option = partial(menu.add_option, _("Include"))

        listc = BooleanOption(_("Include children"), True)
        listc.set_help(_("Whether to list children."))
        add_option("listc", listc)

        listc_spouses = BooleanOption(_("Include spouses of children"), False)
        listc_spouses.set_help(_("Whether to list the spouses of the children."))
        add_option("listc_spouses", listc_spouses)

        incmates = BooleanOption(_("Include spouses"), False)
        incmates.set_help(_("Whether to include detailed spouse information."))
        add_option("incmates", incmates)

        incmateref = BooleanOption(_("Include spouse reference"), False)
        incmateref.set_help(_("Whether to include reference to spouse."))
        add_option("incmateref", incmateref)

        incevents = BooleanOption(_("Include events"), False)
        incevents.set_help(_("Whether to include events."))
        add_option("incevents", incevents)

        desref = BooleanOption(_("Include descendant reference in child list"), True)
        desref.set_help(_("Whether to add descendant references in child list."))
        add_option("desref", desref)

        incphotos = BooleanOption(_("Include Photo/Images from Gallery"), False)
        incphotos.set_help(_("Whether to include images."))
        add_option("incphotos", incphotos)

        add_option = partial(menu.add_option, _("Include (2)"))

        incnotes = BooleanOption(_("Include notes"), True)
        incnotes.set_help(_("Whether to include notes."))
        add_option("incnotes", incnotes)

        incsources = BooleanOption(_("Include sources"), False)
        incsources.set_help(_("Whether to include source references."))
        add_option("incsources", incsources)

        incsrcnotes = BooleanOption(_("Include sources notes"), False)
        incsrcnotes.set_help(
            _(
                "Whether to include source notes in the "
                "Endnotes section. Only works if Include sources is selected."
            )
        )
        add_option("incsrcnotes", incsrcnotes)

        incattrs = BooleanOption(_("Include attributes"), False)
        incattrs.set_help(_("Whether to include attributes."))
        add_option("incattrs", incattrs)

        incaddresses = BooleanOption(_("Include addresses"), False)
        incaddresses.set_help(_("Whether to include addresses."))
        add_option("incaddresses", incaddresses)

        incnames = BooleanOption(_("Include alternative names"), False)
        incnames.set_help(_("Whether to include other names."))
        add_option("incnames", incnames)

        incssign = BooleanOption(
            _("Include sign of succession ('+') in child-list"), True
        )
        incssign.set_help(
            _(
                "Whether to include a sign ('+') before the"
                " descendant number in the child-list to indicate"
                " a child has succession."
            )
        )
        add_option("incssign", incssign)

        incpaths = BooleanOption(_("Include path to start-person"), False)
        incpaths.set_help(
            _(
                "Whether to include the path of descendancy "
                "from the start-person to each descendant."
            )
        )
        add_option("incpaths", incpaths)

        # How to handle missing information
        add_option = partial(menu.add_option, _("Missing information"))

        repplace = BooleanOption(_("Replace missing places with ______"), False)
        repplace.set_help(_("Whether to replace missing Places with blanks."))
        add_option("repplace", repplace)

        repdate = BooleanOption(_("Replace missing dates with ______"), False)
        repdate.set_help(_("Whether to replace missing Dates with blanks."))
        add_option("repdate", repdate)

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
        default_style.add_paragraph_style("DDR-Title", para)

        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=14, italic=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_header_level(2)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_("The style used for the generation header."))
        default_style.add_paragraph_style("DDR-Generation", para)

        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=10, italic=0, bold=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_left_margin(1.5)  # in centimeters
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_("The style used for the children list title."))
        default_style.add_paragraph_style("DDR-ChildTitle", para)

        font = FontStyle()
        font.set(size=10)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(first_indent=-0.75, lmargin=2.25)
        para.set_top_margin(0.125)
        para.set_bottom_margin(0.125)
        para.set_description(_("The style used for the text related to the children."))
        default_style.add_paragraph_style("DDR-ChildList", para)

        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=10, italic=0, bold=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(first_indent=0.0, lmargin=1.5)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_("The style used for the note header."))
        default_style.add_paragraph_style("DDR-NoteHeader", para)

        para = ParagraphStyle()
        para.set(lmargin=1.5)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_("The basic style used for the text display."))
        default_style.add_paragraph_style("DDR-Entry", para)

        para = ParagraphStyle()
        para.set(first_indent=-1.5, lmargin=1.5)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_("The style used for first level headings."))
        default_style.add_paragraph_style("DDR-First-Entry", para)

        font = FontStyle()
        font.set(size=10, face=FONT_SANS_SERIF, bold=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(first_indent=0.0, lmargin=1.5)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_("The style used for second level headings."))
        default_style.add_paragraph_style("DDR-MoreHeader", para)

        font = FontStyle()
        font.set(face=FONT_SERIF, size=10)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(first_indent=0.0, lmargin=1.5)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_("The style used for details."))
        default_style.add_paragraph_style("DDR-MoreDetails", para)

        endnotes.add_endnote_styles(default_style)
