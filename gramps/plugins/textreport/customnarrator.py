"""
Custom Narrator class for use by Obsidian Report and LaTeX Report plugins.
"""

# ------------------------------------------------------------------------
#
# Gramps modules
#
# ------------------------------------------------------------------------
from gramps.gen.lib.date import Date
from gramps.gen.lib.person import Person
from gramps.gen.lib.eventroletype import EventRoleType
from gramps.gen.lib.eventtype import EventType
from gramps.gen.lib.familyreltype import FamilyRelType
from gramps.gen.display.name import displayer as _nd
from gramps.gen.display.place import displayer as _pd
from gramps.gen.utils.alive import probably_alive
from gramps.gen.plug.report import utils
from gramps.gen.const import GRAMPS_LOCALE as glocale

# -------------------------------------------------------------------------
#
# Private constants
#
# -------------------------------------------------------------------------
# In string arrays, the first strings should include the name, the second
# strings should not include the name.
_NAME_INDEX_INCLUDE_NAME = 0
_NAME_INDEX_EXCLUDE_NAME = 1

# In string arrays, the first strings should not include age.
# The following strings should include year, month and day units.
# And support format with precision (see gen/lib/date.py).
_AGE_INDEX_NO_AGE = 0
_AGE_INDEX = 1

# -------------------------------------------------------------------------
#
# Private functions
#
# -------------------------------------------------------------------------

# ------------------------------------------------------------------------
#
# Born strings
#
# ------------------------------------------------------------------------
born_full_date_with_place = [
    "Geboren %(birth_date)s in %(birth_place)s.",
    "Geboren: %(birth_date)s in [[%(birth_place)s]]",
    "\geb\,%(birth_date)s, \place{%(birth_place)s},",
]

born_modified_date_with_place = [
    "Geboren %(modified_date)s in %(birth_place)s.",
    "Geboren: %(modified_date)s in [[%(birth_place)s]]",
    "\geb\,%(modified_date)s, place{%(birth_place)s},",
]

born_full_date_no_place = [
    "Geboren %(birth_date)s.",
    "Geboren: %(birth_date)s",
    "\geb\,%(birth_date)s,",
]

born_modified_date_no_place = [
    "Geboren %(modified_date)s.",
    "Geboren: %(modified_date)s",
    "\geb\,%(modified_date)s,",
]

born_partial_date_with_place = [
    "Geboren %(month_year)s in %(birth_place)s.",
    "Geboren: %(month_year)s in [[%(birth_place)s]]",
    "\geb\,%(month_year)s in %(birth_place)s,",
]

born_partial_date_no_place = [
    "Geboren %(month_year)s.",
    "Geboren: %(month_year)s",
    "\geb\,%(month_year)s,",
]

born_no_date_with_place = [
    "Geboren in %(birth_place)s.",
    "Geboren: in [[%(birth_place)s]]",
    "\geb\,\place{%(birth_place)s},",
]

# ------------------------------------------------------------------------
#
# Died strings
#
# ------------------------------------------------------------------------
died_full_date_with_place = [
    ["Gestorben %(death_date)s in %(death_place)s.", "Gestorben %(death_date)s in %(death_place)s (%(age)s).",],
    ["Gestorben: %(death_date)s in [[%(death_place)s]]", "Gestorben: %(death_date)s in [[%(death_place)s]] (%(age)s)",],
    ["\\tod\,%(death_date)s, \place{%(death_place)s},", "\\tod\,%(death_date)s, \place{%(death_place)s} (%(age)s),",],
]

died_modified_date_with_place = [
    ["Gestorben %(death_date)s in %(death_place)s.", "Gestorben %(death_date)s in %(death_place)s (%(age)s).",],
    ["Gestorben: %(death_date)s in [[%(death_place)s]]", "Gestorben: %(death_date)s in [[%(death_place)s]] (%(age)s)",],
    ["\\tod\,%(death_date)s, \place{%(death_place)s},", "\\tod\,%(death_date)s, \place{%(death_place)s} (%(age)s),",],
]

died_full_date_no_place = [
    ["Gestorben %(death_date)s.", "Gestorben %(death_date)s (%(age)s).",],
    ["Gestorben: %(death_date)s", "Gestorben: %(death_date)s (%(age)s)",],
    ["\\tod\,%(death_date)s,", "\\tod\,%(death_date)s (%(age)s),",],
]

died_modified_date_no_place = [
    ["Gestorben %(death_date)s.", "Gestorben %(death_date)s (%(age)s).",],
    ["Gestorben: %(death_date)s", "Gestorben: %(death_date)s (%(age)s)",],
    ["\\tod\,%(death_date)s,", "\\tod\,%(death_date)s (%(age)s),",],
]

died_partial_date_with_place = [
    ["Gestorben %(month_year)s in %(death_place)s.", "Gestorben %(month_year)s in %(death_place)s (%(age)s).",],
    ["Gestorben: %(month_year)s in [[%(death_place)s]]", "Gestorben: %(month_year)s in [[%(death_place)s]] (%(age)s)",],
    ["\\tod\,%(month_year)s, \place{%(death_place)s},", "\\tod\,%(month_year)s, \place{%(death_place)s} (%(age)s),",],
]

died_partial_date_no_place = [
    ["Gestorben %(month_year)s.", "Gestorben %(month_year)s (%(age)s).",],
    ["Gestorben: %(month_year)s", "Gestorben: %(month_year)s (%(age)s)",],
    ["\\tod\,%(month_year)s,", "\\tod\,%(month_year)s (%(age)s),",],
]

died_no_date_with_place = [
    ["Gestorben in %(death_place)s.", "Gestorben in %(death_place)s (%(age)s).",],
    ["Gestorben: in [[%(death_place)s]]", "Gestorben: in [[%(death_place)s]] (%(age)s)",],
    ["\\tod\,\place{%(death_place)s},", "\\tod\,\place{%(death_place)s} (%(age)s),",],
]

