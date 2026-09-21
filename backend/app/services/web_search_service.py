"""
Service de recherche web

Backends disponibles (par ordre de priorité) :
0. SearXNG auto-hébergé — métamoteur local (gratuit, sans clé, sans quota)
   → Configurer SEARXNG_URL dans .env (ex. http://searxng:8080)
   → Le service `searxng` du docker-compose l'expose sur 127.0.0.1:8888
1. Brave Search API — api.search.brave.com (gratuit, 2000 req/mois, fiable depuis Docker)
   → Configurer BRAVE_SEARCH_API_KEY dans docker-compose.yml ou .env
   → Clé gratuite sur https://api.search.brave.com
2. DuckDuckGo HTML — html.duckduckgo.com (scraping, pas de clé mais rate-limitée)
   → Fallback automatique si Brave API non configurée

Approche DDG :
- Requête HTTP directe sur html.duckduckgo.com (fonctionne depuis Docker quand non rate-limitée)
- Parse le HTML avec BeautifulSoup
- asyncio.to_thread() pour ne pas bloquer la boucle async
- Retry avec backoff + délais aléatoires
"""
import asyncio
import logging
import random
import time
from typing import List, Dict, Any, Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"
_SEARXNG_TIMEOUT = 20.0
_DDG_HTML_URL = "https://html.duckduckgo.com/html/"
_MAX_RETRIES = 4

_DDG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html",
}


# ─── Brave Search ──────────────────────────────────────────────────────────────

def _searxng_search_sync(
    query: str,
    max_results: int,
    base_url: str,
    language: str = "fr",
) -> List[Dict[str, Any]]:
    """Interroge une instance SearXNG via son API JSON.

    SearXNG agrège Google/Bing/Qwant/… : pas de clé, pas de quota, et il tourne
    chez toi. Le format JSON doit être activé (`search.formats: [html, json]`),
    sinon l'instance répond 403 — c'est le cas par défaut.
    """
    url = base_url.rstrip("/") + "/search"
    params = {
        "q": query,
        "format": "json",
        "language": language,
        "safesearch": 0,
    }
    try:
        with httpx.Client(timeout=_SEARXNG_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url, params=params, headers={"Accept": "application/json"})
        if resp.status_code == 403:
            logger.error(
                "SearXNG répond 403 : le format JSON n'est pas activé. Ajouter "
                "`json` à `search.formats` dans searxng/settings.yml, puis "
                "`docker compose restart searxng`."
            )
            return []
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        logger.warning(f"SearXNG indisponible ({base_url}): {e}")
        return []

    results = []
    for item in (payload.get("results") or [])[:max_results]:
        href = item.get("url")
        if not href:
            continue
        results.append({
            "title": item.get("title") or "Sans titre",
            "href": href,
            "body": item.get("content") or "",
            # SearXNG joint souvent la vignette du résultat (mesuré : la moitié
            # des résultats). Autant la conserver : la récupérer plus tard
            # coûterait un téléchargement de page par article.
            "image": item.get("img_src") or item.get("thumbnail") or None,
        })
    logger.info(f"✓ SearXNG: {len(results)} résultats pour '{query}'")
    return results


def _brave_search_sync(
    query: str,
    max_results: int,
    api_key: str,
    country: str = "FR",
    search_lang: str = "fr",
) -> List[Dict[str, Any]]:
    """
    Recherche via l'API Brave Search (synchrone).
    Clé gratuite sur https://api.search.brave.com — 2000 requêtes/mois.
    """
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {
        "q": query,
        "count": min(max_results, 20),
        "country": country,
        "search_lang": search_lang,
        "result_filter": "web",
        "extra_snippets": "true",
    }

    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(_BRAVE_API_URL, headers=headers, params=params)
            resp.raise_for_status()

        data = resp.json()
        web_results = data.get("web", {}).get("results", [])

        results = []
        for item in web_results[:max_results]:
            title = item.get("title", "")
            url = item.get("url", "")
            # Brave fournit `description` et éventuellement `extra_snippets`
            body = item.get("description", "")
            if not body and item.get("extra_snippets"):
                body = " ".join(item["extra_snippets"][:2])

            if title and url:
                results.append({"title": title, "href": url, "body": body})

        logger.debug(f"Brave '{query}' → {len(results)} résultats")
        return results

    except httpx.HTTPStatusError as e:
        logger.error(f"Brave API HTTP {e.response.status_code} pour '{query}': {e.response.text[:200]}")
        return []
    except Exception as e:
        logger.error(f"Brave API erreur pour '{query}': {e}")
        return []


