import codecs
import math
import os
import re
import subprocess  # for Latexindent Formatter
from typing import Dict, List

from gramps.gen.const import HOME_DIR
from gramps.gen.display.place import displayer as _pd
from gramps.gen.lib import Date, EventRoleType, EventType, Person
from gramps.gen.utils.file import media_path_full
from gramps.plugins.docgen.latexdoc import latexescape


def format_nobiliary_particle(surname: str):
    """Formats the surname if it has nobiliary particles (e.g., von)

    Args:
        surname (str): The complete surname incl. nobiliary particles

    Returns:
        (tuple[str, str] | tuple[str, None]): A string tuple containing the pure surname and the nobiliary particle
    """

    nobiliary_particles = [
        "von ",
        "van ",
        "vom ",
        "zu ",
        "de ",
        "d'",
        "del ",
        "di ",
        "da ",
        "dos ",
        "des ",
        "du ",
        "la ",
        "le ",
        "lo ",
        "della ",
        "delle ",
        "degli ",
        "dei ",
        "el ",
        "al ",
        "de la ",
        "de las ",
        "de los ",
    ]

    try:
        for particle in nobiliary_particles:
            if particle in surname.lower():
                parts = surname.split(particle, 1)
                family_name = parts[1].strip()
                return family_name, particle

        return (
            surname,
            None,
        )  # If no preposition is found, return the original surname
    except Exception:
        pass

    return surname, None


def create_latex_index_entry(
    opening: bool, surname: str, alias: str, given: str, formatted_given: str
):
    """Returns a string list of LaTeX index entries

    Args:
        opening (bool): Indicates if this is the opening or closing index entry
        surname (str): The person's complete surname
        alias (str): The person's alias
        given (str): The person's given name(s)
        formatted_given (str): A LaTeX-formatted version of given names as it should appear in the index

    Returns:
        List(str): A string list of index entries
    """

    latex_index_entries = []

    # Format surname with nobility preposition
    stripped_surname, nobility_particle = format_nobiliary_particle(surname)
    formatted_surname = f"{stripped_surname}, {nobility_particle}"
    nobility_particle_formatted = (
        (" " + nobility_particle.strip()) if nobility_particle else ""
    )
    open_close = "|(" if opening else "|)"
    # First index entry: "Formatted Surname, Preposition, Given Name"
    entry_formatted_surname = (
        "\\index[ind]{"
        + stripped_surname
        + "!"
        + given
        + nobility_particle_formatted
        + "@"
        + formatted_given
        + nobility_particle_formatted
        + open_close
        + "}"
    )
    latex_index_entries.append(entry_formatted_surname)

    # Second index entry: "Unformatted Surname --> See Formatted Surname, Preposition"
    if opening and nobility_particle:
        entry_unformatted_surname = (
            "\\index[ind]{" + surname + "|see{" + stripped_surname + "}}"
        )
        latex_index_entries.append(entry_unformatted_surname)

    # Additional index entry if alias is present
    if opening and alias != "":
        entry_alias_given = (
            "\\index[ind]{"
            + alias
            + ", "
            + given
            + "|see{"
            + stripped_surname
            + ", "
            + given
            + nobility_particle_formatted
            + "}}"
        )
        latex_index_entries.append(entry_alias_given)

    return latex_index_entries