died_no_date_no_place = [
    ["", "Gestorben (%(age)s).",],
    ["", "Gestorben: (%(age)s)",],
    ["", "\\tod\,(%(age)s),",],
]

# ------------------------------------------------------------------------
#
# Buried strings
#
# ------------------------------------------------------------------------
buried_full_date_place = [
    "Begraben %(burial_date)s in %(burial_place)s%(endnotes)s.",
    "Begraben: %(burial_date)s in [[%(burial_place)s]]%(endnotes)s",
    "\\begraben\,%(burial_date)s, \place{%(burial_place)s}%(endnotes)s,",
]

buried_full_date_no_place = [
    "Begraben %(burial_date)s%(endnotes)s.",
    "Begraben: %(burial_date)s%(endnotes)s",
    "\\begraben\,%(burial_date)s%(endnotes)s,",
]

buried_partial_date_place = [
    "Begraben %(month_year)s in %(burial_place)s%(endnotes)s.",
    "Begraben: %(month_year)s in [[%(burial_place)s]]%(endnotes)s",
    "\\begraben\,%(month_year)s, \place{%(burial_place)s}%(endnotes)s,",
]

buried_partial_date_no_place = [
    "Begraben %(month_year)s%(endnotes)s.",
    "Begraben: %(month_year)s%(endnotes)s",
    "\\begraben\,%(month_year)s%(endnotes)s,",
]

buried_modified_date_place = [
    "Begraben %(modified_date)s in %(burial_place)s%(endnotes)s.",
    "Begraben: %(modified_date)s in [[%(burial_place)s]]%(endnotes)s",
    "\\begraben\,%(modified_date)s, \place{%(burial_place)s}%(endnotes)s,",
]

buried_modified_date_no_place = [
    "Begraben %(modified_date)s%(endnotes)s.",
    "Begraben: %(modified_date)s%(endnotes)s",
    "\\begraben\,%(modified_date)s%(endnotes)s,",
]

buried_no_date_place = [
    "Begraben in %(burial_place)s%(endnotes)s.",
    "Begraben: in [[%(burial_place)s]]%(endnotes)s",
    "\\begraben\,\place{%(burial_place)s}%(endnotes)s,",
]

buried_no_date_no_place = [
    "Begraben%(endnotes)s.",
    "Begraben:%(endnotes)s",
    "\\begraben\,(endnotes)s,",
]
# ------------------------------------------------------------------------
#
# Baptized strings
#
# ------------------------------------------------------------------------
baptised_full_date_place = [
    "Getauft %(baptism_date)s in %(baptism_place)s%(endnotes)s.",
    "Getauft: %(baptism_date)s in [[%(baptism_place)s]]%(endnotes)s",
    "\\taufe\,%(baptism_date)s, \place{%(baptism_place)s}%(endnotes)s,",
]

baptised_full_date_no_place = [
    "Getauft %(baptism_date)s%(endnotes)s.",
    "Getauft: %(baptism_date)s%(endnotes)s",
    "\\taufe\,%(baptism_date)s%(endnotes)s,",
]

baptised_partial_date_place = [
    "Getauft %(month_year)s in %(baptism_place)s%(endnotes)s.",
    "Getauft: %(month_year)s in [[%(baptism_place)s]]%(endnotes)s",
    "\\taufe\,%(month_year)s, \place{%(baptism_place)s}%(endnotes)s,",
]

baptised_partial_date_no_place = [
    "Getauft %(month_year)s%(endnotes)s.",
    "Getauft: %(month_year)s%(endnotes)s",
    "\\taufe\,%(month_year)s%(endnotes)s,",
]

baptised_modified_date_place = [
    "Getauft %(modified_date)s in %(baptism_place)s%(endnotes)s.",
    "Getauft: %(modified_date)s in [[%(baptism_place)s]]%(endnotes)s",
    "\\taufe\,%(modified_date)s, \place{%(baptism_place)s}%(endnotes)s,",
]

baptised_modified_date_no_place = [
    "Getauft %(modified_date)s%(endnotes)s.",
    "Getauft: %(modified_date)s%(endnotes)s",
    "\\taufe\,%(modified_date)s%(endnotes)s,",
]

baptised_no_date_place = [
    "Getauft in %(baptism_place)s%(endnotes)s.",
    "Getauft: in [[%(baptism_place)s]]%(endnotes)s",
    "\\taufe\,\place{%(baptism_place)s}%(endnotes)s,",
]

baptised_no_date_no_place = [
    "Getauft%(endnotes)s.",
    "Getauft%(endnotes)s",
    "\\taufe%(endnotes)s,",
]

# ------------------------------------------------------------------------
#
# Christened strings
#
# ------------------------------------------------------------------------
christened_full_date_place = [
    "Getauft %(christening_date)s in %(christening_place)s%(endnotes)s.",
    "Getauft: %(christening_date)s in [[%(christening_place)s]]%(endnotes)s",
    "\\taufe\,%(christening_date)s, \place{%(christening_place)s}%(endnotes)s,",
]

christened_full_date_no_place = [
    "Getauft %(christening_date)s%(endnotes)s.",
    "Getauft: %(christening_date)s%(endnotes)s",
    "\\taufe\,%(christening_date)s%(endnotes)s,",
]

christened_partial_date_place = [
    "Getauft %(month_year)s in %(christening_place)s%(endnotes)s.",
    "Getauft: %(month_year)s in [[%(christening_place)s]]%(endnotes)s",
    "\\taufe\,%(month_year)s, \place{%(christening_place)s}%(endnotes)s,",
]

christened_partial_date_no_place = [
    "Getauft %(month_year)s%(endnotes)s.",
    "Getauft: %(month_year)s%(endnotes)s",
    "\\taufe\,%(month_year)s%(endnotes)s,",
]

christened_modified_date_place = [
    "Getauft %(modified_date)s in %(christening_place)s%(endnotes)s.",
    "Getauft: %(modified_date)s in [[%(christening_place)s]]%(endnotes)s",
    "\\taufe\,%(modified_date)s, \place{%(christening_place)s}%(endnotes)s,",
]