# ─── DuckDuckGo HTML (fallback) ────────────────────────────────────────────────

def _ddg_search_sync(query: str, max_results: int, region: str) -> List[Dict[str, Any]]:
    """
    Recherche via le endpoint HTML de DuckDuckGo (fallback).
    Fonctionne sans clé API mais peut être rate-limitée depuis Docker.
    """
    params = {
        "q": query,
        "kl": region,
        "kp": "-1",
    }

    for attempt in range(_MAX_RETRIES):
        try:
            with httpx.Client(headers=_DDG_HEADERS, timeout=15, follow_redirects=True) as client:
                resp = client.post(_DDG_HTML_URL, data=params)
                resp.raise_for_status()

            # DDG renvoie 202 (rate-limit) ou une page vide sans résultats
            if resp.status_code == 202 or len(resp.text) < 500:
                wait = (2 ** attempt) + random.uniform(2, 5)
                logger.warning(
                    f"DDG rate-limited (status={resp.status_code}) pour '{query}' "
                    f"(tentative {attempt+1}/{_MAX_RETRIES}), attente {wait:.1f}s"
                )
                time.sleep(wait)
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            results = []

            for div in soup.select(".results_links"):
                title_tag = div.select_one(".result__a")
                snippet_tag = div.select_one(".result__snippet")

                if not title_tag:
                    continue

                href = title_tag.get("href", "")
                if "duckduckgo.com/y.js" in href:
                    continue  # Filtrer les pubs

                title = title_tag.get_text(strip=True)
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                if title and href:
                    results.append({"title": title, "href": href, "body": snippet})
                    if len(results) >= max_results:
                        break

            logger.debug(f"DDG HTML '{query}' → {len(results)} résultats")
            return results

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (202, 429):
                wait = (2 ** attempt) + random.uniform(1, 3)
                logger.warning(f"DDG rate-limited pour '{query}' (tentative {attempt+1}/{_MAX_RETRIES}), attente {wait:.1f}s")
                time.sleep(wait)
            else:
                logger.error(f"DDG HTTP error {e.response.status_code} pour '{query}'")
                return []
        except Exception as e:
            logger.error(f"DDG scraping erreur pour '{query}': {e}")
            if attempt < _MAX_RETRIES - 1:
                time.sleep(2 + attempt)
            else:
                return []

    logger.error(f"DDG : tous les essais ont échoué pour '{query}'")
    return []


# ─── Service principal ──────────────────────────────────────────────────────────

