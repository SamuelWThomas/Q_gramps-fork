#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2002-2006  Donald N. Allingham
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

# -------------------------------------------------------------------------
#
# Standard Python modules
#
# -------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale

_ = glocale.translation.gettext
try:
    set()
except NameError:
    from sets import Set as set

# -------------------------------------------------------------------------
#
# Gramps modules
#
# -------------------------------------------------------------------------
from gramps.gen.filters.rules import Rule


# -------------------------------------------------------------------------
#
# IsDescendantFamilyOf
#
# -------------------------------------------------------------------------
class IsDescendantFamilyOfInLessThanNthGeneration(Rule):
    """Rule that checks for a person that is a descendant or the spouse
    of a descendant of a specified person not more than N generations away"""

    labels = [_("ID:"), _("Number of generations:"), _("Inclusive:"), _("Exclude:")]
    name = _(
        "Q:Descendant family members of <person> not more than <N> generations away"
    )
    category = _("Descendant filters")
    description = _(
        "Matches people that are descendants or the spouse "
        "of a descendant of a specified person not more than N generations away "
        "and exclusing people in Exclude."
    )

    def prepare(self, db, user):
        self.db = db
        self.matches = set()
        self.root_person = db.get_person_from_gramps_id(self.list[0])
        self.max_gen = int(self.list[1])
        self.add_matches(self.root_person, 0) 
        try:
            if int(self.list[2]):
                inclusive = True
            else:
                inclusive = False
        except IndexError:
            inclusive = True
        if not inclusive:
            self.exclude_root_person()
        exclude_list = self.list[3].split(',') if self.list[3] else []
        self.exclude_persons(exclude_list)


    def reset(self):
        self.matches = set()

    def apply(self, db, person):
        return person.handle in self.matches

    def add_matches(self, person, gen):
        if person is None or person.handle in self.matches:
            # if we have been here before, skip
            return
        self.matches.add(person.handle)
        
        for family_handle in person.get_family_handle_list():
            family = self.db.get_family_from_handle(family_handle)
            if family:
                # Add spouse
                if person.handle == family.get_father_handle():
                    spouse_handle = family.get_mother_handle()
                else:
                    spouse_handle = family.get_father_handle()
                self.matches.add(spouse_handle)

                if gen >= self.max_gen:
                    continue
                # Add every child recursively
                for child_ref in family.get_child_ref_list():
                    if child_ref:
                        self.add_matches(
                            self.db.get_person_from_handle(child_ref.ref), gen + 1
                        )
                

    def exclude_root_person(self):
        # This removes root person and his/her spouses from the matches set
        if not self.root_person:
            return
        self.matches.remove(self.root_person.handle)
        for family_handle in self.root_person.get_family_handle_list():
            family = self.db.get_family_from_handle(family_handle)
            if family:
                if self.root_person.handle == family.get_father_handle():
                    spouse_handle = family.get_mother_handle()
                else:
                    spouse_handle = family.get_father_handle()
                self.matches.remove(spouse_handle)

    def exclude_persons(self, excludes):
        for exclude in excludes:
            person = self.db.get_person_from_gramps_id(exclude)
            self.matches.remove(person.handle)