christened_modified_date_no_place = [
    "Getauft %(modified_date)s%(endnotes)s.",
    "Getauft: %(modified_date)s%(endnotes)s",
    "\\taufe\,%(modified_date)s%(endnotes)s,",
]

christened_no_date_place = [
    "Getauft in %(christening_place)s%(endnotes)s.",
    "Getauft: in [[%(christening_place)s]]%(endnotes)s",
    "\\taufe\,\place{%(christening_place)s}%(endnotes)s,",
]

christened_no_date_no_place = [
    "Getauft%(endnotes)s.",
    "Getauft%(endnotes)s",
    "\\taufe%(endnotes)s,",
]

# ------------------------------------------------------------------------
#
# Marriage strings - Relationship type MARRIED
#
# ------------------------------------------------------------------------
marriage_first_date_place = [
    [
        "Heiratete %(spouse)s %(partial_date)s in %(place)s%(endnotes)s.",
        "Heiratete %(spouse)s %(full_date)s in %(place)s%(endnotes)s.",
        "Heiratete %(spouse)s %(modified_date)s in %(place)s%(endnotes)s.",
    ],
    [
        "Hochzeit: %(spouse)s %(partial_date)s in %(place)s%(endnotes)s",
        "Hochzeit: %(spouse)s %(full_date)s in %(place)s%(endnotes)s",
        "Hochzeit: %(spouse)s %(modified_date)s in %(place)s%(endnotes)s",
    ],
    [
        "\heirat\,%(spouse)s, %(partial_date)s, \place{%(place)s}%(endnotes)s.",
        "\heirat\,%(spouse)s, %(full_date)s, \place{%(place)s}%(endnotes)s.",
        "\heirat\,%(spouse)s, %(modified_date)s, \place{%(place)s}%(endnotes)s.",
    ],
]

marriage_also_date_place = marriage_first_date_place

marriage_first_date = [
    [
        "Heiratete %(spouse)s %(partial_date)s%(endnotes)s.",
        "Heiratete %(spouse)s %(full_date)s%(endnotes)s.",
        "Heiratete %(spouse)s %(modified_date)s%(endnotes)s.",
    ],
    [
        "Hochzeit: %(spouse)s %(partial_date)s%(endnotes)s",
        "Hochzeit: %(spouse)s %(full_date)s%(endnotes)s",
        "Hochzeit: %(spouse)s %(modified_date)s%(endnotes)s",
    ],
    [
        "\heirat\,%(spouse)s, %(partial_date)s%(endnotes)s.",
        "\heirat\,%(spouse)s, %(full_date)s%(endnotes)s.",
        "\heirat\,%(spouse)s, %(modified_date)s%(endnotes)s.",
    ],
]

marriage_also_date = marriage_first_date

marriage_first_place = [
    "Heiratete %(spouse)s in %(place)s%(endnotes)s.",
    "Hochzeit: %(spouse)s in %(place)s%(endnotes)s",
    "\heirat\,%(spouse)s, \place{%(place)s}%(endnotes)s.",
]

marriage_also_place = marriage_first_place

marriage_first_only = [
    "Heiratete %(spouse)s%(endnotes)s.",
    "Hochzeit: %(spouse)s%(endnotes)s",
    "\heirat\,%(spouse)s%(endnotes)s.",
]

marriage_also_only = marriage_first_only

# ------------------------------------------------------------------------
#
# Marriage strings - Relationship type UNMARRIED
#
# ------------------------------------------------------------------------
unmarried_first_date_place = [
    [
        "Partner: %(spouse)s %(partial_date)s in %(place)s%(endnotes)s.",
        "Partner: %(spouse)s %(full_date)s in %(place)s%(endnotes)s.",
        "Partner: %(spouse)s %(modified_date)s in %(place)s%(endnotes)s.",
    ],
    [
        "Partner: %(spouse)s %(partial_date)s in %(place)s%(endnotes)s",
        "Partner: %(spouse)s %(full_date)s in %(place)s%(endnotes)s",
        "Partner: %(spouse)s %(modified_date)s in %(place)s%(endnotes)s",
    ],
    [
        "\partner\,%(spouse)s, %(partial_date)s, \place{%(place)s}%(endnotes)s.",
        "\partner\,%(spouse)s, %(full_date)s, \place{%(place)s}%(endnotes)s.",
        "\partner\,%(spouse)s, %(modified_date)s, \place{%(place)s}%(endnotes)s.",
    ],
]

unmarried_also_date_place = unmarried_first_date_place

unmarried_first_date = [
    [
        "Partner: %(spouse)s %(partial_date)s%(endnotes)s.",
        "Partner: %(spouse)s %(full_date)s%(endnotes)s.",
        "Partner: %(spouse)s %(modified_date)s%(endnotes)s.",
    ],
    [
        "Partner: %(spouse)s %(partial_date)s%(endnotes)s",
        "Partner: %(spouse)s %(full_date)s%(endnotes)s",
        "Partner: %(spouse)s %(modified_date)s%(endnotes)s",
    ],
    [
        "\partner\,%(spouse)s, %(partial_date)s%(endnotes)s.",
        "\partner\,%(spouse)s, %(full_date)s%(endnotes)s.",
        "\partner\,%(spouse)s, %(modified_date)s%(endnotes)s.",
    ],
]

unmarried_also_date = unmarried_first_date

unmarried_first_place = [
    "Partner: %(spouse)s in %(place)s%(endnotes)s.",
    "Partner: %(spouse)s in %(place)s%(endnotes)s",
    "\partner\,%(spouse)s, \place{%(place)s}%(endnotes)s.",
]

unmarried_also_place = unmarried_first_place

unmarried_first_only = [
    "Partner: %(spouse)s%(endnotes)s.",
    "Partner: %(spouse)s%(endnotes)s",
    "\partner\,%(spouse)s%(endnotes)s.",
]

unmarried_also_only = unmarried_first_only

