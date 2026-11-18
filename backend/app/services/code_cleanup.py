"""
Nettoyage des sorties LLM destinées à être écrites telles quelles dans un fichier.

Les modèles encadrent presque systématiquement leur réponse par des fences
Markdown (```html … ```), parfois précédées d'une phrase d'introduction. Ces
marqueurs cassent le fichier produit : on les retire ici, une fois pour toutes.
"""

import posixpath
import re
from typing import Dict, List, Optional, Tuple

# Une ligne de fence : ``` / ~~~ éventuellement suivi d'un langage
_FENCE_RE = re.compile(r'^[ \t]*(?:`{3,}|~{3,})[ \t]*([\w+#.\-]*)[ \t]*$')


def _fence_lines(lines: List[str]) -> List[int]:
    return [i for i, line in enumerate(lines) if _FENCE_RE.match(line)]


def _blocks(lines: List[str], fences: List[int]) -> List[Tuple[int, int]]:
    """Paires (ouverture, fermeture) des blocs clôturés."""
    pairs: List[Tuple[int, int]] = []
    opened: Optional[int] = None
    for index in fences:
        if opened is None:
            opened = index
        else:
            pairs.append((opened, index))
            opened = None
    return pairs


def strip_code_fences(text: Optional[str]) -> str:
    """Retire les fences Markdown qui encadrent du code généré.

    Une sortie en plusieurs fichiers (`=== chemin ===`) est nettoyée fichier
    par fichier : traitée d'un bloc, seul le plus gros fichier survivait.
    """
    if text and _MULTI_FILE.search(text):
        fichiers = split_multi_file(text, nettoyer=True)
        if fichiers:
            return join_multi_file(fichiers)
    return _strip_single(text)


def _strip_single(text: Optional[str]) -> str:
    """Nettoyage d'un fichier seul (voir strip_code_fences).

    - ```lang … ``` couvrant toute la réponse → contenu seul
    - phrase d'intro + un bloc qui domine la réponse → contenu du bloc
    - fence ouvrante orpheline → ligne supprimée
    - sinon le texte est renvoyé inchangé (on ne casse pas un vrai Markdown)
    """
    if not text:
        return text or ''

    cleaned = text.strip()
    lines = cleaned.split('\n')
    non_empty = [i for i, line in enumerate(lines) if line.strip()]
    if not non_empty:
        return cleaned

    first, last = non_empty[0], non_empty[-1]

    # Cas nominal : la réponse entière est un bloc clôturé
    if first != last and _FENCE_RE.match(lines[first]) and _FENCE_RE.match(lines[last]):
        return '\n'.join(lines[first + 1:last]).strip('\n')

    fences = _fence_lines(lines)
    if not fences:
        return cleaned

    # Fence ouvrante sans fermeture (réponse tronquée) → on retire le marqueur
    if len(fences) == 1:
        return '\n'.join(lines[:fences[0]] + lines[fences[0] + 1:]).strip('\n')

    # Intro en prose puis un bloc de code : on garde le bloc s'il domine
    pairs = _blocks(lines, fences)
    if not pairs:
        return cleaned

    def body_size(pair: Tuple[int, int]) -> int:
        return sum(len(line) for line in lines[pair[0] + 1:pair[1]])

    biggest = max(pairs, key=body_size)
    total = sum(len(line) for line in lines) or 1
    if body_size(biggest) / total > 0.6:
        return '\n'.join(lines[biggest[0] + 1:biggest[1]]).strip('\n')

    return cleaned


# ------------------------------------------------- plusieurs fichiers --

# Une tâche peut rendre plusieurs fichiers, chacun précédé de `=== chemin ===`.
# Tout marqueur est reconnu, même au chemin douteux : sinon son contenu se collait
# au fichier précédent. Les chemins refusés par safe_path sont ensuite écartés.
_MULTI_FILE = re.compile(r"^===\s*(\S[^=\n]*?)\s*===\s*$", re.MULTILINE)


def safe_path(path: Optional[str]) -> Optional[str]:
    """Chemin relatif sans remontée : le modèle écrit les chemins, pas nous."""
    if not path:
        return None
    clean = posixpath.normpath(path.replace("\\", "/").strip("`'\" ")).lstrip("/")
    if clean in ("", ".") or clean.startswith("..") or "/../" in f"/{clean}/":
        return None
    return clean


def split_multi_file(code: Optional[str], nettoyer: bool = False) -> Dict[str, str]:
    """Découpe une sortie `=== chemin ===` en fichiers ; vide si ce n'en est pas une."""
    code = code or ""
    marks = list(_MULTI_FILE.finditer(code))
    files: Dict[str, str] = {}
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(code)
        body = code[mark.end():end].strip("\n")
        if nettoyer:
            body = _strip_single(body)
        path = safe_path(mark.group(1))
        if body.strip() and path:
            files[path] = body.rstrip("\n") + "\n"
    return files


def join_multi_file(files: Dict[str, str]) -> str:
    """Inverse de split_multi_file."""
    return "\n".join(f"=== {path} ===\n{body.rstrip()}\n" for path, body in files.items())


_STYLE_INLINE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.I | re.S)
_SCRIPT_INLINE = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.I | re.S)
_TYPE_JS = re.compile(r"""\btype\s*=\s*["']?(?:text/javascript|application/javascript)?["']?(?:\s|$)""", re.I)