class WebSearchService:
    """
    Service de recherche web contextuelle.

    Utilise Brave Search API si BRAVE_SEARCH_API_KEY est configuré,
    sinon fallback sur le scraping HTML DuckDuckGo.

    Obtenir une clé Brave gratuite (2000 req/mois) :
    https://api.search.brave.com → "Get Started for Free"
    """

    def __init__(self, brave_api_key: Optional[str] = None):
        """
        Args:
            brave_api_key: Clé API Brave Search (override la config globale).
                          Si None, utilise BRAVE_SEARCH_API_KEY depuis les settings.
        """
        self._searxng_url = None
        try:
            from app.core.config import settings
            self._searxng_url = (settings.SEARXNG_URL or "").strip() or None
        except Exception:
            pass

        if brave_api_key is not None:
            self._brave_key = brave_api_key
        else:
            try:
                from app.core.config import settings
                self._brave_key = settings.BRAVE_SEARCH_API_KEY
            except Exception:
                self._brave_key = None

        backend = (
            "SearXNG" if self._searxng_url
            else "Brave Search API" if self._brave_key
            else "DuckDuckGo HTML (fallback)"
        )
        logger.debug(f"WebSearchService initialized — backend: {backend}")

    async def search_text(
        self,
        query: str,
        max_results: int = 5,
        region: str = "fr-fr"
    ) -> List[Dict[str, Any]]:
        """
        Recherche textuelle (async, non-bloquant).
        Retourne une liste de dicts : {title, href, body}
        """
        await asyncio.sleep(random.uniform(0.3, 1.2))

        if self._searxng_url:
            logger.info(f"🔎 SearXNG: '{query}' (max={max_results})")
            results = await asyncio.to_thread(
                _searxng_search_sync, query, max_results, self._searxng_url,
                region.split("-")[0] if "-" in region else "fr",
            )
            if results:
                logger.info(f"🔎 '{query}' → {len(results)} résultat(s)")
                return results
            # Instance en panne ou mal configurée : on ne perd pas la requête
            logger.warning("SearXNG n'a rien rendu — repli sur le backend suivant")

        if self._brave_key:
            logger.info(f"🔎 Brave Search: '{query}' (max={max_results})")
            # Convertir la région DDG (fr-fr) en country code Brave (FR)
            country = region.split("-")[-1].upper() if "-" in region else "US"
            search_lang = region.split("-")[0] if "-" in region else "en"
            results = await asyncio.to_thread(
                _brave_search_sync, query, max_results, self._brave_key, country, search_lang
            )
        else:
            logger.info(f"🔎 Recherche DDG: '{query}' (max={max_results}, region={region})")
            results = await asyncio.to_thread(
                _ddg_search_sync, query, max_results, region
            )

        logger.info(f"🔎 '{query}' → {len(results)} résultat(s)")
        return results

    async def search_images(
        self,
        query: str,
        max_results: int = 5,
        region: str = "fr-fr"
    ) -> List[Dict[str, Any]]:
        """
        Recherche d'images — fallback vers la librairie duckduckgo_search.
        """
        await asyncio.sleep(random.uniform(0.5, 2.0))

        def _sync():
            try:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    return list(ddgs.images(
                        keywords=query,
                        region=region,
                        safesearch='moderate',
                        max_results=max_results,
                    ))
            except Exception as e:
                logger.warning(f"DDG images échoué pour '{query}': {e}")
                return []

        results = await asyncio.to_thread(_sync)
        logger.info(f"🖼️ DDG images '{query}' → {len(results)} résultat(s)")
        return results

    def format_search_results_for_llm(
        self,
        results: List[Dict[str, Any]],
        search_type: str = "text"
    ) -> str:
        """Formate les résultats pour injection dans le contexte LLM."""
        if not results:
            return "Aucun résultat trouvé."

        formatted = []
        if search_type == "text":
            for i, result in enumerate(results, 1):
                formatted.append(
                    f"{i}. **{result.get('title', 'Sans titre')}**\n"
                    f"   {result.get('body', '')}\n"
                    f"   Source: {result.get('href', '')}\n"
                )
        elif search_type == "images":
            for i, result in enumerate(results, 1):
                formatted.append(
                    f"{i}. {result.get('title', 'Image sans description')}\n"
                    f"   Image: {result.get('image', '')}\n"
                    f"   Source: {result.get('url', '')}\n"
                )
        return "\n".join(formatted)

    async def search_for_project_references(
        self,
        project_description: str,
        project_type: str = "creative"
    ) -> str:
        """Recherche contextuelle pour un projet créatif."""
        if "carte" in project_description.lower() or "design" in project_description.lower():
            query = f"{project_description} design inspiration tendances 2025"
        elif "canvas" in project_description.lower() or "animation" in project_description.lower():
            query = f"{project_description} creative coding examples"
        else:
            query = f"{project_description} exemples inspirations"

        text_results = await self.search_text(query, max_results=3)
        if not text_results:
            return ""

        formatted = "**Références trouvées sur le web:**\n\n"
        formatted += self.format_search_results_for_llm(text_results, "text")
        return formatted