# ------------------------------------------------------------------------
#
# Marriage strings - Relationship type other than MARRIED or UNMARRIED
#                    i.e. CIVIL UNION or CUSTOM
#
# ------------------------------------------------------------------------
relationship_first_date_place = unmarried_first_date_place

relationship_also_date_place = relationship_first_date_place

relationship_first_date = unmarried_first_date

relationship_also_date = relationship_first_date

relationship_first_place = unmarried_first_place

relationship_also_place = relationship_first_place

relationship_first_only = unmarried_first_only

relationship_also_only = relationship_first_only

#-------------------------------------------------------------------------
#
#  child to parent relationships
#
#-------------------------------------------------------------------------
child_father_mother = {
    Person.UNKNOWN: [
      [
        ("%(male_name)s is the child of %(father)s and %(mother)s."),
        ("%(male_name)s was the child of %(father)s and %(mother)s."),
      ],
      [
        ("This person is the child of %(father)s and %(mother)s."),
        ("This person was the child of %(father)s and %(mother)s."),
      ],
      ("Child of %(father)s and %(mother)s."),
    ],
    Person.MALE : [
      [
        ("%(male_name)s is the son of %(father)s and %(mother)s."),
        ("%(male_name)s was the son of %(father)s and %(mother)s."),
      ],
      [
        ("He is the son of %(father)s and %(mother)s."),
        ("He was the son of %(father)s and %(mother)s."),
      ],
      ("Son of %(father)s and %(mother)s."),
    ],
    Person.FEMALE : [
     [
        ("%(female_name)s is the daughter of %(father)s and %(mother)s."),
        ("%(female_name)s was the daughter of %(father)s and %(mother)s."),
     ],
     [
        ("She is the daughter of %(father)s and %(mother)s."),
        ("She was the daughter of %(father)s and %(mother)s."),
     ],
     ("Daughter of %(father)s and %(mother)s."),
    ]
}

child_father = {
    Person.UNKNOWN : [
      [
        ("%(male_name)s is the child of %(father)s."),
        ("%(male_name)s was the child of %(father)s."),
      ],
      [
        ("This person is the child of %(father)s."),
        ("This person was the child of %(father)s."),
      ],
      ("Child of %(father)s."),
    ],
    Person.MALE : [
      [
        ("%(male_name)s is the son of %(father)s."),
        ("%(male_name)s was the son of %(father)s."),
      ],
      [
        ("He is the son of %(father)s."),
        ("He was the son of %(father)s."),
      ],
      ("Son of %(father)s."),
    ],
    Person.FEMALE : [
      [
        ("%(female_name)s is the daughter of %(father)s."),
        ("%(female_name)s was the daughter of %(father)s."),
      ],
      [
        ("She is the daughter of %(father)s."),
        ("She was the daughter of %(father)s."),
      ],
      ("Daughter of %(father)s."),
    ],
}

child_mother = {
    Person.UNKNOWN : [
      [
        ("%(male_name)s is the child of %(mother)s."),
        ("%(male_name)s was the child of %(mother)s."),
      ],
      [
        ("This person is the child of %(mother)s."),
        ("This person was the child of %(mother)s."),
      ],
      ("Child of %(mother)s."),
    ],
    Person.MALE : [
      [
        ("%(male_name)s is the son of %(mother)s."),
        ("%(male_name)s was the son of %(mother)s."),
      ],
      [
        ("He is the son of %(mother)s."),
        ("He was the son of %(mother)s."),
      ],
      ("Son of %(mother)s."),
    ],
    Person.FEMALE : [
      [
        ("%(female_name)s is the daughter of %(mother)s."),
        ("%(female_name)s was the daughter of %(mother)s."),
      ],
      [
        ("She is the daughter of %(mother)s."),
        ("She was the daughter of %(mother)s."),
      ],
      ("Daughter of %(mother)s."),
   ],
}