def extraire_en_ligne(html: str, css_path: str, js_path: str) -> Tuple[str, str, str]:
    """Sort le CSS et le JS écrits dans le HTML vers leurs fichiers.

    Filet de sécurité quand le modèle a tout mis dans la page malgré la
    consigne : (html relié aux fichiers, css extrait, js extrait). Les scripts
    à `src` (bibliothèques via CDN), les modules et les données JSON restent.
    """
    css = "\n\n".join(m.group(1).strip() for m in _STYLE_INLINE.finditer(html) if m.group(1).strip())
    morceaux_js: List[str] = []

    def sortir_script(m: "re.Match") -> str:
        attributs, corps = m.group(1), m.group(2)
        if "src=" in attributs.lower() or not corps.strip():
            return m.group(0)
        if "type" in attributs.lower() and not _TYPE_JS.search(attributs):
            return m.group(0)  # module, JSON, importmap : on n'y touche pas
        morceaux_js.append(corps.strip())
        return ""

    page = _STYLE_INLINE.sub("", html) if css else html
    page = _SCRIPT_INLINE.sub(sortir_script, page)
    js = "\n\n".join(morceaux_js)
    if css and css_path not in page:
        lien = f'<link rel="stylesheet" href="{css_path}">'
        page = re.sub(r"</head>", f"  {lien}\n</head>", page, count=1, flags=re.I) \
            if re.search(r"</head>", page, re.I) else f"{lien}\n{page}"
    if js and js_path not in page:
        balise = f'<script src="{js_path}" defer></script>'
        page = re.sub(r"</body>", f"  {balise}\n</body>", page, count=1, flags=re.I) \
            if re.search(r"</body>", page, re.I) else f"{page}\n{balise}"
    page = re.sub(r"\n[ \t]*\n([ \t]*\n)+", "\n\n", page)
    return page, css, js


# ---------------------------------------------- raisonnement avant le code --

# Début d'un fichier de code : commentaire, balise, directive, déclaration
_DEBUT_CODE = {
    'html': re.compile(r'^\s*(<!doctype|<html|<!--|<head|<body|<[a-z])', re.I),
    'css': re.compile(r'^\s*(/\*|@|:root|\*|[.#\[]?[a-zA-Z_\-][\w\-\s,.#:>~+\[\]="\'()*]*\{\s*$)'),
    'js': re.compile(r'^\s*(//|/\*|[\'"]use strict|\(|import\s|export\s|const\s|let\s|var\s|'
                     r'(async\s+)?function\b|class\s|window\.|document\.|if\s*\(|try\s*\{)'),
}
_EXTENSIONS_CODE = {'html': 'html', 'htm': 'html', 'css': 'css', 'js': 'js', 'mjs': 'js', 'cjs': 'js'}


def _ressemble_a_de_la_prose(ligne: str) -> bool:
    texte = ligne.strip()
    if not texte:
        return True
    texte = re.sub(r'^([-*]|\d+[.)])\s+', '', texte)       # puces et numéros de liste
    sans_code = re.sub(r'`[^`]*`', 'x', texte)              # `sketch.TWO_PI` compte pour un mot
    return len(sans_code.split()) >= 3 and not re.search(r'[;{}<>]|=>', sans_code)


def retirer_preambule(code: str, chemin: Optional[str]) -> str:
    """Retire le raisonnement écrit avant le code d'un fichier HTML, CSS ou JS.

    Cas du 18/11/2026 : qwen a commencé un .js par vingt lignes d'analyse en
    anglais (« The user wants me to rewrite… »), sans balises : le script ne
    pouvait plus s'exécuter. On coupe tout ce qui précède la première ligne de
    code, à condition que ce qui précède soit bien de la prose.
    """
    extension = (chemin or '').rsplit('.', 1)[-1].lower()
    debut = _DEBUT_CODE.get(_EXTENSIONS_CODE.get(extension, ''))
    if debut is None or not code:
        return code
    lignes = code.split('\n')
    for i, ligne in enumerate(lignes):
        if debut.match(ligne):
            if i and all(_ressemble_a_de_la_prose(l) for l in lignes[:i]):
                return '\n'.join(lignes[i:])
            return code
        if not _ressemble_a_de_la_prose(ligne):
            return code  # ni prose ni début reconnu : on ne touche à rien
    return code


def fichier_plausible(code: Optional[str], chemin: Optional[str]) -> bool:
    """Le contenu ressemble-t-il au fichier demandé ?

    Cas du 18/11/2026 : à l'étape HTML, qwen a répondu par le seul nom du
    fichier (34 caractères), enregistré comme page. Contrôle grossier, fait
    pour attraper ces réponses à côté, pas pour valider le code.
    """
    texte = (code or '').strip()
    extension = (chemin or '').rsplit('.', 1)[-1].lower()
    famille = _EXTENSIONS_CODE.get(extension)
    if famille == 'html':
        return len(texte) >= 150 and bool(re.search(r'<(!doctype|html|head|body|main|div|section|canvas|svg)\b', texte, re.I))
    if famille == 'css':
        return len(texte) >= 15 and '{' in texte and ':' in texte
    if famille == 'js':
        return len(texte) >= 20 and bool(re.search(r'[;{}()=]', texte))
    return bool(texte)
