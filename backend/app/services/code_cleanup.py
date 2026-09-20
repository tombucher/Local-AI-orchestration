"""
Nettoyage des sorties LLM destinées à être écrites telles quelles dans un fichier.

Les modèles encadrent presque systématiquement leur réponse par des fences
Markdown (```html … ```), parfois précédées d'une phrase d'introduction. Ces
marqueurs cassent le fichier produit : on les retire ici, une fois pour toutes.
"""

import re
from typing import List, Optional, Tuple

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
