"""
Notation des références visuelles par un modèle doté de vision.

La notation lexicale (titre + description) ne peut pas fonctionner ici : les
sources nomment leurs images `IMG_8531.JPG` ou `movieposter.jpg`, et une image
intitulée « Brutalist Design » s'est révélée être un tracteur rouillé. Seul un
modèle qui regarde réellement l'image peut trancher.

Mesuré le 21/09/2026 sur gemma4:12b-mlx : ~0,7 s par vignette, soit une
vingtaine de secondes pour un lot complet — négligeable face aux minutes que
prend déjà une veille.
"""

import asyncio
import base64
import logging
import re
from typing import Any, Dict, List, Optional

import aiohttp
import ollama

from app.core.config import settings as app_settings
from app.services.model_registry import resolve_model, supports_vision

logger = logging.getLogger(__name__)

# Au-delà, le temps de notation devient sensible sans gain réel : l'utilisateur
# ne regarde pas 40 images d'un coup.
MAX_IMAGES_A_NOTER = 24
MAX_OCTETS_PAR_IMAGE = 4 * 1024 * 1024
TELECHARGEMENTS_SIMULTANES = 4
SEUIL_DEFAUT = 55.0

# Consigne calibrée : sans échelle explicite ni consigne de sévérité, le modèle
# note tout entre 85 et 95 et ne discrimine rien (mesuré).
GABARIT_PROMPT = """Tu tries des images pour un moodboard.

RECHERCHÉ : {recherche}

Regarde l'image, puis réponds EXACTEMENT sous la forme :
DESCRIPTION | NOTE

- DESCRIPTION : ce que montre l'image, 5 mots maximum, en français.
- NOTE : entier 0-100, calibré ainsi :
  0-20  = aucun rapport (paysage, portrait, animal, bâtiment quelconque)
  30-50 = vague air de famille, mais pas utilisable
  60-80 = utilisable comme référence
  90-100 = exactement ce qui est recherché
Sois sévère : la plupart des images méritent moins de 40."""


def _parse(reponse: str) -> Optional[Dict[str, Any]]:
    """Extrait (description, note) de la réponse du modèle."""
    texte = (reponse or "").strip()
    if not texte:
        return None
    description, _, reste = texte.partition("|")
    nombres = re.findall(r"\b(\d{1,3})\b", reste or texte)
    if not nombres:
        return None
    note = max(0, min(100, int(nombres[-1])))
    libelle = description.strip(" .-—|") if "|" in texte else ""
    return {"score": float(note), "description": libelle[:120]}


async def _telecharger(session: aiohttp.ClientSession, url: str) -> Optional[bytes]:
    """Récupère une vignette, ou None si elle est injoignable ou trop lourde.

    `content.read(n)` renvoie *jusqu'à* n octets, donc souvent le premier paquet
    seulement : on obtenait des images tronquées que le modèle rejetait. On lit
    donc le corps entier, après avoir écarté les gros fichiers sur Content-Length.
    """
    if not url:
        return None
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return None
            annonce = resp.headers.get("Content-Length")
            if annonce and annonce.isdigit() and int(annonce) > MAX_OCTETS_PAR_IMAGE:
                return None  # un GIF de 20 Mo n'apporte rien de plus qu'une vignette
            octets = await resp.read()
            return octets if 0 < len(octets) <= MAX_OCTETS_PAR_IMAGE else None
    except Exception:
        return None


async def score_images_with_vision(
    images: List[Dict[str, Any]],
    recherche: str,
    model: Optional[str] = None,
    limite: int = MAX_IMAGES_A_NOTER,
) -> List[Dict[str, Any]]:
    """Note les images en les regardant, et renseigne `vision_description`.

    `recherche` décrit en une phrase ce que le moodboard cherche.
    Les images non notées (téléchargement ou modèle en échec) gardent leur score
    lexical : mieux vaut un tri imparfait qu'une image perdue.
    """
    if not images:
        return images

    modele = resolve_model(model or app_settings.OLLAMA_MODEL_PROMPT, "notation visuelle")
    if not supports_vision(modele):
        logger.info(f"🖼 {modele} n'a pas la vision — notation lexicale conservée")
        return images

    lot = images[:limite]
    gate = asyncio.Semaphore(TELECHARGEMENTS_SIMULTANES)

    async with aiohttp.ClientSession(
        headers={"User-Agent": "Mozilla/5.0 OrchestratorIA/1.0 (veille personnelle)"}
    ) as session:

        async def recuperer(img):
            async with gate:
                return await _telecharger(session, img.get("thumbnail_url") or img.get("image_url") or "")

        octets_par_image = await asyncio.gather(*(recuperer(i) for i in lot))

    client = ollama.AsyncClient(host=app_settings.OLLAMA_HOST, timeout=120.0)
    prompt = GABARIT_PROMPT.format(recherche=recherche[:400])
    notees = echecs = 0

    # Séquentiel : Ollama sérialise de toute façon les requêtes sur un même modèle
    for img, octets in zip(lot, octets_par_image):
        if not octets:
            echecs += 1
            continue
        try:
            reponse = await client.chat(
                model=modele,
                messages=[{"role": "user", "content": prompt,
                           "images": [base64.b64encode(octets).decode("ascii")]}],
                think=False,
                options={"temperature": 0.1, "num_predict": 40},
            )
            resultat = _parse(reponse["message"].get("content") or "")
        except Exception as e:
            logger.debug(f"Notation visuelle en échec : {e}")
            resultat = None

        if resultat:
            img["relevance_score"] = resultat["score"]
            if resultat["description"]:
                img["vision_description"] = resultat["description"]
            notees += 1
        else:
            echecs += 1

    logger.info(f"👁 Notation visuelle : {notees} images notées par {modele}"
                + (f", {echecs} non notées (score lexical conservé)" if echecs else ""))
    return images


def titre_illisible(titre: str) -> bool:
    """Le titre est-il un nom de fichier ou un identifiant plutôt qu'un intitulé ?"""
    t = (titre or "").strip()
    if not t:
        return True
    if re.fullmatch(r"[\w\-. ]+\.(jpe?g|png|gif|webp|svg)", t, re.I):
        return True
    if re.fullmatch(r"https?://\S+", t):
        return True
    # Suite de chiffres/hexadécimal sans mot lisible
    return bool(re.fullmatch(r"[0-9a-f_\-.]{12,}", t, re.I))
