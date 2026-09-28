"""
Reconnaître le langage d'un fichier d'après son contenu, pas d'après son nom.

Constat du 28/09/2026 : la tâche « Conception du moteur de transformation
ASCII » avait reçu le nom index.html (sa description parlait d'articles
« HTML/Markdown » en entrée). Le modèle a écrit, à juste titre, un module
Python ; l'aperçu du site a alors affiché ce Python comme une page web.

Le nom prévu par le plan de fichiers reste la règle ; on ne le corrige que
lorsque le contenu contredit nettement l'extension.
"""

import json
import re
import unicodedata
from typing import Optional

# Familles d'extensions équivalentes : un .htm reste du HTML
FAMILLES = {
    "html": "html", "htm": "html",
    "css": "css", "scss": "css", "sass": "css",
    "js": "js", "mjs": "js", "cjs": "js", "jsx": "js", "ts": "js", "tsx": "js",
    "py": "py", "md": "md", "markdown": "md", "json": "json", "php": "php",
    "sh": "sh", "sql": "sql", "svg": "svg",
}

_HTML = re.compile(r"<!doctype\s+html|<html[\s>]|<head[\s>]|<body[\s>]", re.I)
_BALISES = re.compile(r"<(div|section|main|header|footer|p|span|ul|a|img|nav|article)[\s>]", re.I)
_PYTHON = re.compile(r"^(def \w+\(|class \w+[:(]|import \w+|from [\w.]+ import |if __name__ == )", re.M)
_JS = re.compile(r"\b(function\s*\w*\s*\(|const |let |=>|document\.|window\.|addEventListener)")
_CSS = re.compile(r"^\s*[@:.#\w\-\[\]*>,\s\"'=()]+\{[^{}]*:[^{}]*;?[^{}]*\}", re.M)


def detect_language(code: Optional[str]) -> Optional[str]:
    """Famille du contenu (html, css, js, py, md, json, php, sh), ou None si incertain."""
    texte = (code or "").lstrip("﻿").strip()
    if not texte:
        return None
    premiere = texte.split("\n", 1)[0]
    if premiere.startswith("#!"):
        if "python" in premiere:
            return "py"
        if re.search(r"\b(ba|z)?sh\b", premiere):
            return "sh"
        if "node" in premiere:
            return "js"
    if texte.startswith("<?php"):
        return "php"
    if texte.startswith("<svg") or (texte.startswith("<?xml") and "<svg" in texte[:500]):
        return "svg"
    if _HTML.search(texte[:2000]) or (texte.startswith("<") and len(_BALISES.findall(texte)) >= 3):
        return "html"
    if texte[0] in "{[":
        try:
            json.loads(texte)
            return "json"
        except ValueError:
            pass
    python = len(_PYTHON.findall(texte))
    js = len(_JS.findall(texte))
    if python >= 2 and python > js:
        return "py"
    if len(_CSS.findall(texte)) >= 2 and js == 0 and python == 0:
        return "css"
    if js >= 2 and python == 0:
        return "js"
    if re.match(r"#{1,3} \S", texte) and python == 0 and js == 0:
        return "md"
    return None


def extension_family(path: Optional[str]) -> Optional[str]:
    if not path or "." not in path:
        return None
    return FAMILLES.get(path.rsplit(".", 1)[1].lower())


def effective_path(path: Optional[str], code: Optional[str], slug: str) -> Optional[str]:
    """Le chemin prévu, sauf si le contenu en contredit nettement l'extension.

    `slug` sert à nommer le fichier corrigé (index.html → moteur-ascii.py) :
    garder « index » pour un module Python serait trompeur.
    """
    if not path:
        return path
    attendu = extension_family(path)
    reel = detect_language(code)
    if attendu is None or reel is None or attendu == reel:
        return path
    dossier = path.rsplit("/", 1)[0] + "/" if "/" in path else ""
    return f"{dossier}{slug}.{reel}"


def file_slug(title: str, max_length: int = 48) -> str:
    """Nom de fichier tiré d'un titre, coupé entre deux mots (pas « …-transfor »)."""
    texte = "".join(c for c in unicodedata.normalize("NFD", title or "")
                    if unicodedata.category(c) != "Mn").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", texte).strip("-") or "fichier"
    if len(slug) > max_length:
        coupe = slug[:max_length + 1].rsplit("-", 1)[0]
        slug = coupe if len(coupe) >= 12 else slug[:max_length]
    return slug.strip("-")