FORMAT_NORMALTEXT = 0
FORMAT_MARKDOWN = 1
FORMAT_LATEX = 2
# ------------------------------------------------------------------------
#
# Narrator
#
# ------------------------------------------------------------------------
class CustomNarrator:
    """
    Narrator is a class which provides narration text.
    """

    def __init__(
        self,
        dbase,
        verbose=True,
        use_call_name=False,
        use_fulldate=False,
        empty_date="",
        empty_place="",
        place_format=-1,
        nlocale=glocale,
        format=FORMAT_NORMALTEXT,
    ):
        """
        Initialize the narrator class.

        If nlocale is passed in (a GrampsLocale), then
        the translated values will be returned instead.

        :param dbase: The database that contains the data to be narrated.
        :type dbase: :class:`~gen.db.base,DbBase`
        :param verbose: Specifies whether complete sentences should be used.
        :type verbose: bool
        :param use_call_name: Specifies whether a person's call name should be
            used for the first name.
        :type use_call_name: bool
        :param empty_date: String to use when a date is not known.
        :type empty_date: str
        :param empty_place: String to use when a place is not known.
        :type empty_place: str
        :param get_endnote_numbers: A callable to use for getting a string
            representing endnote numbers.
            The function takes a :class:`~gen.lib.CitationBase` instance.
            A typical return value from get_endnote_numbers() would be "2a" and
            would represent a reference to an endnote in a document.
        :type get_endnote_numbers:
            callable( :class:`~gen.lib.CitationBase` )
        :param nlocale: allow deferred translation of dates and strings
        :type nlocale: a GrampsLocale instance
        :param place_format: allow display of places in any place format
        :type place_format: int
        """
        self.__db = dbase
        self.__verbose = verbose
        self.__use_call = use_call_name
        self.__use_fulldate = use_fulldate
        self.__empty_date = empty_date
        self.__empty_place = empty_place
        self.__person = None
        self.__first_name = ""
        self.__first_name_used = False

        self.__translate_text = nlocale.translation.gettext
        self.__get_date = nlocale.get_date
        self._locale = nlocale
        self._place_format = place_format

        self.__format_number = format

    def set_subject(self, person):
        """
        Start a new story about this person. The person's first name will be
        used in the first sentence. A pronoun will be used as the subject for
        each subsequent sentence.
        :param person: The person to be the subject of the story.
        :type person: :class:`~gen.lib.person,Person`
        """
        self.__person = person

        if self.__use_call and person.get_primary_name().get_call_name():
            self.__first_name = person.get_primary_name().get_call_name()
        else:
            self.__first_name = person.get_primary_name().get_first_name()

        if self.__first_name:
            self.__first_name_used = False  # use their name the first time
        else:
            self.__first_name_used = True  # but use a pronoun if no name

    def get_born_string(self):
        """
        Get a string narrating the birth of the subject.
        Example sentences:
            Person was born on Date.
            Person was born on Date in Place.
            Person was born in Place.
            ''

        :returns: A sentence about the subject's birth.
        :rtype: unicode
        """

        text = ""

        bplace = self.__empty_place
        bdate = self.__empty_date
        birth_event = None
        bdate_full = False
        bdate_mod = False

        birth_ref = self.__person.get_birth_ref()
        if birth_ref and birth_ref.ref:
            birth_event = self.__db.get_event_from_handle(birth_ref.ref)
            if birth_event:
                if self.__use_fulldate:
                    bdate = self.__get_date(birth_event.get_date_object())
                else:
                    bdate = birth_event.get_date_object().get_year()
                bplace_handle = birth_event.get_place_handle()
                if bplace_handle:
                    place = self.__db.get_place_from_handle(bplace_handle)
                    bplace = _pd.display_event(
                        self.__db, birth_event, fmt=self._place_format
                    )
                bdate_obj = birth_event.get_date_object()
                bdate_full = bdate_obj and bdate_obj.get_day_valid()
                #if bdate_full: bdate = f"{bdate.split('-')[2]}.{bdate.split('-')[1]}.{bdate.split('-')[0]}"
                bdate_mod = bdate_obj and bdate_obj.get_modifier() != Date.MOD_NONE

        value_map = {
            "name": self.__first_name,
            "male_name": self.__first_name,
            "unknown_gender_name": self.__first_name,
            "female_name": self.__first_name,
            "birth_date": bdate,
            "birth_place": bplace,
            "month_year": bdate,
            "modified_date": bdate,
        }

        if bdate:
            if bdate_mod:
                if bplace:
                    text = born_modified_date_with_place[self.__format_number]
                else:
                    text = born_modified_date_no_place[self.__format_number]
            elif bdate_full:
                if bplace:
                    text = born_full_date_with_place[self.__format_number]
                else:
                    text = born_full_date_no_place[self.__format_number]
            else:
                if bplace:
                    text = born_partial_date_with_place[self.__format_number]
                else:
                    text = born_partial_date_no_place[self.__format_number]
        else:
            if bplace:
                text = born_no_date_with_place[self.__format_number]
            else:
                text = ""

        if text:
            text = text % value_map

        return text

    def get_died_string(self, include_age=False):
        """
        Get a string narrating the death of the subject.
        Example sentences:
            Person died on Date
            Person died on Date at the age of 'age'
            Person died on Date in Place
            Person died on Date in Place at the age of 'age'
            Person died in Place
            Person died in Place at the age of 'age'
            Person died
            ''
        where 'age' string is an advanced age calculation.

        :returns: A sentence about the subject's death.
        :rtype: unicode
        """

        text = ""

        dplace = self.__empty_place
        ddate = self.__empty_date
        death_event = None
        ddate_full = False
        ddate_mod = False

        death_ref = self.__person.get_death_ref()
        if death_ref and death_ref.ref:
            death_event = self.__db.get_event_from_handle(death_ref.ref)
            if death_event:
                if self.__use_fulldate:
                    ddate = self.__get_date(death_event.get_date_object())
                else:
                    ddate = death_event.get_date_object().get_year()
                dplace_handle = death_event.get_place_handle()
                if dplace_handle:
                    place = self.__db.get_place_from_handle(dplace_handle)
                    dplace = _pd.display_event(
                        self.__db, death_event, fmt=self._place_format
                    )
                ddate_obj = death_event.get_date_object()
                ddate_full = ddate_obj and ddate_obj.get_day_valid()
                ddate_mod = ddate_obj and ddate_obj.get_modifier() != Date.MOD_NONE

        if include_age:
            age, age_index = self.__get_age_at_death()
        else:
            age = 0
            age_index = _AGE_INDEX_NO_AGE

        value_map = {
            "name": self.__first_name,
            "unknown_gender_name": self.__first_name,
            "male_name": self.__first_name,
            "female_name": self.__first_name,
            "death_date": ddate,
            "modified_date": ddate,
            "death_place": dplace,
            "age": age,
            "month_year": ddate,
        }

        if ddate and ddate_mod:
            if dplace:
                text = died_modified_date_with_place[self.__format_number][age_index]
            else:
                text = died_modified_date_no_place[self.__format_number][age_index]
        elif ddate and ddate_full:
            if dplace:
                text = died_full_date_with_place[self.__format_number][age_index]
            else:
                text = died_full_date_no_place[self.__format_number][age_index]
        elif ddate:
            if dplace:
                text = died_partial_date_with_place[self.__format_number][age_index]
            else:
                text = died_partial_date_no_place[self.__format_number][age_index]
        elif dplace:
            text = died_no_date_with_place[self.__format_number][age_index]
        else:
            text = died_no_date_no_place[self.__format_number][age_index]

        if text:
            text = text % value_map

        return text

    def get_buried_string(self):
        """
        Get a string narrating the burial of the subject.
        Example sentences:
            Person was  buried on Date.
            Person was  buried on Date in Place.
            Person was  buried in Month_Year.
            Person was  buried in Month_Year in Place.
            Person was  buried in Place.
            ''

        :returns: A sentence about the subject's burial.
        :rtype: unicode
        """

        text = ""

        bplace = self.__empty_place
        bdate = self.__empty_date
        bdate_full = False
        bdate_mod = False

        burial = None
        for event_ref in self.__person.get_event_ref_list():
            event = self.__db.get_event_from_handle(event_ref.ref)
            if (
                event
                and event.type.value == EventType.BURIAL
                and event_ref.role.value == EventRoleType.PRIMARY
            ):
                burial = event
                break

        if burial:
            if self.__use_fulldate:
                bdate = self.__get_date(burial.get_date_object())
            else:
                bdate = burial.get_date_object().get_year()
            bplace_handle = burial.get_place_handle()
            if bplace_handle:
                place = self.__db.get_place_from_handle(bplace_handle)
                bplace = _pd.display_event(self.__db, burial, fmt=self._place_format)
            bdate_obj = burial.get_date_object()
            bdate_full = bdate_obj and bdate_obj.get_day_valid()
            bdate_mod = bdate_obj and bdate_obj.get_modifier() != Date.MOD_NONE
        else:
            return text

        value_map = {
            "unknown_gender_name": self.__first_name,
            "male_name": self.__first_name,
            "name": self.__first_name,
            "female_name": self.__first_name,
            "burial_date": bdate,
            "burial_place": bplace,
            "month_year": bdate,
            "modified_date": bdate,
            "endnotes": "",
        }

        if bdate and bdate_mod:
            if bplace:  # male, date, place
                text = buried_modified_date_place[self.__format_number]
            else:  # male, date, no place
                text = buried_modified_date_no_place[self.__format_number]
        elif bdate and bdate_full:
            if bplace:  # male, date, place
                text = buried_full_date_place[self.__format_number]
            else:  # male, date, no place
                text = buried_full_date_no_place[self.__format_number]
        elif bdate:
            if bplace:  # male, month_year, place
                text = buried_partial_date_place[self.__format_number]
            else:  # male, month_year, no place
                text = buried_partial_date_no_place[self.__format_number]
        elif bplace:  # male, no date, place
            text = buried_no_date_place[self.__format_number]
        else:  # male, no date, no place
            text = buried_no_date_no_place[self.__format_number]

        if text:
            text = text % value_map

        return text

    def get_baptised_string(self):
        """
        Get a string narrating the baptism of the subject.
        Example sentences:
            Person was baptized on Date.
            Person was baptized on Date in Place.
            Person was baptized in Month_Year.
            Person was baptized in Month_Year in Place.
            Person was baptized in Place.
            ''

        :returns: A sentence about the subject's baptism.
        :rtype: unicode
        """

        text = ""

        bplace = self.__empty_place
        bdate = self.__empty_date
        bdate_full = False
        bdate_mod = False

        baptism = None
        for event_ref in self.__person.get_event_ref_list():
            event = self.__db.get_event_from_handle(event_ref.ref)
            if (
                event
                and event.type.value == EventType.BAPTISM
                and event_ref.role.value == EventRoleType.PRIMARY
            ):
                baptism = event
                break

        if baptism:
            if self.__use_fulldate:
                bdate = self.__get_date(baptism.get_date_object())
            else:
                bdate = baptism.get_date_object().get_year()
            bplace_handle = baptism.get_place_handle()
            if bplace_handle:
                place = self.__db.get_place_from_handle(bplace_handle)
                bplace = _pd.display_event(self.__db, baptism, fmt=self._place_format)
            bdate_obj = baptism.get_date_object()
            bdate_full = bdate_obj and bdate_obj.get_day_valid()
            bdate_mod = bdate_obj and bdate_obj.get_modifier() != Date.MOD_NONE
        else:
            return text

        value_map = {
            "unknown_gender_name": self.__first_name,
            "male_name": self.__first_name,
            "name": self.__first_name,
            "female_name": self.__first_name,
            "baptism_date": bdate,
            "baptism_place": bplace,
            "month_year": bdate,
            "modified_date": bdate,
            "endnotes": "",
        }

        if bdate and bdate_mod:
            if bplace:  # male, date, place
                text = baptised_modified_date_place[self.__format_number]
            else:  # male, date, no place
                text = baptised_modified_date_no_place[self.__format_number]
        elif bdate and bdate_full:
            if bplace:  # male, date, place
                text = baptised_full_date_place[self.__format_number]
            else:  # male, date, no place
                text = baptised_full_date_no_place[self.__format_number]
        elif bdate:
            if bplace:  # male, month_year, place
                text = baptised_partial_date_place[self.__format_number]
            else:  # male, month_year, no place
                text = baptised_partial_date_no_place[self.__format_number]
        elif bplace:  # male, no date, place
            text = baptised_no_date_place[self.__format_number]
        else:  # male, no date, no place
            text = baptised_no_date_no_place[self.__format_number]

        if text:
            text = text % value_map

        return text

    def get_christened_string(self):
        """
        Get a string narrating the christening of the subject.
        Example sentences:
            Person was christened on Date.
            Person was christened on Date in Place.
            Person was christened in Month_Year.
            Person was christened in Month_Year in Place.
            Person was christened in Place.
            ''

        :returns: A sentence about the subject's christening.
        :rtype: unicode
        """

        if not self.__first_name_used:
            name_index = _NAME_INDEX_INCLUDE_NAME
            self.__first_name_used = True
        else:
            name_index = _NAME_INDEX_EXCLUDE_NAME

        gender = self.__person.get_gender()

        text = ""

        cplace = self.__empty_place
        cdate = self.__empty_date
        cdate_full = False
        cdate_mod = False

        christening = None
        for event_ref in self.__person.get_event_ref_list():
            event = self.__db.get_event_from_handle(event_ref.ref)
            if (
                event
                and event.type.value == EventType.CHRISTEN
                and event_ref.role.value == EventRoleType.PRIMARY
            ):
                christening = event
                break

        if christening:
            if self.__use_fulldate:
                cdate = self.__get_date(christening.get_date_object())
            else:
                cdate = christening.get_date_object().get_year()
            cplace_handle = christening.get_place_handle()
            if cplace_handle:
                place = self.__db.get_place_from_handle(cplace_handle)
                cplace = _pd.display_event(
                    self.__db, christening, fmt=self._place_format
                )
            cdate_obj = christening.get_date_object()
            cdate_full = cdate_obj and cdate_obj.get_day_valid()
            cdate_mod = cdate_obj and cdate_obj.get_modifier() != Date.MOD_NONE
        else:
            return text

        value_map = {
            "unknown_gender_name": self.__first_name,
            "male_name": self.__first_name,
            "name": self.__first_name,
            "female_name": self.__first_name,
            "christening_date": cdate,
            "christening_place": cplace,
            "month_year": cdate,
            "modified_date": cdate,
            "endnotes": "",
        }

        if cdate and cdate_mod:
            if cplace:  # male, date, place
                text = christened_modified_date_place[self.__format_number]
            else:  # male, date, no place
                text = christened_modified_date_no_place[self.__format_number]
        elif cdate and cdate_full:
            if cplace:  # male, date, place
                text = christened_full_date_place[self.__format_number]
            else:  # male, date, no place
                text = christened_full_date_no_place[self.__format_number]
        elif cdate:
            if cplace:  # male, month_year, place
                text = christened_partial_date_place[self.__format_number]
            else:  # male, month_year, no place
                text = christened_partial_date_no_place[self.__format_number]
        elif cplace:  # male, no date, place
            text = christened_no_date_place[self.__format_number]
        else:  # male, no date, no place
            text = christened_no_date_no_place[self.__format_number]

        if text:
            text = text % value_map

        return text

    def get_married_string(self, family, is_first=True, name_display=None):
        """
        Get a string narrating the marriage of the subject.
        Example sentences:
            Person was married to Spouse on Date.
            Person was married to Spouse.
            Person was also married to Spouse on Date.
            Person was also married to Spouse.
            ""

        :param family: The family that contains the Spouse for this marriage.
        :type family: :class:`~gen.lib.family,Family`
        :param is_first: Indicates whether this sentence represents the first
            marriage. If it is not the first marriage, the sentence will
            include "also".
        :type is_first: bool
        :param name_display: An object to be used for displaying names
        :type name_display: :class:`~gen.display.name,NameDisplay`
        :returns: A sentence about the subject's marriage.
        :rtype: unicode
        """

        date = self.__empty_date
        place = self.__empty_place

        spouse_name = None
        spouse_handle = utils.find_spouse(self.__person, family)
        if spouse_handle:
            spouse = self.__db.get_person_from_handle(spouse_handle)
            if spouse:
                if not name_display:
                    spouse_name = _nd.display(spouse)
                else:
                    spouse_name = name_display.display(spouse)
        if not spouse_name:
            spouse_name = self.__translate_text("Unknown")  # not: "Unknown"

        event = utils.find_marriage(self.__db, family)
        if event:
            if self.__use_fulldate:
                mdate = self.__get_date(event.get_date_object())
            else:
                mdate = event.get_date_object().get_year()
            if mdate:
                date = mdate
            place_handle = event.get_place_handle()
            if place_handle:
                place_obj = self.__db.get_place_from_handle(place_handle)
                place = _pd.display_event(self.__db, event, fmt=self._place_format)
        relationship = family.get_relationship()

        value_map = {
            "spouse": spouse_name,
            "endnotes": "",
            "full_date": date,
            "modified_date": date,
            "partial_date": date,
            "place": place,
        }

        date_full = 0

        if event:
            dobj = event.get_date_object()

            if dobj.get_modifier() != Date.MOD_NONE:
                date_full = 2
            elif dobj and dobj.get_day_valid():
                date_full = 1

        gender = self.__person.get_gender()

        # This would be much simpler, excepting for translation considerations
        # Currently support FamilyRelType's:
        #     MARRIED     : civil and/or religious
        #     UNMARRIED
        #     CIVIL UNION : described as a relationship
        #     UNKNOWN     : also described as a relationship
        #     CUSTOM      : also described as a relationship
        #
        # In the future, there may be a need to distinguish between
        # CIVIL UNION, UNKNOWN and CUSTOM relationship types
        # CUSTOM will be difficult as user can supply any arbitrary string to
        # describe type

        if is_first:
            if date and place and self.__verbose:
                if relationship == FamilyRelType.MARRIED:
                    text = marriage_first_date_place[self.__format_number][date_full]
                elif relationship == FamilyRelType.UNMARRIED:
                    text = unmarried_first_date_place[self.__format_number][date_full]
                else:
                    text = relationship_first_date_place[self.__format_number][date_full]
            elif date and place:
                if relationship == FamilyRelType.MARRIED:
                    text = marriage_first_date_place[self.__format_number][date_full]
                elif relationship == FamilyRelType.UNMARRIED:
                    text = unmarried_first_date_place[self.__format_number][date_full]
                else:
                    text = relationship_first_date_place[self.__format_number][date_full]
            elif date and self.__verbose:
                if relationship == FamilyRelType.MARRIED:
                    text = marriage_first_date[self.__format_number][date_full]
                elif relationship == FamilyRelType.UNMARRIED:
                    text = unmarried_first_date[self.__format_number][date_full]
                else:
                    text = relationship_first_date[self.__format_number][date_full]
            elif date:
                if relationship == FamilyRelType.MARRIED:
                    text = marriage_first_date[self.__format_number][date_full]
                elif relationship == FamilyRelType.UNMARRIED:
                    text = unmarried_first_date[self.__format_number][date_full]
                else:
                    text = relationship_first_date[self.__format_number][date_full]
            elif place and self.__verbose:
                if relationship == FamilyRelType.MARRIED:
                    text = marriage_first_place[self.__format_number]
                elif relationship == FamilyRelType.UNMARRIED:
                    text = unmarried_first_place[self.__format_number]
                else:
                    text = relationship_first_place[self.__format_number]
            elif place:
                if relationship == FamilyRelType.MARRIED:
                    text = marriage_first_place[self.__format_number]
                elif relationship == FamilyRelType.UNMARRIED:
                    text = unmarried_first_place[self.__format_number]
                else:
                    text = relationship_first_place[self.__format_number]
            elif self.__verbose:
                if relationship == FamilyRelType.MARRIED:
                    text = marriage_first_only[self.__format_number]
                elif relationship == FamilyRelType.UNMARRIED:
                    text = unmarried_first_only[self.__format_number]
                else:
                    text = relationship_first_only[self.__format_number]
            else:
                if relationship == FamilyRelType.MARRIED:
                    text = marriage_first_only[self.__format_number]
                elif relationship == FamilyRelType.UNMARRIED:
                    text = unmarried_first_only[self.__format_number]
                else:
                    text = relationship_first_only[self.__format_number]
        else:
            if date and place and self.__verbose:
                if relationship == FamilyRelType.MARRIED:
                    text = marriage_also_date_place[self.__format_number][date_full]
                elif relationship == FamilyRelType.UNMARRIED:
                    text = unmarried_also_date_place[self.__format_number][date_full]
                else:
                    text = relationship_also_date_place[self.__format_number][date_full]
            elif date and place:
                if relationship == FamilyRelType.MARRIED:
                    text = marriage_also_date_place[self.__format_number][date_full]
                elif relationship == FamilyRelType.UNMARRIED:
                    text = unmarried_also_date_place[self.__format_number][date_full]
                else:
                    text = relationship_also_date_place[self.__format_number][date_full]
            elif date and self.__verbose:
                if relationship == FamilyRelType.MARRIED:
                    text = marriage_also_date[self.__format_number][date_full]
                elif relationship == FamilyRelType.UNMARRIED:
                    text = unmarried_also_date[self.__format_number][date_full]
                else:
                    text = relationship_also_date[self.__format_number][date_full]
            elif date:
                if relationship == FamilyRelType.MARRIED:
                    text = marriage_also_date[self.__format_number][date_full]
                elif relationship == FamilyRelType.UNMARRIED:
                    text = unmarried_also_date[self.__format_number][date_full]
                else:
                    text = relationship_also_date[self.__format_number][date_full]
            elif place and self.__verbose:
                if relationship == FamilyRelType.MARRIED:
                    text = marriage_also_place[self.__format_number]
                elif relationship == FamilyRelType.UNMARRIED:
                    text = unmarried_also_place[self.__format_number]
                else:
                    text = relationship_also_place[self.__format_number]
            elif place:
                if relationship == FamilyRelType.MARRIED:
                    text = marriage_also_place[self.__format_number]
                elif relationship == FamilyRelType.UNMARRIED:
                    text = unmarried_also_place[self.__format_number]
                else:
                    text = relationship_also_place[self.__format_number]
            elif self.__verbose:
                if relationship == FamilyRelType.MARRIED:
                    text = marriage_also_only[self.__format_number]
                elif relationship == FamilyRelType.UNMARRIED:
                    text = unmarried_also_only[self.__format_number]
                else:
                    text = relationship_also_only[self.__format_number]
            else:
                if relationship == FamilyRelType.MARRIED:
                    text = marriage_also_only[self.__format_number]
                elif relationship == FamilyRelType.UNMARRIED:
                    text = unmarried_also_only[self.__format_number]
                else:
                    text = relationship_also_only[self.__format_number]

        if text:
            text = self.__translate_text(text) % value_map
            text = text + " "
        return text

    def get_child_string(self, father_name="", mother_name=""):
        """
        Get a string narrating the relationship to the parents of the subject.
        Missing information will be omitted without loss of readability.
        Example sentences:
            Person was the son of father_name and mother_name.
            Person was the daughter of father_name and mother_name.
            ""

        :param father_name: The name of the Subjects' father.
        :type father_name: unicode
        :param mother_name: The name of the Subjects' mother.
        :type mother_name: unicode
        :returns: A sentence about the subject's parents.
        :rtype: unicode
        """

        value_map = {
            "father": father_name,
            "mother": mother_name,
            "male_name": self.__first_name,
            "name": self.__first_name,
            "female_name": self.__first_name,
            "unknown_gender_name": self.__first_name,
        }

        dead = not probably_alive(self.__person, self.__db)

        if not self.__first_name_used:
            index = _NAME_INDEX_INCLUDE_NAME
            self.__first_name_used = True
        else:
            index = _NAME_INDEX_EXCLUDE_NAME

        gender = self.__person.get_gender()

        text = ""
        if mother_name and father_name and self.__verbose:
            text = child_father_mother[gender][index][dead]
        elif mother_name and father_name:
            text = child_father_mother[gender][2]
        elif mother_name and self.__verbose:
            text = child_mother[gender][index][dead]
        elif mother_name:
            text = child_mother[gender][2]
        elif father_name and self.__verbose:
            text = child_father[gender][index][dead]
        elif father_name:
            text = child_father[gender][2]

        if text:
            text = self.__translate_text(text) % value_map
            text = text + " "

        return text

    def __get_age_at_death(self):
        """
        Calculate the age the person died.

        Returns a tuple representing (age, age_index).
        """
        birth_ref = self.__person.get_birth_ref()
        if birth_ref:
            birth_event = self.__db.get_event_from_handle(birth_ref.ref)
            birth = birth_event.get_date_object()
            birth_year_valid = birth.get_year_valid()
        else:
            birth_year_valid = False
        death_ref = self.__person.get_death_ref()
        if death_ref:
            death_event = self.__db.get_event_from_handle(death_ref.ref)
            death = death_event.get_date_object()
            death_year_valid = death.get_year_valid()
        else:
            death_year_valid = False

        # without at least a year for each event no age can be calculated
        if birth_year_valid and death_year_valid:
            span = death - birth
            if span and span.is_valid():
                if span:
                    age = span.get_repr(dlocale=self._locale)
                    age_index = _AGE_INDEX
                else:
                    age = 0
                    age_index = _AGE_INDEX_NO_AGE
            else:
                age = 0
                age_index = _AGE_INDEX_NO_AGE
        else:
            age = 0
            age_index = _AGE_INDEX_NO_AGE

        return age, age_index
