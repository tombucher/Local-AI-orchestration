"""
Module de recherche web générique

Responsabilités :
- Scraping de pages web (HTTP, RSS)
- Extraction de données structurées
- Recherche multi-sources
- Gestion des APIs externes
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup
import feedparser

from app.core.config import settings as app_settings

logger = logging.getLogger(__name__)



def _image_d_entree(entry) -> Optional[str]:
    """Vignette d'une entrée RSS, sans télécharger la page de l'article.

    Mesuré sur les flux configurés : Reporterre, Hyperallergic et Colossal en
    fournissent une pour la quasi-totalité de leurs entrées, tantôt en
    `media:content`, tantôt par une balise <img> dans le résumé.
    """
    for media in (entry.get("media_content") or []):
        url = media.get("url")
        if url and (str(media.get("type", "")).startswith("image")
                    or url.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif"))):
            return url
    for thumb in (entry.get("media_thumbnail") or []):
        if thumb.get("url"):
            return thumb["url"]
    html = (entry.get("content") or [{}])[0].get("value") or entry.get("summary", "")
    balise = BeautifulSoup(html, "html.parser").find("img") if html else None
    src = balise.get("src") if balise else None
    return src if src and src.startswith("http") else None


class WebResearchModule:
    """
    Module de recherche web réutilisable

    Utilisable pour :
    - Veille technologique (GitHub, Stack Overflow, HN)
    - Recherche de financements (data.gouv.fr, portails publics)
    - Veille culturelle (festivals, expositions)
    - Recherche académique (arXiv, HAL)
    """

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.default_headers = {
            'User-Agent': 'OrchestrateurIA/1.0 (Research Bot)',
            'Accept': 'text/html,application/json,application/rss+xml'
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.default_headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    _BLOCKED_HOSTS = ("localhost", "host.docker.internal", "postgres", "backend", "frontend", "ollama")

    @staticmethod
    def _is_safe_url(url: str) -> bool:
        """Anti-SSRF : uniquement http(s) vers des hôtes publics. Les URLs viennent
        de résultats de recherche externes ; le backend Docker voit host.docker.internal,
        Ollama, Postgres… qu'il ne doit jamais requêter pour le compte d'une page."""
        import ipaddress
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
        except Exception:
            return False
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        host = parsed.hostname.lower()
        if host in WebResearchModule._BLOCKED_HOSTS or host.endswith((".internal", ".local", ".localhost")):
            return False
        try:
            ip = ipaddress.ip_address(host)
            return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast)
        except ValueError:
            return True  # nom de domaine public

    async def fetch_url(self, url: str, timeout: int = 30) -> str:
        """
        Récupère le contenu d'une URL

        Args:
            url: URL à récupérer
            timeout: Timeout en secondes

        Returns:
            Contenu HTML/JSON de la page
        """
        if not self.session:
            raise RuntimeError("Use 'async with' to create session")
        if not self._is_safe_url(url):
            raise ValueError(f"URL refusée (schéma ou hôte interne) : {url}")

        try:
            async with self.session.get(url, timeout=timeout, max_redirects=5) as response:
                response.raise_for_status()
                if not self._is_safe_url(str(response.url)):
                    raise ValueError(f"Redirection vers un hôte interne refusée : {response.url}")
                content = await response.text()
                logger.info(f"✓ Fetched {url} ({len(content)} chars)")
                return content
        except Exception as e:
            logger.error(f"✗ Failed to fetch {url}: {e}")
            raise

    async def fetch_page_text(self, url: str, max_chars: int = 4000, timeout: int = 20) -> str:
        """
        Récupère une page et en extrait le texte brut (sans balises),
        tronqué à max_chars. Pour l'extraction LLM (deadlines, montants...).
        """
        try:
            html = await self.fetch_url(url, timeout=timeout)
        except Exception:
            return ""
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        text = ' '.join(soup.get_text(separator=' ').split())
        return text[:max_chars]

    async def search_aides_territoires(
        self,
        keywords: List[str],
        api_key: Optional[str] = None,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Recherche d'aides publiques sur l'API Aides-Territoires (beta.gouv.fr).
        Nécessite une clé API gratuite (https://aides-territoires.beta.gouv.fr/api/).
        Sans clé, retourne [] silencieusement.
        """
        if not api_key:
            logger.info("Aides-Territoires: pas de clé API configurée, recherche ignorée")
            return []
        if not self.session:
            raise RuntimeError("Use 'async with' to create session")

        base = "https://aides-territoires.beta.gouv.fr"
        try:
            # 1. Échanger la clé API contre un JWT
            async with self.session.post(
                f"{base}/api/connexion/",
                headers={"X-AUTH-TOKEN": api_key},
                timeout=15,
            ) as resp:
                resp.raise_for_status()
                token = (await resp.json()).get("token")
            if not token:
                logger.warning("Aides-Territoires: pas de token dans la réponse")
                return []

            # 2. Rechercher les aides
            query = " ".join(keywords[:5])
            async with self.session.get(
                f"{base}/api/aids/",
                params={"text": query, "page_size": max_results},
                headers={"Authorization": f"Bearer {token}"},
                timeout=20,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

            results = []
            for aid in data.get("results", []):
                results.append({
                    "title": aid.get("name", "Sans titre"),
                    "url": aid.get("url") or f"{base}{aid.get('slug', '')}",
                    "description": (aid.get("description") or "")[:1000],
                    "source_platform": "Aides-Territoires",
                    "deadline": aid.get("submission_deadline"),  # YYYY-MM-DD ou None
                    "financers": aid.get("financers", []),
                })
            logger.info(f"✓ Aides-Territoires: {len(results)} aides pour '{query}'")
            return results
        except Exception as e:
            logger.warning(f"Aides-Territoires search failed: {e}")
            return []

    # ------------------------------------------------------------------
    # Sources d'images libres (veille visuelle / moodboard) — sans clé API
    # ------------------------------------------------------------------

    # Openverse refuse page_size > 20 en anonyme (401 « may not exceed 20 »)
    OPENVERSE_ANON_MAX = 20

    async def search_openverse(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Openverse (openverse.org) : agrégateur d'images sous licence libre.

        C'est la seule source réellement interrogeable du lot : les APIs musée
        retombent sur leur fonds classique dès que la requête en sort.
        """
        try:
            async with self.session.get(
                "https://api.openverse.org/v1/images/",
                params={"q": query, "page_size": min(max_results, self.OPENVERSE_ANON_MAX)},
                headers={"User-Agent": "OrchestratorIA/1.0 (veille personnelle)"},
                timeout=20,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
            results = []
            for img in data.get("results", []):
                if not img.get("url"):
                    continue
                results.append({
                    "title": img.get("title") or "Sans titre",
                    "url": img.get("foreign_landing_url") or img.get("url"),
                    "image_url": img.get("url"),
                    "thumbnail_url": img.get("thumbnail") or img.get("url"),
                    "license": f"{img.get('license', '')} {img.get('license_version', '')}".strip().upper(),
                    "description": img.get("attribution") or "",
                    "source_platform": "Openverse",
                })
            logger.info(f"✓ Openverse: {len(results)} images pour '{query}'")
            return results
        except Exception as e:
            logger.warning(f"Openverse search failed for '{query}': {e}")
            return []

    async def search_aic(self, query: str, max_results: int = 8) -> List[Dict[str, Any]]:
        """Art Institute of Chicago : œuvres d'art en accès libre (IIIF)."""
        try:
            async with self.session.get(
                "https://api.artic.edu/api/v1/artworks/search",
                params={
                    "q": query,
                    "limit": max_results,
                    "fields": "id,title,image_id,artist_display,date_display",
                },
                timeout=20,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
            results = []
            for art in data.get("data", []):
                image_id = art.get("image_id")
                if not image_id:
                    continue
                iiif = f"https://www.artic.edu/iiif/2/{image_id}"
                results.append({
                    "title": art.get("title") or "Sans titre",
                    "url": f"https://www.artic.edu/artworks/{art.get('id')}",
                    "image_url": f"{iiif}/full/843,/0/default.jpg",
                    "thumbnail_url": f"{iiif}/full/400,/0/default.jpg",
                    "license": "CC0 / domaine public",
                    "description": " — ".join(filter(None, [art.get("artist_display"), art.get("date_display")])),
                    "source_platform": "Art Institute of Chicago",
                })
            logger.info(f"✓ AIC: {len(results)} œuvres pour '{query}'")
            return results
        except Exception as e:
            logger.warning(f"AIC search failed for '{query}': {e}")
            return []

    async def search_met(self, query: str, max_results: int = 6) -> List[Dict[str, Any]]:
        """Met Museum (Open Access). API en deux temps : recherche d'IDs puis détails."""
        try:
            async with self.session.get(
                "https://collectionapi.metmuseum.org/public/collection/v1/search",
                params={"q": query, "hasImages": "true"},
                timeout=20,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
            object_ids = (data.get("objectIDs") or [])[:max_results]

            async def _fetch_object(oid: int) -> Optional[Dict[str, Any]]:
                try:
                    async with self.session.get(
                        f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}",
                        timeout=15,
                    ) as r:
                        r.raise_for_status()
                        obj = await r.json()
                    if not obj.get("primaryImageSmall"):
                        return None
                    return {
                        "title": obj.get("title") or "Sans titre",
                        "url": obj.get("objectURL", ""),
                        "image_url": obj.get("primaryImage") or obj.get("primaryImageSmall"),
                        "thumbnail_url": obj.get("primaryImageSmall"),
                        "license": "Open Access (CC0)" if obj.get("isPublicDomain") else "Droits réservés",
                        "description": " — ".join(filter(None, [obj.get("artistDisplayName"), obj.get("objectDate")])),
                        "source_platform": "Met Museum",
                    }
                except Exception:
                    return None

            objects = await asyncio.gather(*[_fetch_object(oid) for oid in object_ids])
            results = [o for o in objects if o]
            logger.info(f"✓ Met Museum: {len(results)} œuvres pour '{query}'")
            return results
        except Exception as e:
            logger.warning(f"Met search failed for '{query}': {e}")
            return []

    async def search_wikimedia_commons(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Wikimedia Commons : images libres (licence lue dans les métadonnées)."""
        try:
            async with self.session.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query", "format": "json", "generator": "search",
                    "gsrsearch": query, "gsrnamespace": 6, "gsrlimit": max_results,
                    "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 480,
                },
                headers={"User-Agent": "OrchestratorIA/1.0 (veille personnelle)"},
                timeout=20,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
            results = []
            for page in (data.get("query", {}).get("pages", {}) or {}).values():
                info = (page.get("imageinfo") or [{}])[0]
                url = info.get("url")
                # Les URLs Commons portent une chaîne de requête (utm_…) : tester le chemin seul
                if not url or not url.split("?")[0].lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
                    continue
                meta = info.get("extmetadata", {}) or {}
                title = (meta.get("ObjectName", {}) or {}).get("value") or page.get("title", "").replace("File:", "")
                artist = BeautifulSoup((meta.get("Artist", {}) or {}).get("value", ""), "html.parser").get_text(" ", strip=True)
                results.append({
                    "title": title[:200],
                    "url": info.get("descriptionurl") or url,
                    "image_url": url,
                    "thumbnail_url": info.get("thumburl") or url,
                    "license": (meta.get("LicenseShortName", {}) or {}).get("value", "Commons"),
                    "description": artist,
                    "source_platform": "Wikimedia Commons",
                })
            logger.info(f"✓ Wikimedia Commons: {len(results)} images pour '{query}'")
            return results
        except Exception as e:
            logger.warning(f"Wikimedia Commons search failed for '{query}': {e}")
            return []

    # Flux RSS de blogs design/art dont les entrées exposent des images
    # Flux vérifiés le 20/09/2026 (entrées + images présentes).
    # CreativeApplications retiré : le flux ne sert plus qu'une entrée « RSS Feed Inactive ».
    DEFAULT_DESIGN_FEEDS = [
        "https://www.thisiscolossal.com/feed/",
        "https://www.designboom.com/feed/",
        "https://hyperallergic.com/feed/",
        "https://www.dezeen.com/feed/",
    ]

    # Catalogue de flux vérifiés le 20/09/2026 (HTTP 200 + entrées présentes).
    # Chaque flux est étiqueté FR/EN : on choisit les sources d'après le SUJET de la
    # veille, pas d'après sa catégorie — un sujet « typographie » classé en « news »
    # doit recevoir des flux design, pas des flux climat.
    FEED_CATALOGUE: List[Dict[str, Any]] = [
        {"url": "https://www.thisiscolossal.com/feed/", "tags": [
            "art", "installation", "sculpture", "exposition", "craft", "artiste"]},
        {"url": "https://hyperallergic.com/feed/", "tags": [
            "art", "exposition", "musée", "museum", "artiste", "critique"]},
        {"url": "https://www.dezeen.com/feed/", "tags": [
            "design", "architecture", "graphisme", "objet", "mobilier"]},
        {"url": "https://we-make-money-not-art.com/feed/", "tags": [
            "art", "numérique", "digital", "interactive", "technologie", "critique",
            "generative", "génératif", "code", "creative coding"]},
        {"url": "https://www.creativebloq.com/feeds/all", "tags": [
            "design", "graphisme", "typographie", "typography", "police", "font",
            "poster", "affiche", "illustration", "identité"]},
        {"url": "https://hnrss.org/frontpage", "tags": [
            "tech", "code", "logiciel", "software", "développement", "open source"]},
        {"url": "https://theconversation.com/fr/environnement/articles.atom", "tags": [
            "écologie", "environnement", "climat", "science", "recherche"]},
        {"url": "https://reporterre.net/spip.php?page=backend", "tags": [
            "écologie", "environnement", "climat", "politique", "transition"]},
        {"url": "https://www.carbonbrief.org/feed/", "tags": [
            "climat", "climate", "carbone", "énergie", "energy"]},
        {"url": "https://news.mongabay.com/feed/", "tags": [
            "biodiversité", "forêt", "nature", "conservation", "environnement"]},
        {"url": "https://e360.yale.edu/feed.xml", "tags": [
            "environnement", "climat", "nature", "pollution"]},
        {"url": "https://insideclimatenews.org/feed/", "tags": [
            "climat", "climate", "énergie", "pollution"]},
        {"url": "https://www.terrestres.org/feed/", "tags": [
            "écologie", "politique", "transition", "critique"]},
        {"url": "https://theecologist.org/rss", "tags": [
            "écologie", "environnement", "nature"]},
        {"url": "https://www.nature.com/nclimate.rss", "tags": [
            "climat", "climate", "science", "recherche", "académique"]},
    ]

    # Complément quand trop peu de flux correspondent au sujet : larges et
    # toujours pertinents pour un profil art numérique + design.
    GENERALIST_TOPUP: List[str] = [
        "https://www.thisiscolossal.com/feed/",
        "https://hyperallergic.com/feed/",
        "https://www.creativebloq.com/feeds/all",
        "https://we-make-money-not-art.com/feed/",
        "https://www.dezeen.com/feed/",
    ]

    # Repli quand aucune étiquette ne correspond au sujet
    DEFAULT_ARTICLE_FEEDS: Dict[str, List[str]] = {
        "tech": ["https://hnrss.org/frontpage",
                 "https://we-make-money-not-art.com/feed/",
                 "https://www.creativebloq.com/feeds/all"],
        "cultural": ["https://www.thisiscolossal.com/feed/",
                     "https://hyperallergic.com/feed/",
                     "https://www.dezeen.com/feed/"],
        "news": ["https://theconversation.com/fr/environnement/articles.atom",
                 "https://reporterre.net/spip.php?page=backend",
                 "https://www.thisiscolossal.com/feed/"],
        "academic": ["https://www.nature.com/nclimate.rss",
                     "https://theconversation.com/fr/environnement/articles.atom"],
    }

    @classmethod
    def select_feeds(cls, terms: Optional[List[str]] = None, scope: str = "news",
                     limit: int = 6,
                     user_feeds: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        """Choisit les flux dont les étiquettes recoupent le sujet de la veille.

        `user_feeds` est la bibliothèque personnelle ({url, tags}) : à correspondance
        égale elle passe devant le catalogue intégré, puisque c'est l'utilisateur qui
        a jugé ces sources dignes d'intérêt.
        """
        fallback = cls.DEFAULT_ARTICLE_FEEDS.get(scope, cls.DEFAULT_ARTICLE_FEEDS["news"])
        haystack = ' '.join(t.casefold() for t in (terms or []))
        if not haystack:
            personal = [f["url"] for f in (user_feeds or [])][:limit]
            return personal or fallback[:limit]

        scored = []
        for feed in (user_feeds or []):
            hits = sum(1 for tag in (feed.get("tags") or []) if str(tag).casefold() in haystack)
            if hits:
                scored.append((hits + 0.5, feed["url"]))  # bonus : source choisie par l'utilisateur
        for feed in cls.FEED_CATALOGUE:
            hits = sum(1 for tag in feed["tags"] if tag in haystack)
            if hits:
                scored.append((hits, feed["url"]))
        if not scored:
            # Sujet hors catalogue : les flux perso d'abord, sinon le défaut du scope
            personal = [f["url"] for f in (user_feeds or [])][:limit]
            return personal or fallback[:limit]

        scored.sort(key=lambda x: -x[0])
        chosen: List[str] = []
        for _, url in scored:           # un flux peut être à la fois perso et au catalogue
            if url not in chosen:
                chosen.append(url)
            if len(chosen) >= limit:
                break

        # Les flux ne sont pas interrogeables : on ne lit que leurs dernières
        # entrées. Trop peu de sources = récolte quasi nulle, donc on complète —
        # avec les généralistes art/design plutôt qu'avec le défaut du scope, qui
        # collerait des flux climat sur un sujet typographie.
        for url in cls.GENERALIST_TOPUP:
            if len(chosen) >= max(3, min(limit, 4)):
                break
            if url not in chosen:
                chosen.append(url)
        return chosen[:limit]

    async def search_rss_articles(
        self,
        terms: Optional[List[str]] = None,
        feeds: Optional[List[str]] = None,
        scope: str = "news",
        max_per_feed: int = 8,
        exclude_urls: Optional[set] = None,
        min_results: int = 8,
        max_results: int = 14,
        user_feeds: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Articles issus de flux RSS/Atom, filtrés par mots-clés.

        Alternative gratuite et fiable à DuckDuckGo (403 fréquents) et à Brave
        (payant). Les flux ne sont pas interrogeables : on récupère les dernières
        entrées et on filtre localement, comme le fait l'outil OpenWebUI maison.
        """
        urls = [f for f in (feeds or self.select_feeds(terms, scope, user_feeds=user_feeds))
                if str(f).startswith("http")]
        if not urls:
            return []

        lowered = [t.casefold() for t in (terms or []) if t and len(t) > 2]
        already = exclude_urls or set()

        # Chaque flux renvoie (entrées correspondant aux termes, entrées récentes brutes)
        spares: List[List[Dict[str, Any]]] = []

        async def _one(feed_url: str) -> List[Dict[str, Any]]:
            try:
                raw = await self.fetch_url(feed_url, timeout=15)
            except Exception as e:
                logger.warning(f"Flux RSS injoignable {feed_url}: {e}")
                return []
            parsed = feedparser.parse(raw)
            source_name = (parsed.feed.get("title") or feed_url)[:100]
            found: List[Dict[str, Any]] = []
            spare: List[Dict[str, Any]] = []
            for entry in parsed.entries[:40]:
                link = (entry.get("link") or "").strip()
                if not link or link in already:
                    continue  # Anti-doublon : déjà vu lors d'un scan précédent
                title = BeautifulSoup(entry.get("title", ""), "html.parser").get_text(" ", strip=True)
                summary = BeautifulSoup(
                    entry.get("summary", "") or (entry.get("content") or [{}])[0].get("value", ""),
                    "html.parser",
                ).get_text(" ", strip=True)[:600]
                item = {
                    "title": title[:300] or "Sans titre",
                    "url": link,
                    "description": summary,
                    "source_platform": source_name,
                    "published": entry.get("published") or entry.get("updated") or "",
                    "image": _image_d_entree(entry),
                }
                if lowered and not any(t in f"{title} {summary}".casefold() for t in lowered):
                    if len(spare) < max_per_feed:
                        spare.append(item)
                    continue
                found.append(item)
                if len(found) >= max_per_feed:
                    break
            spares.append(spare)
            return found

        # Concurrence bridée : le résolveur DNS du conteneur sature au-delà
        gate = asyncio.Semaphore(4)

        async def _guarded(feed_url: str):
            async with gate:
                return await _one(feed_url)

        batches = await asyncio.gather(*(_guarded(u) for u in urls), return_exceptions=True)
        valid = [b for b in batches if isinstance(b, list)]
        results = [item for batch in valid for item in batch]

        # Un filtre lexical strict sur un sujet pointu ne laisse presque rien passer
        # et affame l'analyse de pertinence LLM qui suit. En dessous du seuil, on
        # complète avec les dernières entrées non filtrées : c'est le modèle qui tranche.
        if lowered and len(results) < min_results:
            seen = {r["url"] for r in results}
            filler = [
                item for batch in spares for item in batch
                if item["url"] not in seen and item["url"] not in already
            ]
            results += filler[: max_results - len(results)]
            logger.info(f"📰 RSS : filtre trop étroit ({len(seen)} articles), "
                        f"complété à {len(results)} pour laisser l'IA trancher")

        results = results[:max_results]
        logger.info(f"📰 RSS ({scope}) : {len(results)} articles depuis {len(urls)} flux")
        return results

    # Pexels : API officielle, clé gratuite, licence permissive (usage libre y
    # compris commercial). Seule source du lot dont les images sont réellement
    # réutilisables sans vérifier les droits au cas par cas.
    #
    # Unsplash a été envisagé puis écarté : ses règles réservent l'API à des
    # usages « non-automated », imposent de déclencher `links.download_location`
    # à chaque sélection d'image et une attribution par lien profil avec UTM —
    # incompatible avec une veille programmée. Pexels, lui, autorise
    # l'automatisation (200 req/h) contre un lien visible et le crédit photographe.
    PEXELS_SEARCH = "https://api.pexels.com/v1/search"

    async def search_pexels(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Photographies Pexels. Nécessite `PEXELS_API_KEY` (gratuite)."""
        cle = getattr(app_settings, "PEXELS_API_KEY", "") or ""
        if not cle:
            return []
        try:
            async with self.session.get(
                self.PEXELS_SEARCH,
                params={"query": query, "per_page": min(max_results, 80)},
                headers={"Authorization": cle},
                timeout=20,
            ) as resp:
                if resp.status == 401:
                    logger.error("Pexels refuse la clé (401) — vérifier PEXELS_API_KEY")
                    return []
                resp.raise_for_status()
                data = await resp.json()
        except Exception as e:
            logger.warning(f"Pexels search failed for '{query}': {e}")
            return []

        results = []
        for photo in (data.get("photos") or [])[:max_results]:
            src = photo.get("src") or {}
            apercu = src.get("medium") or src.get("small") or src.get("tiny")
            if not apercu:
                continue
            auteur = (photo.get("photographer") or "").strip()
            results.append({
                "title": (photo.get("alt") or f"Photo de {auteur}" or "Sans titre")[:200],
                "url": photo.get("url") or "https://www.pexels.com",
                "image_url": src.get("large") or src.get("original") or apercu,
                "thumbnail_url": apercu,
                # Pexels exige un lien visible vers Pexels et le crédit du
                # photographe : les deux figurent dans la licence affichée, et
                # `url` pointe vers la page Pexels de la photo.
                "license": (f"Photo de {auteur} sur Pexels — libre d'usage"
                            if auteur else "Pexels — libre d'usage"),
                "description": f"Pexels · {query}",
                "source_platform": "Pexels",
            })
        logger.info(f"✓ Pexels: {len(results)} images pour '{query}'")
        return results

    # Internet Archive : API de recherche publique et documentée, sans clé.
    # Évaluée le 21/09/2026 sur des requêtes d'art numérique : 62 % d'images
    # jugées pertinentes par le modèle vision, médiane 90 — de loin le meilleur
    # rendement du lot (les APIs musée plafonnaient à 3 %).
    ARCHIVE_SEARCH = "https://archive.org/advancedsearch.php"
    ARCHIVE_THUMB = "https://archive.org/services/img/"

    async def search_internet_archive(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Images d'Internet Archive : documents imprimés, tickets, matériel ancien.

        ⚠️ Les droits varient d'un dépôt à l'autre : à traiter comme des
        références, pas comme des visuels réutilisables sans vérification.
        """
        params = {
            "q": f"{query} AND mediatype:image",
            "fl[]": "identifier",
            "rows": str(max_results),
            "output": "json",
        }
        try:
            async with self.session.get(
                self.ARCHIVE_SEARCH, params=params,
                headers={"User-Agent": "OrchestratorIA/1.0 (veille personnelle)"},
                timeout=25,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except Exception as e:
            logger.warning(f"Internet Archive search failed for '{query}': {e}")
            return []

        results = []
        for doc in (data.get("response", {}).get("docs") or [])[:max_results]:
            identifiant = doc.get("identifier")
            if not identifiant:
                continue
            vignette = f"{self.ARCHIVE_THUMB}{identifiant}"
            results.append({
                # Les identifiants sont opaques (« dauzuk-papierki-18-001 ») : la
                # notation par vision leur donnera une description lisible.
                "title": identifiant.replace("-", " ").replace("_", " ")[:200],
                "url": f"https://archive.org/details/{identifiant}",
                "image_url": vignette,
                "thumbnail_url": vignette,
                "license": "Internet Archive — droits variables selon le dépôt",
                "description": f"Internet Archive · {query}",
                "source_platform": "Internet Archive",
            })
        logger.info(f"✓ Internet Archive: {len(results)} images pour '{query}'")
        return results

    # Are.na : /v2/search/blocks renvoie 403 pour tout le monde (blocage anti-bot).
    # On passe donc par les *channels*, ce qui vaut mieux : ce sont des collections
    # curatées par des humains, exactement la matière d'un moodboard.
    ARENA_API = "https://api.are.na/v2"

    async def search_arena(
        self,
        query: str,
        max_channels: int = 3,
        per_channel: int = 8,
    ) -> List[Dict[str, Any]]:
        """Références visuelles depuis Are.na (collections curatées art/design).

        ⚠️ Contrairement aux autres sources, les images Are.na ne sont PAS libres de
        droits : ce sont des références rassemblées par des utilisateurs depuis tout
        le web. À utiliser comme inspiration, jamais comme visuel réutilisable.
        """
        token = getattr(app_settings, "ARENA_ACCESS_TOKEN", "") or ""
        headers = {"User-Agent": "OrchestratorIA/1.0 (veille personnelle)", "Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with self.session.get(
                f"{self.ARENA_API}/search/channels",
                params={"q": query, "per": max_channels},
                headers=headers,
                timeout=20,
            ) as resp:
                resp.raise_for_status()
                channels = (await resp.json()).get("channels", []) or []
        except Exception as e:
            logger.warning(f"Are.na channel search failed for '{query}': {e}")
            return []

        results: List[Dict[str, Any]] = []
        for channel in channels:
            slug = channel.get("slug")
            if not slug or not channel.get("length"):
                continue
            channel_title = channel.get("title") or slug
            try:
                async with self.session.get(
                    f"{self.ARENA_API}/channels/{slug}/contents",
                    params={"per": per_channel, "direction": "desc"},
                    headers=headers,
                    timeout=20,
                ) as resp:
                    resp.raise_for_status()
                    blocks = (await resp.json()).get("contents", []) or []
            except Exception as e:
                logger.warning(f"Are.na contents failed for '{slug}': {e}")
                continue

            for block in blocks:
                image = (block.get("image") or {})
                display = (image.get("display") or {}).get("url")
                if not display:
                    continue
                block_title = block.get("title") or block.get("generated_title") or channel_title
                results.append({
                    # Le titre d'un bloc est souvent un nom de fichier : c'est le nom
                    # du channel qui porte le sens, donc il va dans la description
                    # pour que la notation de pertinence puisse s'y accrocher.
                    "title": str(block_title)[:200],
                    # `source` vaut null sur les blocs téléversés directement
                    "url": (block.get("source") or {}).get("url") or f"https://www.are.na/block/{block.get('id')}",
                    "image_url": display,
                    "thumbnail_url": (image.get("thumb") or {}).get("url") or display,
                    "license": "Are.na — référence, droits non vérifiés",
                    "description": f"Collection Are.na « {channel_title} »",
                    "source_platform": "Are.na",
                })

        logger.info(f"✓ Are.na: {len(results)} images pour '{query}' ({len(channels)} collections)")
        return results

    async def search_rss_images(
        self,
        keywords: List[str],
        feeds: Optional[List[str]] = None,
        max_per_feed: int = 6,
    ) -> List[Dict[str, Any]]:
        """Images des flux RSS design dont l'entrée mentionne un des mots-clés
        (les flux ne sont pas interrogeables : on filtre les dernières entrées)."""
        feeds = [f for f in (feeds or self.DEFAULT_DESIGN_FEEDS) if f.startswith("http")]
        terms = [k.casefold() for k in keywords if k]
        results: List[Dict[str, Any]] = []

        async def _one(feed_url: str) -> List[Dict[str, Any]]:
            try:
                raw = await self.fetch_url(feed_url, timeout=15)
            except Exception:
                return []
            parsed = feedparser.parse(raw)
            found = []
            for entry in parsed.entries[:40]:
                text = f"{entry.get('title', '')} {entry.get('summary', '')}".casefold()
                if terms and not any(t in text for t in terms):
                    continue
                image = None
                for media in entry.get("media_content", []) or []:
                    if str(media.get("type", "")).startswith("image") or media.get("url", "").lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                        image = media.get("url"); break
                if not image:
                    thumbs = entry.get("media_thumbnail", []) or []
                    image = thumbs[0].get("url") if thumbs else None
                if not image:
                    html = (entry.get("content") or [{}])[0].get("value") or entry.get("summary", "")
                    img = BeautifulSoup(html, "html.parser").find("img")
                    image = img.get("src") if img else None
                if not image:
                    continue
                found.append({
                    "title": entry.get("title", "Sans titre")[:200],
                    "url": entry.get("link", feed_url),
                    "image_url": image,
                    "thumbnail_url": image,
                    "license": "Droits réservés (blog)",
                    "description": BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(" ", strip=True)[:300],
                    "source_platform": parsed.feed.get("title", feed_url)[:60],
                })
                if len(found) >= max_per_feed:
                    break
            return found

        batches = await asyncio.gather(*[_one(f) for f in feeds])
        for b in batches:
            results.extend(b)
        logger.info(f"✓ RSS design: {len(results)} images ({len(feeds)} flux)")
        return results

    async def search_visual_references(
        self,
        queries: List[str],
        max_total: int = 40,
        keywords: Optional[List[str]] = None,
        feeds: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Recherche parallèle de références visuelles sur toutes les sources libres
        (Openverse, Art Institute of Chicago, Met, Wikimedia Commons, flux RSS design),
        dédoublonnée par image_url."""
        # Rendement mesuré le 20/09/2026 sur une requête d'art numérique :
        # Openverse ~seule source utile, AIC ~3 %, Met 0 %, Wikimedia coupe en 429
        # dès qu'on l'interroge en parallèle. D'où ce dosage.
        factories = []
        # Openverse est la seule source vraiment interrogeable : on lui donne
        # toutes les requêtes, les autres n'en reçoivent que les premières.
        for q in queries[:4]:
            factories.append(lambda q=q: self.search_openverse(q))
        for q in queries[:2]:
            factories += [lambda q=q: self.search_aic(q), lambda q=q: self.search_met(q)]
        if queries:
            factories.append(lambda: self.search_wikimedia_commons(queries[0]))
        # Internet Archive : meilleur rendement mesuré, et sans clé
        for q in queries[:3]:
            factories.append(lambda q=q: self.search_internet_archive(q))
        # Pexels : ignoré silencieusement si la clé n'est pas configurée
        if getattr(app_settings, "PEXELS_API_KEY", ""):
            for q in queries[:2]:
                factories.append(lambda q=q: self.search_pexels(q))
        # Are.na : la meilleure source pour l'art numérique contemporain, mais
        # deux appels par requête — on la limite aux deux premières.
        if getattr(app_settings, "ARENA_ACCESS_TOKEN", ""):
            for q in queries[:2]:
                factories.append(lambda q=q: self.search_arena(q))
        factories.append(lambda: self.search_rss_images(keywords or queries, feeds))

        # Une douzaine de requêtes simultanées saturait le résolveur DNS du conteneur
        # (« Temporary failure in name resolution » sur des hôtes pourtant valides).
        gate = asyncio.Semaphore(4)

        async def _guarded(make):
            async with gate:
                return await make()

        batches = await asyncio.gather(*(_guarded(f) for f in factories), return_exceptions=True)
        for batch in batches:
            if isinstance(batch, Exception):
                logger.warning(f"Source visuelle en échec : {type(batch).__name__}: {batch}")
        batches = [b for b in batches if isinstance(b, list)]

        # Tour de rôle entre les sources pour qu'aucune n'écrase les autres
        # quand on plafonne à max_total
        seen = set()
        results: List[Dict[str, Any]] = []
        queues = [list(b) for b in batches if b]
        while queues and len(results) < max_total:
            for q in list(queues):
                if not q:
                    queues.remove(q)
                    continue
                r = q.pop(0)
                key = r.get("image_url")
                if key and key not in seen:
                    seen.add(key)
                    results.append(r)
                    if len(results) >= max_total:
                        break
        return results

    async def scrape_html(self, url: str, selectors: Dict[str, str]) -> Dict[str, Any]:
        """
        Scrape une page HTML avec des sélecteurs CSS

        Args:
            url: URL à scraper
            selectors: Dict de sélecteurs CSS {"field_name": "css.selector"}

        Returns:
            Dict avec les données extraites

        Example:
            selectors = {
                "title": "h1.title",
                "description": "div.description",
                "date": "span.date"
            }
        """
        html = await self.fetch_url(url)
        soup = BeautifulSoup(html, 'html.parser')

        result = {"url": url, "scraped_at": datetime.utcnow().isoformat()}

        for field, selector in selectors.items():
            element = soup.select_one(selector)
            if element:
                result[field] = element.get_text(strip=True)
            else:
                result[field] = None
                logger.warning(f"Selector '{selector}' not found for field '{field}'")

        return result

    async def scrape_multiple(
        self,
        urls: List[str],
        selectors: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Scrape plusieurs URLs en parallèle

        Args:
            urls: Liste d'URLs
            selectors: Sélecteurs CSS communs

        Returns:
            Liste de résultats
        """
        import asyncio

        tasks = [self.scrape_html(url, selectors) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to scrape {urls[i]}: {result}")
            else:
                valid_results.append(result)

        return valid_results

    async def fetch_rss_feed(self, feed_url: str) -> List[Dict[str, Any]]:
        """
        Récupère un flux RSS/Atom

        Args:
            feed_url: URL du flux RSS

        Returns:
            Liste d'entrées du flux
        """
        content = await self.fetch_url(feed_url)
        feed = feedparser.parse(content)

        entries = []
        for entry in feed.entries:
            entries.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "description": entry.get("summary", entry.get("description", "")),
                "published": entry.get("published", entry.get("updated", "")),
                "author": entry.get("author", ""),
                "tags": [tag.term for tag in entry.get("tags", [])]
            })

        logger.info(f"✓ Fetched {len(entries)} entries from RSS feed")
        return entries

    async def search_github(
        self,
        keywords: List[str],
        language: Optional[str] = None,
        min_stars: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Recherche sur GitHub

        Args:
            keywords: Mots-clés de recherche
            language: Langage de programmation (optionnel)
            min_stars: Nombre minimum d'étoiles

        Returns:
            Liste de repositories
        """
        # Construction de la requête
        query = " ".join(keywords)
        if language:
            query += f" language:{language}"
        if min_stars > 0:
            query += f" stars:>={min_stars}"

        api_url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=20"

        try:
            content = await self.fetch_url(api_url)
            import json
            data = json.loads(content)

            results = []
            for item in data.get("items", []):
                results.append({
                    "title": item["full_name"],
                    "url": item["html_url"],
                    "description": item.get("description", ""),
                    "stars": item["stargazers_count"],
                    "language": item.get("language", ""),
                    "last_update": item["updated_at"],
                    "topics": item.get("topics", [])
                })

            logger.info(f"✓ Found {len(results)} GitHub repos for '{query}'")
            return results

        except Exception as e:
            logger.error(f"GitHub search failed: {e}")
            return []

    async def search_hackernews(self, keywords: List[str], days: int = 7) -> List[Dict[str, Any]]:
        """
        Recherche sur Hacker News via Algolia API

        Args:
            keywords: Mots-clés
            days: Nombre de jours dans le passé

        Returns:
            Liste d'articles HN
        """
        query = " ".join(keywords)
        api_url = f"https://hn.algolia.com/api/v1/search?query={query}&tags=story&hitsPerPage=20"

        try:
            content = await self.fetch_url(api_url)
            import json
            data = json.loads(content)

            results = []
            for hit in data.get("hits", []):
                results.append({
                    "title": hit.get("title", ""),
                    "url": hit.get("url", f"https://news.ycombinator.com/item?id={hit['objectID']}"),
                    "points": hit.get("points", 0),
                    "num_comments": hit.get("num_comments", 0),
                    "author": hit.get("author", ""),
                    "created_at": hit.get("created_at", "")
                })

            logger.info(f"✓ Found {len(results)} HN stories for '{query}'")
            return results

        except Exception as e:
            logger.error(f"HN search failed: {e}")
            return []

    async def search_data_gouv(
        self,
        keywords: List[str],
        organization: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Recherche sur data.gouv.fr (datasets publics français)

        Args:
            keywords: Mots-clés
            organization: Organisation spécifique

        Returns:
            Liste de datasets
        """
        query = " ".join(keywords)
        api_url = f"https://www.data.gouv.fr/api/1/datasets/?q={query}&page_size=20"

        if organization:
            api_url += f"&organization={organization}"

        try:
            content = await self.fetch_url(api_url)
            import json
            data = json.loads(content)

            results = []
            for dataset in data.get("data", []):
                results.append({
                    "title": dataset.get("title", ""),
                    "url": f"https://www.data.gouv.fr/fr/datasets/{dataset.get('slug', '')}",
                    "description": dataset.get("description", ""),
                    "organization": dataset.get("organization", {}).get("name", ""),
                    "tags": dataset.get("tags", []),
                    "last_update": dataset.get("last_update", ""),
                    "frequency": dataset.get("frequency", "")
                })

            logger.info(f"✓ Found {len(results)} datasets on data.gouv.fr for '{query}'")
            return results

        except Exception as e:
            logger.error(f"data.gouv.fr search failed: {e}")
            return []

    async def generic_search(
        self,
        source: str,
        keywords: List[str],
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Point d'entrée générique pour recherche multi-sources

        Args:
            source: Type de source ("github", "hackernews", "datagouv", "rss", etc.)
            keywords: Mots-clés
            filters: Filtres supplémentaires spécifiques à la source

        Returns:
            Liste de résultats normalisés
        """
        filters = filters or {}

        if source == "github":
            return await self.search_github(
                keywords,
                language=filters.get("language"),
                min_stars=filters.get("min_stars", 0)
            )
        elif source == "hackernews":
            return await self.search_hackernews(keywords, days=filters.get("days", 7))
        elif source == "datagouv":
            return await self.search_data_gouv(keywords, organization=filters.get("organization"))
        elif source == "rss" and filters.get("feed_url"):
            return await self.fetch_rss_feed(filters["feed_url"])
        else:
            logger.warning(f"Unknown source: {source}")
            return []
