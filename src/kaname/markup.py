"""Plain text and compact Markdown escaping shared by composition and links."""
import re


def plain(value):
    return " ".join(str(value).split())


def inline(value):
    return re.sub(r"([\\`*_{}\[\]()<>!#|])", r"\\\1", plain(value))


def concept(value):
    return plain(re.sub(r"[\[\]#|^<>\\/:*?\"]", " ", plain(value))).strip(" .")[:160].rstrip(" .")


def valid_saved_concept(value):
    """Canonical terms or the exact output range of the old formatter.

    Old replacement could leave repeated ASCII spaces or truncate at a space
    or period at character 160. Accept those saved labels without rewriting
    Notes; delimiters, non-ASCII whitespace and unbounded labels stay rejected.
    """
    if not isinstance(value, str) or not 1 <= len(value) <= 160:
        return False
    if value == concept(value):
        return True
    if (value.startswith((" ", ".")) or
            (len(value) < 160 and value.endswith((" ", "."))) or
            any(char.isspace() and char != " " for char in value)):
        return False
    return concept(value) == plain(value).strip(" .")
