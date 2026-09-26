"""
Contrat d'interface entre les fichiers d'un projet web, et contrôle de cohérence.

Constat du 26/09/2026 sur le projet de test : le HTML (7 400 caractères) était
transmis tronqué à 4 000 au CSS et au JS. La zone du simulateur se trouvait après
la coupure : le JS a ciblé `#bouton-imprimer`, qui n'existait pas, et le CSS a
stylé 14 classes absentes du HTML tout en oubliant 16 qui y étaient.

Le code peut être tronqué ; le contrat, lui, est court et toujours transmis en
entier : identifiants, classes, variables CSS, éléments visés par le JS.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set

_HTML_ID = re.compile(r"""\bid\s*=\s*["'`]([^"'`\s>]+)["'`]""")
_HTML_CLASS = re.compile(r"""\bclass(?:Name)?\s*=\s*["'`]([^"'`>]+)["'`]""")
_JS_ID_ASSIGN = re.compile(r"""\.id\s*=\s*["'`]([\w-]+)["'`]""")
_JS_CLASSLIST = re.compile(r"""classList\.(?:add|toggle|replace)\(([^)]*)\)""")
_JS_BY_ID = re.compile(r"""getElementById\(\s*["'`]([\w-]+)["'`]""")
_JS_QUERY = re.compile(r"""querySelector(?:All)?\(\s*["'`]([^"'`]+)["'`]""")
_STRING = re.compile(r"""["'`]([\w-]+)["'`]""")
_HTML_BUTTON_ID = re.compile(r"""<button\b[^>]*?\bid\s*=\s*["']([^"']+)["']""", re.I)
_LOCAL_REF = re.compile(r"""<(?:link|script|img)\b[^>]*?\b(?:href|src)\s*=\s*["']([^"']+)["']""", re.I)

_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_CSS_DECLARATION = re.compile(r":[^;{}]*;")
_CSS_URL = re.compile(r"url\([^)]*\)", re.I)
_CSS_CLASS = re.compile(r"\.(-?[_a-zA-Z][\w-]*)")
_CSS_ID = re.compile(r"#(-?[_a-zA-Z][\w-]*)")
_CSS_VAR_DEF = re.compile(r"(--[\w-]+)\s*:")
_SEL_ID = re.compile(r"#(-?[_a-zA-Z][\w-]*)")
_SEL_CLASS = re.compile(r"\.(-?[_a-zA-Z][\w-]*)")


@dataclass
class Contract:
    ids: Set[str] = field(default_factory=set)            # définis (HTML, ou créés par le JS)
    classes: Set[str] = field(default_factory=set)        # utilisées dans le balisage
    styled_classes: Set[str] = field(default_factory=set)  # stylées par le CSS
    styled_ids: Set[str] = field(default_factory=set)
    css_vars: Set[str] = field(default_factory=set)
    targeted_ids: Set[str] = field(default_factory=set)   # visés par le JS
    targeted_classes: Set[str] = field(default_factory=set)
    local_refs: Set[str] = field(default_factory=set)     # fichiers liés par le HTML
    button_ids: Set[str] = field(default_factory=set)     # boutons prévus par le HTML

    def is_empty(self) -> bool:
        return not any(vars(self).values())


def _kind(path: str) -> str:
    return path.rsplit(".", 1)[-1].lower() if "." in path else ""


def _markup(code: str, contract: Contract) -> None:
    contract.ids |= set(_HTML_ID.findall(code))
    for group in _HTML_CLASS.findall(code):
        # Les gabarits JS glissent des ${…} dans les classes : on les ignore
        contract.classes |= {c for c in group.split() if re.fullmatch(r"-?[_a-zA-Z][\w-]*", c)}


def extract_contract(path: str, code: str) -> Contract:
    contract = Contract()
    code = code or ""
    kind = _kind(path)

    if kind in ("html", "htm"):
        _markup(code, contract)
        contract.button_ids = set(_HTML_BUTTON_ID.findall(code))
        contract.local_refs = {
            ref for ref in _LOCAL_REF.findall(code)
            if not re.match(r"^(https?:|//|data:|mailto:|#)", ref)
        }
    elif kind in ("css", "scss", "sass"):
        bare = _CSS_URL.sub("", _CSS_DECLARATION.sub(";", _CSS_COMMENT.sub("", code)))
        contract.styled_classes = set(_CSS_CLASS.findall(bare))
        contract.styled_ids = set(_CSS_ID.findall(bare))
        contract.css_vars = set(_CSS_VAR_DEF.findall(_CSS_COMMENT.sub("", code)))
    elif kind in ("js", "mjs", "jsx", "ts", "tsx"):
        _markup(code, contract)  # balisage construit dans des chaînes
        contract.ids |= set(_JS_ID_ASSIGN.findall(code))
        for args in _JS_CLASSLIST.findall(code):
            contract.classes |= set(_STRING.findall(args))
        contract.targeted_ids = set(_JS_BY_ID.findall(code))
        for selector in _JS_QUERY.findall(code):
            contract.targeted_ids |= set(_SEL_ID.findall(selector))
            contract.targeted_classes |= set(_SEL_CLASS.findall(selector))
    return contract


def _liste(items: Set[str], prefix: str = "", limit: int = 80) -> str:
    ordered = sorted(items)
    shown = ", ".join(f"`{prefix}{i}`" for i in ordered[:limit])
    return shown + (f" … (+{len(ordered) - limit})" if len(ordered) > limit else "")


def format_contract(path: str, contract: Contract) -> str:
    """Résumé d'un fichier, à injecter en entier dans le prompt."""
    lines = [f"- `{path}`"]
    if contract.ids:
        lines.append(f"  - identifiants : {_liste(contract.ids, '#')}")
    if contract.classes:
        lines.append(f"  - classes : {_liste(contract.classes, '.')}")
    if contract.styled_classes:
        lines.append(f"  - classes stylées : {_liste(contract.styled_classes, '.')}")
    if contract.css_vars:
        lines.append(f"  - variables CSS : {_liste(contract.css_vars)}")
    if contract.targeted_ids or contract.targeted_classes:
        cibles = contract.targeted_ids and _liste(contract.targeted_ids, '#') or ""
        if contract.targeted_classes:
            cibles = ", ".join(filter(None, [cibles, _liste(contract.targeted_classes, '.')]))
        lines.append(f"  - éléments visés par le script : {cibles}")
    return "\n".join(lines)


def check_coherence(files: Dict[str, str]) -> List[str]:
    """Liens cassés entre les fichiers d'un projet web, en phrases lisibles.

    Ne signale que ce qui casse réellement le rendu : un script qui vise un
    élément absent, un fichier lié qui n'existe pas, un HTML que la feuille de
    styles ignore presque entièrement.
    """
    contracts = {path: extract_contract(path, code) for path, code in files.items()}
    html = {p: c for p, c in contracts.items() if _kind(p) in ("html", "htm")}
    css = {p: c for p, c in contracts.items() if _kind(p) in ("css", "scss", "sass")}
    scripts = {p: c for p, c in contracts.items() if _kind(p) in ("js", "mjs", "jsx", "ts", "tsx")}
    if not html:
        return []

    ids_definis = set().union(*(c.ids for c in contracts.values()))
    classes_utilisees = set().union(*(c.classes for c in contracts.values()))
    warnings: List[str] = []

    for path, c in scripts.items():
        manquants = c.targeted_ids - ids_definis
        if manquants:
            warnings.append(f"{path} vise {_liste(manquants, '#', 8)}, absent du HTML : le script ne trouvera pas ces éléments.")
        classes_manquantes = c.targeted_classes - classes_utilisees
        if classes_manquantes:
            warnings.append(f"{path} cherche {_liste(classes_manquantes, '.', 8)}, classe utilisée nulle part.")

    if scripts:
        cibles = set().union(*(c.targeted_ids for c in scripts.values()))
        for path, c in html.items():
            inertes = c.button_ids - cibles
            if inertes:
                warnings.append(f"{path} prévoit {_liste(inertes, '#', 8)}, bouton qu'aucun script ne branche : il restera sans effet.")

    for path, c in html.items():
        absents = {ref.split("?")[0].lstrip("./") for ref in c.local_refs} - set(files)
        if absents:
            warnings.append(f"{path} charge {_liste(absents, '', 8)}, fichier qui n'existe pas dans le projet.")

    if css:
        stylees = set().union(*(c.styled_classes for c in css.values()))
        html_classes = set().union(*(c.classes for c in html.values()))
        if html_classes:
            ignorees = html_classes - stylees
            if len(ignorees) >= max(3, len(html_classes) / 3):
                warnings.append(
                    f"La feuille de styles ignore {len(ignorees)} classes du HTML sur {len(html_classes)} "
                    f"(ex. {_liste(set(sorted(ignorees)[:6]), '.')})."
                )
        creees_par_script = set().union(*(c.classes for c in scripts.values())) if scripts else set()
        non_stylees = creees_par_script - stylees
        if len(non_stylees) >= 3:
            warnings.append(
                f"Le script crée des éléments de classes {_liste(non_stylees, '.', 8)} "
                f"que la feuille de styles ne connaît pas : ils s'afficheront sans style."
            )
        orphelines = stylees - classes_utilisees
        if len(orphelines) >= 5:
            warnings.append(
                f"La feuille de styles définit {len(orphelines)} classes que ni le HTML ni le script "
                f"n'utilisent (ex. {_liste(set(sorted(orphelines)[:6]), '.')})."
            )
    return warnings
