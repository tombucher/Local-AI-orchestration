"""
Bibliothèque de flux : vérification d'un flux RSS/Atom et déduction de ses thèmes.

À l'ajout, on interroge réellement le flux. Deux raisons :
1. repérer tout de suite les URLs mortes — deux des flux de veille écolo de
   l'utilisateur renvoyaient 404 depuis des mois sans que rien ne le signale ;
2. déduire des étiquettes à partir du contenu, pour que la veille puisse choisir
   les sources adaptées au sujet sans que l'utilisateur ait à les saisir.
"""

import logging
import re
from collections import Counter
from typing import Any, Dict, List, Optional

import aiohttp
import feedparser
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

FETCH_TIMEOUT = 15
MAX_TAGS = 12
MIN_TAG_LENGTH = 4

# Mots trop fréquents pour caractériser un flux
TAG_STOPWORDS = {
    # français
    'dans', 'pour', 'avec', 'sans', 'plus', 'tout', 'tous', 'cette', 'leur', 'être',
    'avoir', 'faire', 'entre', 'après', 'avant', 'depuis', 'contre', 'aussi', 'comme',
    'quand', 'alors', 'encore', 'toujours', 'jamais', 'autres', 'ainsi', 'même',
    'nouveau', 'nouvelle', 'nouvelles', 'article', 'articles', 'lire', 'suite',
    # anglais
    'this', 'that', 'with', 'from', 'have', 'has', 'been', 'their', 'there', 'what',
    'when', 'which', 'will', 'would', 'about', 'more', 'most', 'other', 'into',
    'than', 'they', 'them', 'were', 'also', 'said', 'says', 'new', 'news', 'post',
    'posts', 'read', 'appeared', 'first', 'article', 'continue', 'reading',
    # mois : ils remontent systématiquement depuis les dates des entrées
    'janvier', 'février', 'fevrier', 'mars', 'avril', 'juin', 'juillet', 'août', 'aout',
    'septembre', 'octobre', 'novembre', 'décembre', 'decembre',
    'january', 'february', 'march', 'april', 'june', 'july', 'august',
    'september', 'october', 'november', 'december',
    # verbes et mots passe-partout qui remontent sinon comme « thèmes »
    'like', 'likes', 'make', 'makes', 'made', 'become', 'becomes', 'matter',
    'matters', 'member', 'members', 'through', 'between', 'during', 'where',
    'while', 'these', 'those', 'such', 'over', 'under', 'after', 'before',
    'being', 'does', 'each', 'every', 'much', 'many', 'some', 'only', 'just',
    'still', 'well', 'back', 'even', 'take', 'takes', 'come', 'comes', 'gets',
    'know', 'think', 'want', 'need', 'look', 'looks', 'find', 'finds', 'show',
    'shows', 'says', 'year', 'years', 'time', 'times', 'today', 'week', 'world',
    'people', 'work', 'works', 'život',
    'leurs', 'notre', 'votre', 'nous', 'vous', 'elles', 'celui', 'celle',
    'ceux', 'dont', 'mais', 'donc', 'puis', 'très', 'bien', 'peut', 'sont',
    'était', 'fait', 'faits', 'chez', 'sous', 'vers', 'selon', 'toute',
    'toutes', 'autre', 'année', 'années', 'jour', 'jours', 'gens',
}


def _words(text: str) -> List[str]:
    """Mots signifiants d'un texte.

    Découpe sur les apostrophes : sans ça « l'écologie » ressort en « l'écologie »
    au lieu d'« écologie », et le thème principal du flux passe à la trappe.
    """
    out: List[str] = []
    for token in re.split(r"[^\w'’-]+", (text or '').casefold()):
        for part in re.split(r"['’]", token):
            part = part.strip('-_')
            if len(part) >= MIN_TAG_LENGTH and not part.isdigit() and part not in TAG_STOPWORDS:
                out.append(part)
    return out


def derive_tags(parsed: Any, limit: int = MAX_TAGS) -> List[str]:
    """Déduit les thèmes d'un flux depuis son titre, ses catégories et ses entrées.

    Trois sources, par ordre de fiabilité décroissante :
    1. le titre et la description du flux — ils décrivent la ligne éditoriale ;
    2. les catégories déclarées par les entrées, quand le flux en publie ;
    3. les mots récurrents des entrées, **présents dans au moins deux entrées** —
       sans ce seuil, un nom propre croisé une fois (« jules », « ferry ») devient
       un thème du flux.
    """
    scores: Counter = Counter()

    for source, weight in ((parsed.feed.get('title', ''), 6),
                           (parsed.feed.get('subtitle', '') or parsed.feed.get('description', ''), 4)):
        for word in dict.fromkeys(_words(source)):
            scores[word] += weight

    entries = parsed.entries[:25]
    entry_hits: Counter = Counter()
    for entry in entries:
        for tag in (entry.get('tags') or []):
            label = (tag.get('term') or '').casefold().strip()
            if MIN_TAG_LENGTH <= len(label) <= 40 and label not in TAG_STOPWORDS:
                scores[label] += 4
        text = BeautifulSoup(
            f"{entry.get('title', '')} {entry.get('summary', '')}", 'html.parser'
        ).get_text(' ', strip=True)
        # dict.fromkeys : un mot répété dans un même article ne compte qu'une fois
        for word in dict.fromkeys(_words(text)):
            entry_hits[word] += 1

    for word, hits in entry_hits.items():
        if hits >= 2:  # thème récurrent, pas un accident d'actualité
            scores[word] += hits

    return [word for word, _ in scores.most_common(limit)]


async def inspect_feed(url: str, session: Optional[aiohttp.ClientSession] = None) -> Dict[str, Any]:
    """Interroge un flux et renvoie son état.

    Renvoie toujours un dict — jamais d'exception — avec :
    `ok`, `status` (message lisible), `title`, `tags`, `entry_count`, `sample`.
    """
    result: Dict[str, Any] = {
        "ok": False, "status": "", "title": "", "tags": [], "entry_count": 0, "sample": [],
    }

    # Garde-fou : uniquement du http(s) public (mêmes règles que la recherche web)
    from app.services.modules.web_research import WebResearchModule
    if not WebResearchModule._is_safe_url(url):
        result["status"] = "URL refusée (doit être une adresse http(s) publique)"
        return result

    own_session = session is None
    session = session or aiohttp.ClientSession(
        headers={"User-Agent": "Mozilla/5.0 OrchestratorIA/1.0 (veille personnelle)"}
    )
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=FETCH_TIMEOUT)) as resp:
            if resp.status != 200:
                result["status"] = f"Le serveur répond {resp.status}"
                return result
            raw = await resp.text()
    except Exception as e:
        result["status"] = f"Injoignable ({type(e).__name__})"
        return result
    finally:
        if own_session:
            await session.close()

    parsed = feedparser.parse(raw)
    entries = parsed.entries or []
    if not entries:
        result["status"] = "Répond, mais ne contient aucune entrée (flux inactif ?)"
        return result

    result.update({
        "ok": True,
        "status": "ok",
        "title": (parsed.feed.get("title") or url)[:255],
        "tags": derive_tags(parsed),
        "entry_count": len(entries),
        "sample": [
            BeautifulSoup(e.get("title", ""), "html.parser").get_text(" ", strip=True)[:120]
            for e in entries[:3]
        ],
    })
    logger.info(f"✓ Flux vérifié « {result['title'][:40]} » : {len(entries)} entrées, "
                f"thèmes {result['tags'][:5]}")
    return result
