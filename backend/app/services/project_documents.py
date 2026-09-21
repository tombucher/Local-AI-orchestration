"""
Mise à disposition des documents de projet au modèle.

Principe retenu : injection **selon la tâche, avec budget**. Tout déverser dans
chaque prompt sature la fenêtre de contexte dès le troisième fichier ; on classe
donc les documents par pertinence vis-à-vis de la tâche et on en injecte le
contenu intégral jusqu'à un plafond de caractères. Les suivants sont seulement
cités par leur nom et leur note, pour que le modèle sache qu'ils existent.

Les images suivent un chemin distinct : elles ne comptent pas dans le budget
texte et ne sont transmises qu'aux modèles annonçant la capacité `vision`.
"""

import base64
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_document import DocumentKind, ProjectDocument

logger = logging.getLogger(__name__)

# Budget de texte issu des documents, par génération
MAX_CONTEXT_CHARS = 12000
MAX_CHARS_PER_DOCUMENT = 6000
# Au-delà, une image coûte trop de tokens pour un modèle local
MAX_IMAGES = 3

LANG_BY_EXTENSION = {
    'py': 'python', 'js': 'javascript', 'mjs': 'javascript', 'ts': 'typescript',
    'tsx': 'tsx', 'jsx': 'jsx', 'html': 'html', 'htm': 'html', 'css': 'css',
    'scss': 'scss', 'json': 'json', 'yaml': 'yaml', 'yml': 'yaml', 'sh': 'bash',
    'sql': 'sql', 'md': 'markdown', 'toml': 'toml', 'rs': 'rust', 'go': 'go',
}


@dataclass
class DocumentContext:
    """Ce que les documents d'un projet apportent à une génération."""

    text: str = ""                                  # Bloc à insérer dans le prompt
    images: List[str] = field(default_factory=list)  # Images en base64, pour les modèles vision
    used: List[str] = field(default_factory=list)    # Noms des documents injectés en entier
    mentioned: List[str] = field(default_factory=list)  # Noms seulement cités

    def __bool__(self) -> bool:
        return bool(self.text or self.images)


def _language_for(name: str) -> str:
    extension = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    return LANG_BY_EXTENSION.get(extension, '')


def _significant(text: str) -> set:
    return {w for w in re.findall(r"[a-zà-öø-ÿ0-9][\w'’-]{3,}", (text or '').casefold())}


def _relevance(doc: ProjectDocument, needle: set) -> float:
    """Recouvrement entre le document (nom + note) et l'objectif de la tâche.

    Volontairement grossier : le nom et la note portent l'essentiel du sens, et
    scanner le contenu entier de chaque document à chaque génération coûterait
    plus cher que le gain de tri.
    """
    if not needle:
        return 0.0
    haystack = _significant(f"{doc.name} {doc.note or ''}")
    if not haystack:
        return 0.0
    return len(haystack & needle) / len(needle)


async def load_documents(db: AsyncSession, project_id: int) -> List[ProjectDocument]:
    """Documents actifs d'un projet, les plus récents d'abord."""
    result = await db.execute(
        select(ProjectDocument)
        .where(ProjectDocument.project_id == project_id, ProjectDocument.enabled.is_(True))
        .order_by(ProjectDocument.created_at.desc())
    )
    return list(result.scalars().all())


async def build_document_context(
    db: AsyncSession,
    project_id: int,
    objective: str = "",
    include_images: bool = False,
    max_chars: int = MAX_CONTEXT_CHARS,
) -> DocumentContext:
    """Assemble les documents pertinents pour une tâche donnée.

    `objective` est le titre et la description de la tâche : il sert à classer
    les documents. `include_images` n'est vrai que si le modèle a la vision.
    """
    documents = await load_documents(db, project_id)
    if not documents:
        return DocumentContext()

    needle = _significant(objective)
    textuels = [d for d in documents if not d.is_image]
    images = [d for d in documents if d.is_image]

    # Les plus pertinents d'abord ; à égalité, les plus récents (ordre de la requête)
    textuels.sort(key=lambda d: -_relevance(d, needle))

    contexte = DocumentContext()
    budget = max_chars
    extraits: List[str] = []

    for doc in textuels:
        contenu = (doc.content or '').strip()
        if not contenu:
            continue
        if budget < 400:  # plus la place d'injecter quoi que ce soit d'utile
            contexte.mentioned.append(doc.name)
            continue
        limite = min(MAX_CHARS_PER_DOCUMENT, budget)
        tronque = len(contenu) > limite
        corps = contenu[:limite] + ("\n… (document tronqué)" if tronque else "")
        budget -= len(corps)
        contexte.used.append(doc.name)

        entete = f"#### {doc.name}"
        if doc.note:
            entete += f" — {doc.note}"
        if doc.kind == DocumentKind.CODE:
            extraits.append(f"{entete}\n```{_language_for(doc.name)}\n{corps}\n```")
        else:
            extraits.append(f"{entete}\n{corps}")

    if include_images:
        for doc in images[:MAX_IMAGES]:
            if doc.binary:
                contexte.images.append(base64.b64encode(doc.binary).decode("ascii"))
                contexte.used.append(doc.name)
    else:
        # Le modèle ne voit pas les images : au moins signaler qu'elles existent
        for doc in images:
            contexte.mentioned.append(doc.name)

    if not extraits and not contexte.images and not contexte.mentioned:
        return DocumentContext()

    lignes = ["## Documents de référence fournis par l'utilisateur",
              "Ils font autorité : préfère-les à tes suppositions."]
    if extraits:
        lignes.append("")
        lignes.extend(extraits)
    if contexte.images:
        lignes.append("")
        lignes.append(f"{len(contexte.images)} image(s) de référence sont jointes à ce message.")
    if contexte.mentioned:
        lignes.append("")
        lignes.append("Également disponibles dans le projet, non détaillés ici : "
                      + ", ".join(f"« {n} »" for n in contexte.mentioned))

    contexte.text = "\n".join(lignes)
    logger.info(
        f"📎 Documents projet {project_id} : {len(contexte.used)} injectés, "
        f"{len(contexte.mentioned)} cités, {len(contexte.images)} image(s)"
    )
    return contexte


def summarise_for_memory(documents: List[ProjectDocument]) -> str:
    """Ligne résumant les documents, pour le carnet de projet."""
    if not documents:
        return ""
    parts = []
    for doc in documents[:10]:
        label = doc.name
        if doc.note:
            label += f" ({doc.note})"
        parts.append(label)
    return "Documents fournis : " + " ; ".join(parts)