def format_with_latexindent(filename: str) -> None:
    """Formats the given file with latexindent, overwriting the original

    Args:
        filename (str): Full path and filename of the file to be formatted

    Raises:
        FileNotFoundError: If the specified file is not found
    """
    try:
        # Check if latexindent is on the system path
        subprocess.run(["latexindent", "--version"], capture_output=True, check=True)

        # Check if the file exists
        if not os.path.exists(filename):
            raise FileNotFoundError("File not found: " + filename)

        # Run latexindent to format the file contents and overwrite the file
        subprocess.run(
            ["latexindent", "-w", "-s", "-y", "-o", filename, filename],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # the format_with_latexindent method uses subprocess.run with the stdout and stderr arguments set to subprocess.DEVNULL, which redirects the output to null and suppresses any console output.
        # Additionally, the -s option is added to silence any progress indicator, and the -y option is added to assume "yes" to all questions, avoiding any prompts during formatting

    except subprocess.CalledProcessError:
        print("Error occurred while running latexindent.")
    except FileNotFoundError:
        print(
            "latexindent not found on the system path. Please make sure it is installed."
        )


def get_latex_biography(person: List[str], order_system: str, gramps_id: bool) -> str:
    """Returns a complete LaTeX-formatted biography of 'person'

    Args:
        person (List[str]): A string list containing all biographical facts
        order_system (str): Either 'henry' for downward reports or 'kekule'
        gramps_id (bool): If visible Gramps-IDs should be part of the biography

    Returns:
        str: formatted biography of person
    """
    # Write biography (if this is not a duplicate)
    biography = ""
    # Write Reference ID if not filtered:
    if not person["filtered"]:
        biography += "\\label{" + person["ID"] + "}"
    else:
        biography += "\\filteredperson{"
    # Write Sosa-Stradonitz Numbering
    biography += "\\" + order_system + "{" + person["kekule"] + "}"
    # Reset place ("ebenda")
    biography += "\\resetplace "
    # Show GrampsID
    if gramps_id:
        biography += "\\GrID{" + person["GrID"] + "}"
    biography += person["tags"]
    # Write name
    if person["titel"] != "":
        biography += "\\titel{" + person["titel"] + "} "
    if person["nachname"] != "":
        biography += "\\nachname{" + person["nachname"] + "} "
    alias = person["alias"]
    if alias != "":
        alias = "(alias " + alias + ")"
        biography += "\\alias{" + alias + "} "
    if person["suffix"] != "":
        biography += "\\suffix{" + person["suffix"] + "} "
    biography = biography.strip()
    biography += ", "

    # Vornamen, incl. Rufname und Spitzname
    name_parts = person["vornamen"].split()
    name_string = " ".join(name_parts)

    if person["rufname"] and person["rufname"] in name_parts:
        if name_parts[0] != person["rufname"]:
            name_string = name_string.replace(
                person["rufname"], f"\\rufname{{{person['rufname']}}}"
            )

    if person["spitzname"]:
        name_string += f" \\spitzname{{{person['spitzname']}}}"

    biography += "\\vornamen{" + name_string.strip() + "}"

    if person["filtered"]:
        latex_id = person["ID"]
        filter_name = person[
            "filtered"
        ]  # If filter is present, this entry hold the filter name
        biography += f"\\filteredpersonref{{{latex_id}}}{{{filter_name}}}"
        biography += "}"  # This closes the \filteredperson{ tag that the entire entry is wrapped in.
        biography += " " + "\n\n"
    else:
        biography += ", "

        # Write opening Index-entry (with cross reference when an alias name is present)
        biography += "".join(
            create_latex_index_entry(
                True,
                (person["nachname"] + " " + person["suffix"]).strip(),
                person["alias"],
                person["vornamen"],
                name_string,
            )
        )

        # Write CV-Data
        if person["beruf"] != "":
            biography += "\\beruf{" + person["beruf"] + "}, "
        if person["geboren"] != "":
            biography += person["geboren"] + " "
        if person["abstammung"] != "":
            biography += person["abstammung"] + ", "
        if person["getauft"] != "":
            biography += person["getauft"] + " "
        if person["gestorben"] != "":
            biography += person["gestorben"] + " "
        if person["begraben"] != "":
            biography += person["begraben"] + " "
        if biography.strip()[-1] == ",":
            biography = biography.strip()[:-1]
        biography += ". "

        # Include trees
        if person["trees"] != "":
            # visual cure: use \rightpitchfork for up-trees and \letftpitchfork for down
            biography += " " + person["treelinks"]
            biography += "\n" + person["trees"] + " \n"
        # Include picture
        if person["picture"] != "":
            biography += "\n " + person["picture"] + " \n "
        # Include notes
        if person["notitzen"] != "":
            biography += "\par \n " + person["notitzen"] + " " + "\\\\\n\n"
        # Reset place ("ebenda")
        biography += "\\resetplace "
        # Write partnerships
        hochzeiten = person["hochzeiten"]
        if hochzeiten != "":
            if not person["notitzen"]:
                biography += " " + "\n\n"
            biography += hochzeiten + " " + "\n\n"
        # Write closing Index-entry
        biography += "".join(
            create_latex_index_entry(
                False,
                (person["nachname"] + " " + person["suffix"]).strip(),
                person["alias"],
                person["vornamen"],
                name_string,
            )
        )
        # Insert newline if necessary
        if hochzeiten == "" and person["notitzen"] == "":
            biography += " " + "\n\n"

    # Collect in Output string
    biography = biography.replace("  ", " ")
    biography = re.sub(r"\. \.", ". ", biography, 0, re.MULTILINE)  # replace ". ."
    biography = re.sub(r",\.", ".", biography, 0, re.MULTILINE)  # replace ",."
    biography = re.sub(r" {2,}", " ", biography, 0, re.MULTILINE)  # double space
    biography = re.sub(
        r" +([,\.])([^\.])", r"\1\2", biography, 0, re.MULTILINE
    )  # spaces
    biography = re.sub(r"\.{2}", r".", biography, 0, re.MULTILINE)  # double .
    biography = re.sub(
        r"([0-9]+)\.([0-9]+)\.([\d]{4})",
        r"\\DTMdisplaydate{\3}{\2}{\1}{-1}",
        biography,
    )  # formats dates for Latex' DateTime2
    biography += "\n\n"
    return biography


def format_note(note: str) -> str:
    """Format the given note text to prepare it for inclusion in a LaTeX document

    Args:
        note (str): The note text to be formatted

    Returns:
        str: The note's text, ready for inclusion in a LaTeX document
    """

    return_string = ""
    text = str(note)

    # https://regex101.com/
    text = re.sub(r" \.", ".", text)  # remove space before dot
    text = re.sub("„", '"', text)  # lower typog. quote
    text = re.sub("“", '"', text)  # upper typog. quote
    text = re.sub("”", '"', text)  # upper typog. quote
    text = re.sub("–", "--", text)  # replace a long hyphen by two normal hyphens
    text = re.sub("—", "--", text)  # long hyphens—
    text = re.sub(
        r"([zdosuv])\.[ ]?([BhÄJäouZaAUT])\.", r"\1.\\,\2.", text
    )  # correctly displaying the two-letter abbreviations
    text = transform_abbreviations(
        text
    )  # transform abbreviations according to The Economist style guide
    # TODO #[...] / ... --> \textelp{}
    text = re.sub(r"([ (_@])\'(.+?)\'([ \".?!_@)])", r"\1|\2|\3", text)  # single quotes
    text = re.sub(
        r"([ (_@])‚(.+?)‘([ \".?!_@)])", r"\1|\2|\3", text
    )  # single typograph quotes quotes
    text = re.sub(
        r"([0-9]{2})([0-9]{2}) ??-+? ??([0-9]{2})([^0-9]+)",
        r"\1\2--\1\3\4",
        text,
    )  # 1941-42 --> 1941--1942
    text = re.sub(r"(?P<digit>\d),5", r"\g<digit>1/2", text)  # ,5 -> 1/2
    text = re.sub(r"(?P<digit>\d),25", r"\g<digit>1/4", text)  # ,25 -> 1/4
    text = re.sub(r"[1]/([234])([^0-9])", r"\\nicefrac{1}{\1}\2", text)  # make fraction
    text = re.sub(r" {2,}", " ", text)  # double space
    text = re.sub(r" {1,}([.,?!])", r"\1", text)  # spaces before punctuation marks
    text = re.sub(r"\(= (.*?)\)", r"(=~\1)", text)  # protected space after "="
    text = re.sub(" - ", " -- ", text)  # long hyphens
    text = re.sub(r"(\d) [-–] (\d)", r"\1--\2", text)  # 2000 - 2001 --> 2000--2001
    text = re.sub(r"(\d)[-–](\d)", r"\1--\2", text)  # 2000-2001 --> 2000--2001
    text = re.sub(r"(\d) -- (\d)", r"\1--\2", text)  # 2000 -- 2001 --> 2000--2001
    # format dates:
    text = re.sub(
        r"([0-9]+)\.([0-9]+)\.([\d]{4})",
        r"\\DTMdisplaydate{\3}{\2}{\1}{-1}",
        text,
    )  # formats dates for Latex' DateTime2
    # compile markups:
    text = re.sub(
        r"\_(.*?)\_", r"\\footnote{\1}", text, flags=re.DOTALL
    )  # _.._ will be treated as footnote
    text = re.sub(
        r"\#(.*?)\#", r"\\unterabsatz{\1}", text
    )  # #..# will be treated as subsubheading
    text = re.sub(
        r"\*(.*?)\*", r"\\textit{\1}", text, flags=re.DOTALL
    )  # *..* italics (as in Markdown)
    text = re.sub(
        r"\^\(--> (.*?)\)", r"\\index{\1}", text
    )  # Index entries in the format: ^(--> <ENTRY>)

    text = re.sub(r"\"(.*?)\"", r"\\enquote{\1}", text)  # \enquote
    text = re.sub(r"\"(.*?)\"", r"\\zitat{\1}", text, flags=re.DOTALL)  # \zitat

    # text = re.sub(r"[\r\n]+", "\\r\\n", text, 0, re.MULTILINE)  # delete emtpy lines

    text = re.sub(r" &", "\\,\\&", text)  # Escape the Ampersand sign
    text = re.sub(r"%", "\\%", text)  # Escape the percent sign

    # text = latexescape(text)

    return_string += text
    return return_string


def transform_abbreviations(text: str) -> str:
    """Transform abbreviations to LaTeX complying with the ECONOMIST style guide.

    Args:
        text (str): the text to transform

    Returns:
        str: the transformed text
    """

    words = re.split("(\W)", text)
    processed_words = []

    for word in words:
        capital_letter_count = sum(1 for letter in word if letter.isupper())
        if capital_letter_count >= 2 or capital_letter_count == len(word):
            processed_word = re.sub(
                r"([A-ZÄÖÜ]+)",
                lambda match: f"\\textsc{{{match.group(0).lower()}}}",
                word,
            )
        else:
            processed_word = word
        processed_words.append(processed_word)

    return "".join(processed_words)


def get_latex_id(person: Person) -> str:
    """Returns a valid, human-readable person ID for use in LaTeX

    Args:
        person (Person): A Person object

    Returns:
        str: The person's ID bases on name and GrampsID
    """
    person_id = ""
    person_id = (
        get_nachname(person)
        + person.primary_name.first_name
        + person.primary_name.suffix
        + str(person.get_gramps_id())
    )
    person_id = person_id.replace(" ", "")
    umlaute = {
        "ö": "oe",
        "ä": "ae",
        "ü": "ue",
        "Ä": "AE",
        "Ö": "OE",
        "Ü": "UE",
        "ß": "ss",
        "æ": "ae",
    }
    for char in umlaute:
        person_id = person_id.replace(char, umlaute[char])
    return person_id


def get_nachname(person: Person) -> str:
    """Returns the first valid surname of a person

    Args:
        person (Person): A Person object

    Returns:
        str: A string containing the first surname of person
    """
    nachname = ""
    nachnamen = person.primary_name.surname_list
    if len(nachnamen) > 0:
        nachname = nachnamen[0].surname
    return nachname


def get_empty_indiviudal() -> Dict:
    """Returns a dict with all the relevant keys but empty values

    Returns:
        Dict: Dict to describe a person
    """

    individual = {
        "ID": "",
        "GrID": "",
        "kekule": "",
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
        "hochzeiten": "",
        "notitzen": "",
        "beruf": "",
        "abstammung": "",
        "tags": "",
        "treelinks": "",
        "trees": "",
        "filtered": False,
        "partner": None,
    }
    return individual


def color_is_dark(html_color: str) -> bool:
    """Determines if a color is dark or light

    Args:
        html_color (str): The HTML Color Code to check, provide without leading #

    Returns:
        bool: True if the color is dark, False if it is light
    """
    [r, g, b] = (int(html_color[i : i + 2], 16) for i in (0, 2, 4))
    hsp = math.sqrt(0.299 * (r * r) + 0.587 * (g * g) + 0.114 * (b * b))
    if hsp > 127.5:
        return False
    else:
        return True


def tree_create(definition: str, db, person: Person, dir: str) -> str:
    tree_type, *generations = definition.split(",")
    if not generations:
        generations = [3, 2]  # set a default value
    tex = []
    tree_type = tree_type.lower().strip()
    if tree_type == "up" or tree_type.startswith("asc"):
        family_handles = person.get_main_parents_family_handle()
        if family_handles:
            tree_write_subgraph_anc(
                db, 0, "parent", family_handles, person.handle, int(generations[0]), tex
            )
    elif tree_type == "down" or tree_type.startswith("desc"):
        family_handles = person.get_family_handle_list()
        if len(family_handles) > 0:
            tree_write_subgraph_desc(
                db, 0, "child", family_handles, person.handle, int(generations[0]), tex
            )
    elif tree_type.startswith("sand"):
        family_report = "fam" in tree_type  # default would then be family = false
        nosiblings = ["no-sib", "wo-sib", "nosib", "wosib", "without-sib", "withoutsib"]
        siblings = "sib" in tree_type and not any(
            s in tree_type for s in nosiblings
        )  # defaults to siblings = false
        up = int(generations[0])
        down = int(generations[1])

        if not family_report:
            family_handle = person.get_main_parents_family_handle()
            if family_handle:
                tree_sand_subgraph_up(
                    db,
                    0,
                    "sandclock",
                    family_handle,
                    person.handle,
                    up,
                    down,
                    family_report,
                    siblings,
                    tex,
                )
        else:
            family_handles = person.get_family_handle_list()
            if len(family_handles) > 0:
                # This makes a sandclock graph only for the first family!!!
                family = db.get_family_from_handle(family_handles[0])
                tree_start_subgraph(0, "sandclock", family, tex)
                tree_sand_subgraph_up_parents(
                    db, 0, family, up, down, family_report, siblings, tex
                )
                for childref in family.get_child_ref_list():
                    child = db.get_person_from_handle(childref.ref)
                    family_handles = child.get_family_handle_list()
                    if len(family_handles) > 0:
                        tree_sand_subgraph_down(
                            db,
                            1,
                            "child",
                            family_handles,
                            child.handle,
                            down,
                            family_report,
                            siblings,
                            tex,
                        )
                    else:
                        tree_write_node(db, 1, "c", child, False, tex)
                tree_write(0, "}\n", tex)
    else:
        return ""  # not a valid definition
    # end tree
    # tree_write(0, "}\n", tex) # produces one } too many...
    tree_write(0, "\n", tex)

    # save to .graph file
    filename = get_filename(person, "tree", definition, "graph", dir, "trees")
    directory = os.path.dirname(filename)
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    f = codecs.open(filename, "w+", encoding="utf-8")
    for i in range(len(tex)):
        f.write(tex[i])
    f.close()
    return filename  # returns absolute path of .graph file


def tree_sand_subgraph_up_parents(
    db, level, family, max_up, max_down, fam_report, siblings, tex
):
    for handle in (family.get_father_handle(), family.get_mother_handle()):
        if handle:
            parent = db.get_person_from_handle(handle)
            family_handle = parent.get_main_parents_family_handle()
            if family_handle and level < max_up:
                tree_sand_subgraph_up(
                    db,
                    level + 1,
                    "parent",
                    family_handle,
                    handle,
                    max_up,
                    max_down,
                    fam_report,
                    siblings,
                    tex,
                )
            else:
                tree_write_node(db, level + 1, "p", parent, True, tex)


def tree_sand_subgraph_up(
    db,
    level,
    subgraph_type,
    family_handle,
    ghandle,
    max_up,
    max_down,
    fam_report,
    siblings,
    tex,
):
    if level > max_up:
        return
    family = db.get_family_from_handle(family_handle)
    tree_start_subgraph(level, subgraph_type, family, tex)
    tree_sand_subgraph_up_parents(
        db, level, family, max_up, max_down, fam_report, siblings, tex
    )
    for childref in family.get_child_ref_list():
        child = db.get_person_from_handle(childref.ref)
        if childref.ref == ghandle:
            if subgraph_type != "sandclock":
                tree_write_node(db, level + 1, "g", child, True, tex)
        elif siblings:
            tree_write_node(db, level + 1, "c", child, False, tex)

    if fam_report and subgraph_type == "sandclock":
        person = db.get_person_from_handle(ghandle)
        family_handles = person.get_family_handle_list()
        if len(family_handles) > 0:
            tree_sand_subgraph_down(
                db,
                0,
                "child",
                family_handles,
                person.handle,
                max_down,
                fam_report,
                siblings,
                tex,
            )

    tree_write(level, "}\n", tex)


def tree_sand_subgraph_down(
    db,
    level,
    subgraph_type,
    family_handles,
    ghandle,
    max_down,
    fam_report,
    siblings,
    tex,
):
    if level >= max_down:
        return
    family = db.get_family_from_handle(family_handles[0])
    tree_start_subgraph(level, subgraph_type, family, tex)
    for handle in family_handles[1:]:
        tree_sand_subgraph_down(
            db,
            level + 1,
            "union",
            [handle],
            ghandle,
            max_down,
            fam_report,
            siblings,
            tex,
        )
    for handle in (family.get_father_handle(), family.get_mother_handle()):
        if handle:
            parent = db.get_person_from_handle(handle)
            if handle == ghandle:
                if subgraph_type == "child":
                    tree_write_node(db, level + 1, "g", parent, False, tex)
            else:
                tree_write_node(db, level + 1, "p", parent, True, tex)
    for childref in family.get_child_ref_list():
        child = db.get_person_from_handle(childref.ref)
        family_handles = child.get_family_handle_list()
        if len(family_handles) > 0:
            if level + 1 >= max_down:
                tree_write_node(db, level + 1, "c", child, True, tex)
            else:
                tree_sand_subgraph_down(
                    db,
                    level + 1,
                    "child",
                    family_handles,
                    childref.ref,
                    max_down,
                    fam_report,
                    siblings,
                    tex,
                )
        else:
            tree_write_node(db, level + 1, "c", child, True, tex)
    tree_write(level, "}\n", tex)


def tree_write_subgraph_desc(
    db,
    level: int,
    subgraph_type: str,
    family_handles,
    ghandle,
    max_generations: int,
    tex: List[str],
):
    """Writes a descending subgraph for a specified family handle to the tex argument

    Args:
        db (_type_): The Gramps data base
        level (int): level to write
        subgraph_type (str): Subgraph type: union, child, p
        family_handles (_type_): The family handle for the subgraph
        ghandle (_type_): The center person
        max_generations (int): The max number of generations to include
        tex (List[str]): Where the graph output should be collected
    """
    if level >= max_generations:
        return
    family = db.get_family_from_handle(family_handles[0])
    tree_start_subgraph(level, subgraph_type, family, tex)
    for handle in family_handles[1:]:
        tree_write_subgraph_desc(
            db, level + 1, "union", [handle], ghandle, max_generations, tex
        )
    for handle in (family.get_father_handle(), family.get_mother_handle()):
        if handle:
            parent = db.get_person_from_handle(handle)
            if handle == ghandle:
                if subgraph_type == "child":
                    tree_write_node(db, level + 1, "g", parent, False, tex)
            else:
                tree_write_node(db, level + 1, "p", parent, True, tex)
    for childref in family.get_child_ref_list():
        child = db.get_person_from_handle(childref.ref)
        family_handles = child.get_family_handle_list()
        if len(family_handles) > 0:
            family_handles = child.get_family_handle_list()
            if level + 1 >= max_generations:
                tree_write_node(db, level + 1, "c", child, True, tex)
            else:
                tree_write_subgraph_desc(
                    db,
                    level + 1,
                    "child",
                    family_handles,
                    childref.ref,
                    max_generations,
                    tex,
                )
        else:
            tree_write_node(db, level + 1, "c", child, True, tex)
    # end subgraph (level)
    tree_write(level, "}\n", tex)


def tree_write_subgraph_anc(
    db, level, subgraph_type, family_handle, ghandle, max_generations, tex
):
    """Writes an ascending subgraph for a specified family handle to the tex argument

    Args:
        db (_type_): The Gramps data base
        level (int): level to write
        subgraph_type (str): Subgraph type: union, child, p
        family_handles (_type_): The family handle for the subgraph
        ghandle (_type_): The center person
        max_generations (int): The max number of generations to include
        tex (List[str]): Where the graph output should be collected
    """
    if level > max_generations:
        return
    family = db.get_family_from_handle(family_handle)
    tree_start_subgraph(level, subgraph_type, family, tex)
    for handle in (family.get_father_handle(), family.get_mother_handle()):
        if handle:
            parent = db.get_person_from_handle(handle)
            family_handle = parent.get_main_parents_family_handle()
            if family_handle:
                tree_write_subgraph_anc(
                    db, level + 1, "parent", family_handle, handle, max_generations, tex
                )
            else:
                tree_write_node(db, level + 1, "p", parent, True, tex)
    for childref in family.get_child_ref_list():
        child = db.get_person_from_handle(childref.ref)
        if childref.ref == ghandle:
            tree_write_node(db, level + 1, "g", child, True, tex)
        else:
            tree_write_node(db, level + 1, "c", child, False, tex)
    tree_write(level, "}\n", tex)


def tree_start_subgraph(level, subgraph_type, family, tex, option_list=None):
    options = ["id=%s" % family.gramps_id]
    if option_list:
        options.extend(option_list)
    tree_write(level, "%s[%s]{\n" % (subgraph_type, ",".join(options)), tex)


def tree_write(level, text, tex):
    """
    Write indented text.
    """
    tex.append("  " * level + text)


def tree_write_node(db, level, node_type, person, marriage_flag, tex, option_list=None):
    options = ["id=%s" % person.gramps_id]
    if option_list:
        options.extend(option_list)
    tree_write(level, "%s[%s]{\n" % (node_type, ",".join(options)), tex)
    if person.gender == Person.MALE:
        tree_write(level + 1, "male,\n", tex)
    elif person.gender == Person.FEMALE:
        tree_write(level + 1, "female,\n", tex)
    elif person.gender == Person.UNKNOWN:
        tree_write(level + 1, "neuter,\n", tex)
    name = person.get_primary_name()
    nick = name.get_nick_name()
    surn = name.get_surname()

    name_parts = [
        tree_format_given(name),
        "\\nick{{{}}}".format(escape(nick)) if nick else "",
        "\\surn{{{}}}".format(escape(surn)) if surn else "",
    ]
    name_komplett = "{{{}}}".format(" ".join([e for e in name_parts if e]))
    hyperref = get_latex_id(person)
    hyperref = "{\\hyperref[%s]{%s}" % (hyperref, name_komplett)
    hyperref += "\\seitenzahl{" + get_latex_id(person) + "}},\n"
    tree_write(level + 1, "name = %s" % hyperref, tex)

    for eventref in person.get_event_ref_list():
        if eventref.role == EventRoleType.PRIMARY:
            event = db.get_event_from_handle(eventref.ref)
            tree_write_event(db, level + 1, event, tex)
    if marriage_flag:
        for handle in person.get_family_handle_list():
            family = db.get_family_from_handle(handle)
            for eventref in family.get_event_ref_list():
                if eventref.role == EventRoleType.FAMILY:
                    event = db.get_event_from_handle(eventref.ref)
                    tree_write_event(db, level + 1, event, tex)
    for attr in person.get_attribute_list():
        # Comparison with 'Occupation' for backwards compatibility with Gramps 5.0
        attr_type = str(attr.get_type())
        if attr_type in ("Occupation", ("Occupation")):
            tree_write(
                level + 1, "profession = {%s},\n" % escape(attr.get_value()), tex
            )
        if attr_type == "Comment":
            tree_write(level + 1, "comment = {%s},\n" % escape(attr.get_value()), tex)
    # For images:
    # for mediaref in person.get_media_list():
    #     media = db.get_media_from_handle(mediaref.ref)
    #     path = media_path_full(db, media.get_path())
    #     if os.path.isfile(path):
    #         if win():
    #             path = path.replace("\\", "/")
    #         self.write(level + 1, "image = {{%s}%s},\n" % os.path.splitext(path),tex)
    #         break  # first image only
    tree_write(level, "}\n", tex)


def tree_write_event(db, level, event, tex):
    """
    Write an event.
    """
    modifier = None
    if event.type == EventType.BIRTH:
        event_type = "birth"
        if "died" in event.description.lower():
            modifier = "died"
        if "stillborn" in event.description.lower():
            modifier = "stillborn"
        # modifier = 'out of wedlock'
    elif event.type == EventType.BAPTISM:
        event_type = "baptism"
    elif event.type == EventType.ENGAGEMENT:
        event_type = "engagement"
    elif event.type == EventType.MARRIAGE:
        event_type = "marriage"
    elif event.type == EventType.DIVORCE:
        event_type = "divorce"
    elif event.type == EventType.DEATH:
        event_type = "death"
    elif event.type == EventType.BURIAL:
        event_type = "burial"
        if "killed" in event.description.lower():
            modifier = "killed"
    elif event.type == EventType.CREMATION:
        event_type = "burial"
        modifier = "cremated"
    # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
    elif event.type == EventType.OCCUPATION:
        # Sosa Stradonitz fehlt auch noch: kekule = 100 //ohne Klammern!
        # LatexID --> UUID
        event_type = "profession"
    # ---------------------------------------------------------------------------------------------------
    else:
        return

    date = event.get_date_object()

    if date.get_calendar() == Date.CAL_GREGORIAN:
        calendar = "AD"  # GR
    elif date.get_calendar() == Date.CAL_JULIAN:
        calendar = "JU"
    else:
        calendar = ""

    if date.get_modifier() == Date.MOD_ABOUT:
        calendar = "ca" + calendar

    date_str = format_iso(date.get_ymd(), calendar)
    if date.get_modifier() == Date.MOD_BEFORE:
        date_str = "/" + date_str
    elif date.get_modifier() == Date.MOD_AFTER:
        date_str = date_str + "/"
    elif date.is_compound():
        stop_date = format_iso(date.get_stop_ymd(), calendar)
        date_str = date_str + "/" + stop_date

    place = escape(_pd.display_event(db, event))
    place = place.replace("-", "\--")

    # ADDED FOR Q-LATEX OUTPUT--------------------------------------------------------------------------
    place = ""
    if event_type == "profession":
        beruf = escape(event.get_description())
        tree_write(level, "%s = {%s},\n" % (event_type, beruf), tex)
    # if modifier:
    elif modifier:
        # ---------------------------------------------------------------------------------------------------
        event_type += "+"
        tree_write(
            level, "%s = {%s}{%s}{%s},\n" % (event_type, date_str, place, modifier), tex
        )
    elif place == "":
        event_type += "-"
        tree_write(level, "%s = {%s},\n" % (event_type, date_str), tex)
    else:
        tree_write(level, "%s = {%s}{%s},\n" % (event_type, date_str, place), tex)


def tree_format_given(name):
    """
    Format given names.
    """
    first = name.get_first_name()
    call = name.get_call_name()
    if call:
        if call in first:
            where = first.index(call)
            return "{before}\\pref{{{call}}}{after}".format(
                before=escape(first[:where]),
                call=escape(call),
                after=escape(first[where + len(call) :]),
            )
        else:
            # ignore erroneous call name
            return escape(first)
    else:
        return escape(first)


def escape(text):
    lookup = {
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
        "~": "\\~{}",
        "^": "\\^{}",
        "\\": "\\textbackslash{}",
    }
    pattern = re.compile("|".join([re.escape(key) for key in lookup.keys()]))
    return pattern.sub(lambda match: lookup[match.group(0)], text)


def format_iso(date_tuple, calendar):
    """
    Format an iso date.
    """
    year, month, day = date_tuple
    if year == 0:
        iso_date = ""
    elif month == 0:
        iso_date = str(year)
    elif day == 0:
        iso_date = "%s-%s" % (year, month)
    else:
        iso_date = "%s-%s-%s" % (year, month, day)
    if calendar and calendar != "AD":
        iso_date = "(%s)%s" % (calendar, iso_date)
    return iso_date


def get_filename(
    person: Person, prefix: str, suffix: str, extension: str, dir: str, subfolder: str
) -> str:
    filename = ""
    if prefix:
        filename += normalize_string(prefix) + "-"
    filename += (
        normalize_string(get_nachname(person) + "-" + person.primary_name.first_name)
        + "-"
        + str(person.get_gramps_id())
    )
    if suffix:
        filename += "-" + normalize_string(suffix)
    if extension:
        filename += "." + extension
    if not dir:
        dir = HOME_DIR
    filename_abs = os.path.normpath(
        os.path.normcase(os.path.join(dir, subfolder, filename))
    )
    return filename_abs


def normalize_string(text):
    output = re.sub(r"[\\/: \_!\?.%öäüÄÖÜß#,\(\)|]*", r"", text)
    return output


def write_output_to_file(filename, output):
    f = codecs.open(filename, "w+", encoding="utf-8")
    # write intro for using this file as a subfile in latex
    f.write(
        """\\documentclass[00-Maindoc]{subfiles}\n	
        \\begin{document}\n\n	
        """
    )
    for i in range(len(output) - 1):
        i = i + 1
        f.write(output[i])
    # write outro
    f.write("\n\\end{document}")
    f.close()


def write_parents(db, person, person_data):
    """write out the main parents of a person"""
    geschlecht = person.get_gender()  # Person.MALE / Person.FEMALE / Person.UNKNOWN
    if geschlecht == Person.MALE:
        geschlecht_text = "Sohn"
    elif geschlecht == Person.FEMALE:
        geschlecht_text = "Tochter"
    else:
        geschlecht_text = "Kind"
    family_handle = person.get_main_parents_family_handle()
    if family_handle:
        family = db.get_family_from_handle(family_handle)
        mother_handle = family.get_mother_handle()
        father_handle = family.get_father_handle()
        if mother_handle:
            mother = db.get_person_from_handle(mother_handle)
            mother_name = mother.primary_name.first_name + " "
            mother_spitzname = mother.primary_name.nick
            if mother_spitzname:
                mother_name += "\\spitzname{" + mother_spitzname + "} "
            mother_name += get_nachname(mother)
            mother_name = mother_name.strip()
            mother_id = get_latex_id(mother)
        else:
            mother_name = ""
            mother_id = ""

        if father_handle:
            father = db.get_person_from_handle(father_handle)
            father_name = father.primary_name.first_name + " "
            father_spitzname = father.primary_name.nick
            if father_spitzname:
                father_name += "\\spitzname{" + father_spitzname + "} "
            father_name += get_nachname(father)
            father_name = father_name.strip()
            father_id = get_latex_id(father)
        else:
            father_name = ""
            father_id = ""

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
        person_data["abstammung"] = eltern_text


def write_marriage(db, narrator, name_display, person, person_data):
    """
    Output marriage sentence.
    """
    is_first = True
    hochzeit_nr = 0
    anzahl_hochzeiten = len(person.get_family_handle_list())
    for family_handle in person.get_family_handle_list():
        family = db.get_family_from_handle(family_handle)
        
        spouse_handle = None
        if family:
            if person.get_handle() == family.get_father_handle():
                spouse_handle = family.get_mother_handle()
            else:
                spouse_handle = family.get_father_handle()
        
        spouse = ""
        if spouse_handle:
            spouse = db.get_person_from_handle(spouse_handle)

        text = narrator.get_married_string(family, is_first, name_display)
        if text:
            text = transform_abbreviations(text)
            hochzeit_nr += 1
            if anzahl_hochzeiten > 1:
                text = "\\circled{" + str(hochzeit_nr) + "}\\," + text

            kinder_text = ""
            kinder = family.get_child_ref_list()
            if len(kinder) > 0:
                count = 1
                for kind_ref in kinder:
                    child_handle = kind_ref.ref
                    kind = db.get_person_from_handle(child_handle)
                    kind_vorname = kind.primary_name.first_name
                    kind_spitzname = kind.primary_name.nick
                    kinder_text += "\\hyperref[" + get_latex_id(kind) + "]{"
                    if len(kinder) > 1:
                        kinder_text += "(" + str(count) + ")~"
                    kinder_text += kind_vorname
                    if kind_spitzname:
                        kinder_text += " \\spitzname{" + kind_spitzname + "}"
                    kinder_text += "}\seitenzahl{" + get_latex_id(kind) + "}"
                    if count < len(kinder):
                        kinder_text += ", "
                    if count == len(kinder):
                        kinder_text += ". "
                    count += 1
            if kinder_text:
                if not spouse:
                    text += " Kinder: " + kinder_text
                elif person_data["partner"] != spouse:
                    text += " Kinder: " + kinder_text
                else:
                    text += " (Kinder:~$\\rightarrow$\\,Partner)"

            if hochzeit_nr < anzahl_hochzeiten:
                text += "" + "\n\n"
            person_data["hochzeiten"] += text

            is_first = False

