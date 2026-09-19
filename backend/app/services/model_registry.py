"""
Registre des modèles Ollama — résolution centrale du modèle à utiliser.

Problème résolu : les préférences utilisateur et les défauts de config
référencent des modèles qui peuvent avoir été supprimés d'Ollama (404).
Ici, tout appel LLM passe par `resolve_model()` : le modèle préféré s'il
est installé, sinon un repli réellement disponible, avec un avertissement.

`supports_thinking()` lit les capacités réelles du modèle (API /show) pour
décider s'il faut passer `think=False` — plus fiable qu'une détection par nom.
"""
import logging
import time
from typing import Any, Dict, List, Optional

import ollama

from app.core.config import settings

logger = logging.getLogger(__name__)

_LIST_TTL_SECONDS = 60
_list_cache: Dict[str, Any] = {"ts": 0.0, "models": []}
_caps_cache: Dict[str, set] = {}
_warned_missing: set = set()


def _client() -> ollama.Client:
    return ollama.Client(host=settings.OLLAMA_HOST)


def _field(obj: Any, *keys: str) -> Optional[Any]:
    """Lit un champ sur un dict ou un objet pydantic (ollama>=0.5)."""
    for key in keys:
        if isinstance(obj, dict) and obj.get(key) is not None:
            return obj[key]
        value = getattr(obj, key, None)
        if value is not None:
            return value
    return None


def list_local_models_detailed(force: bool = False) -> List[Dict[str, Any]]:
    """Modèles installés (nom, taille, date), avec cache court."""
    now = time.time()
    if not force and _list_cache["models"] and now - _list_cache["ts"] < _LIST_TTL_SECONDS:
        return _list_cache["models"]
    try:
        resp = _client().list()
        raw = _field(resp, "models") or []
        models = []
        for m in raw:
            name = _field(m, "model", "name")
            if not name:
                continue
            models.append({
                "name": name,
                "size": _field(m, "size") or 0,
                "modified_at": str(_field(m, "modified_at") or ""),
            })
        _list_cache.update(ts=now, models=models)
        return models
    except Exception as e:
        logger.warning(f"Ollama model list failed: {e}")
        return _list_cache["models"]


def list_local_models(force: bool = False) -> List[str]:
    return [m["name"] for m in list_local_models_detailed(force)]


def _is_usable_for_fallback(name: str) -> bool:
    lowered = name.lower()
    return "embed" not in lowered and ":cloud" not in lowered


def _matches(preferred: str, installed: List[str]) -> Optional[str]:
    """Correspondance exacte, ou sans tag (ex: 'devstral-small-2' ~ 'devstral-small-2:latest')."""
    if preferred in installed:
        return preferred
    base = preferred.split(":")[0]
    for name in installed:
        if name.split(":")[0] == base:
            return name
    return None


def resolve_model(preferred: Optional[str], purpose: str = "") -> str:
    """Retourne le modèle préféré s'il est installé, sinon un repli disponible.

    Ordre de repli : défaut de config (OLLAMA_MODEL_CODE) → premier modèle
    local utilisable (hors embeddings et modèles cloud) → n'importe lequel.
    Si Ollama ne répond pas, renvoie le préféré tel quel (l'erreur remontera
    à l'appel).
    """
    preferred = preferred or settings.OLLAMA_MODEL_CODE
    installed = list_local_models()
    if not installed:
        return preferred

    match = _matches(preferred, installed)
    if match:
        return match

    candidates = [m for m in installed if _is_usable_for_fallback(m)] or installed
    fallback = _matches(settings.OLLAMA_MODEL_CODE, candidates) or candidates[0]

    key = (preferred, fallback)
    if key not in _warned_missing:
        _warned_missing.add(key)
        logger.warning(
            f"⚠️ Modèle '{preferred}' introuvable dans Ollama"
            f"{f' ({purpose})' if purpose else ''} → repli sur '{fallback}'. "
            "Mets à jour tes préférences de modèles dans Paramètres."
        )
    return fallback


def supports_thinking(model: str) -> bool:
    """True si le modèle expose la capacité 'thinking' (qwen3.x, deepseek-r1, gpt-oss…).
    Lu via l'API /show et mis en cache ; repli sur une heuristique par nom."""
    if model in _caps_cache:
        return "thinking" in _caps_cache[model]
    try:
        info = _client().show(model)
        caps = set(_field(info, "capabilities") or [])
        _caps_cache[model] = caps
        return "thinking" in caps
    except Exception as e:
        logger.debug(f"show({model}) failed: {e} — heuristique par nom")
        lowered = model.lower()
        return any(tag in lowered for tag in ("qwen3", "deepseek-r1", "gpt-oss"))


def think_kwargs(model: str) -> Dict[str, Any]:
    """Kwargs à passer à client.chat() : think=False seulement si le modèle le supporte
    (les modèles sans thinking rejettent le paramètre)."""
    return {"think": False} if supports_thinking(model) else {}
