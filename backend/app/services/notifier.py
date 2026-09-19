"""
Notifications push via ntfy (https://ntfy.sh) — envoi du briefing du matin
sur le téléphone. Désactivé si NTFY_TOPIC est vide.
"""
import base64
import logging
from typing import Optional

import aiohttp

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    return bool(settings.NTFY_TOPIC)


async def send_notification(title: str, message: str, tags: str = "newspaper", click: Optional[str] = None, priority: int = 3) -> bool:
    """Envoie une notification ntfy. Retourne True si acceptée par le serveur."""
    if not is_enabled():
        return False
    url = f"{settings.NTFY_URL.rstrip('/')}/{settings.NTFY_TOPIC}"
    # Les en-têtes HTTP sont en latin-1 : ntfy accepte le titre encodé RFC 2047 sinon
    encoded_title = title if title.isascii() else "=?UTF-8?B?" + base64.b64encode(title.encode()).decode() + "?="
    headers = {
        "Title": encoded_title,
        "Tags": tags,
        "Priority": str(priority),
    }
    if click:
        headers["Click"] = click
    if settings.NTFY_TOKEN:
        headers["Authorization"] = f"Bearer {settings.NTFY_TOKEN}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=message.encode("utf-8"), headers=headers, timeout=15) as resp:
                ok = resp.status < 300
                if not ok:
                    logger.warning(f"ntfy a refusé la notification ({resp.status}): {await resp.text()}")
                return ok
    except Exception as e:
        logger.warning(f"ntfy indisponible : {e}")
        return False


def format_briefing(summary: str, top_priorities: list, next_actions: Optional[list] = None) -> str:
    """Texte court et lisible sur téléphone."""
    lines = [summary.strip()]
    if top_priorities:
        lines.append("")
        for i, p in enumerate(top_priorities[:3], 1):
            lines.append(f"{i}. {p}")
    if next_actions:
        lines.append("")
        lines.append("→ " + " · ".join(next_actions[:2]))
    return "\n".join(lines)


async def notify_briefing(report) -> bool:
    """Envoie le briefing quotidien (objet DailyReport du service)."""
    if not is_enabled():
        return False
    next_actions = [
        f"{p.project_name} : {p.next_obvious_action}"
        for p in getattr(report, "projects", [])
        if getattr(p, "next_obvious_action", None)
    ]
    click = f"{settings.APP_PUBLIC_URL.rstrip('/')}/dashboard" if settings.APP_PUBLIC_URL else None
    sent = await send_notification(
        title="Le briefing du matin",
        message=format_briefing(report.summary, report.top_priorities, next_actions),
        click=click,
    )
    if sent:
        logger.info("📱 Briefing envoyé via ntfy")
    return sent
