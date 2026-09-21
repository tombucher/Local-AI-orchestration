"""
Tests des sources d'images à clé (Unsplash, Pexels).

Les réponses simulées reproduisent les schémas documentés officiellement ; ces
tests valident donc le mapping des champs, pas la disponibilité des services.
"""

import pytest

from app.services.modules.web_research import WebResearchModule


class _FausseReponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status = status

    async def json(self, **_):
        return self._payload

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _FausseSession:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
        self.dernier_appel = None

    def get(self, url, **kwargs):
        self.dernier_appel = (url, kwargs)
        return _FausseReponse(self.payload, self.status)


def _module(payload, status=200):
    m = WebResearchModule()
    m.session = _FausseSession(payload, status)
    return m


# ------------------------------------------------------------- Unsplash ----

UNSPLASH_OK = {
    "results": [{
        "description": "Vieille imprimante thermique",
        "alt_description": "imprimante",
        "urls": {"raw": "r", "full": "f", "regular": "https://u/regular.jpg",
                 "small": "https://u/small.jpg", "thumb": "https://u/thumb.jpg"},
        "links": {"html": "https://unsplash.com/photos/abc"},
        "user": {"name": "Jeanne Dupont"},
    }]
}


@pytest.mark.asyncio
async def test_unsplash_mapping(monkeypatch):
    from app.services.modules import web_research as wr
    monkeypatch.setattr(wr.app_settings, "UNSPLASH_ACCESS_KEY", "cle-factice", raising=False)

    m = _module(UNSPLASH_OK)
    res = await m.search_unsplash("imprimante thermique")

    assert len(res) == 1
    img = res[0]
    assert img["title"] == "Vieille imprimante thermique"
    assert img["thumbnail_url"] == "https://u/small.jpg"
    assert img["image_url"] == "https://u/regular.jpg"
    assert img["url"] == "https://unsplash.com/photos/abc"
    assert img["source_platform"] == "Unsplash"
    assert "Jeanne Dupont" in img["license"]
    # L'authentification Unsplash se fait par « Client-ID », pas « Bearer »
    _, kwargs = m.session.dernier_appel
    assert kwargs["headers"]["Authorization"] == "Client-ID cle-factice"


@pytest.mark.asyncio
async def test_unsplash_sans_cle_ignore():
    from app.services.modules import web_research as wr
    original = wr.app_settings.UNSPLASH_ACCESS_KEY
    wr.app_settings.UNSPLASH_ACCESS_KEY = ""
    try:
        assert await _module(UNSPLASH_OK).search_unsplash("x") == []
    finally:
        wr.app_settings.UNSPLASH_ACCESS_KEY = original


@pytest.mark.asyncio
async def test_unsplash_cle_refusee(monkeypatch, caplog):
    import logging
    from app.services.modules import web_research as wr
    monkeypatch.setattr(wr.app_settings, "UNSPLASH_ACCESS_KEY", "mauvaise", raising=False)

    with caplog.at_level(logging.ERROR):
        assert await _module({}, status=401).search_unsplash("x") == []
    assert "UNSPLASH_ACCESS_KEY" in caplog.text


# --------------------------------------------------------------- Pexels ----

PEXELS_OK = {
    "photos": [{
        "id": 123,
        "url": "https://www.pexels.com/photo/123/",
        "photographer": "Paul Martin",
        "alt": "Ticket de caisse imprimé",
        "src": {"original": "https://p/orig.jpg", "large": "https://p/large.jpg",
                "medium": "https://p/medium.jpg", "tiny": "https://p/tiny.jpg"},
    }]
}


@pytest.mark.asyncio
async def test_pexels_mapping(monkeypatch):
    from app.services.modules import web_research as wr
    monkeypatch.setattr(wr.app_settings, "PEXELS_API_KEY", "cle-factice", raising=False)

    m = _module(PEXELS_OK)
    res = await m.search_pexels("ticket imprimé")

    assert len(res) == 1
    img = res[0]
    assert img["title"] == "Ticket de caisse imprimé"
    assert img["thumbnail_url"] == "https://p/medium.jpg"
    assert img["image_url"] == "https://p/large.jpg"
    assert img["source_platform"] == "Pexels"
    assert "Paul Martin" in img["license"]
    # Pexels attend la clé brute, sans préfixe
    _, kwargs = m.session.dernier_appel
    assert kwargs["headers"]["Authorization"] == "cle-factice"


@pytest.mark.asyncio
async def test_pexels_sans_cle_ignore():
    from app.services.modules import web_research as wr
    original = wr.app_settings.PEXELS_API_KEY
    wr.app_settings.PEXELS_API_KEY = ""
    try:
        assert await _module(PEXELS_OK).search_pexels("x") == []
    finally:
        wr.app_settings.PEXELS_API_KEY = original


@pytest.mark.asyncio
async def test_photo_sans_url_ignoree(monkeypatch):
    from app.services.modules import web_research as wr
    monkeypatch.setattr(wr.app_settings, "PEXELS_API_KEY", "cle", raising=False)

    assert await _module({"photos": [{"id": 1, "src": {}}]}).search_pexels("x") == []
