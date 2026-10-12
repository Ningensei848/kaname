"""Plain text and compact Markdown escaping shared by composition and links."""
import re


def plain(value):
    return " ".join(str(value).split())


def inline(value):
    return re.sub(r"([\\`*_{}\[\]()<>!#|])", r"\\\1", plain(value))


def concept(value):
    return re.sub(r"[\[\]#|^<>\\/:*?\"]", " ", plain(value)).strip(" .")[:160]
