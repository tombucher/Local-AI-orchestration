"""
Structured logging avec correlation IDs pour traçabilité des requêtes.

Chaque requête HTTP reçoit un correlation_id unique (UUID court).
Ce correlation_id est propagé dans tous les logs émis pendant la requête,
permettant de tracer une tâche à travers scheduler → orchestrator → LLM.
"""
import logging
import uuid
from contextvars import ContextVar

# ContextVar pour stocker le correlation_id de la requête en cours
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default='-')


def get_correlation_id() -> str:
    """Retourne le correlation_id du contexte courant."""
    return correlation_id_var.get()


def set_correlation_id(cid: str | None = None) -> str:
    """Définit un correlation_id (génère un UUID court si non fourni)."""
    if cid is None:
        cid = uuid.uuid4().hex[:8]
    correlation_id_var.set(cid)
    return cid


class CorrelationFilter(logging.Filter):
    """Filtre logging qui injecte le correlation_id dans chaque record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()  # type: ignore[attr-defined]
        return True


def setup_logging(log_level: str = "INFO") -> None:
    """Configure le logging structuré avec correlation_id."""
    root_logger = logging.getLogger()

    # Format avec correlation_id
    formatter = logging.Formatter(
        '%(asctime)s [%(correlation_id)s] %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Appliquer le filtre et le formatter au handler existant ou en créer un
    if root_logger.handlers:
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
            handler.addFilter(CorrelationFilter())
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.addFilter(CorrelationFilter())
        root_logger.addHandler(handler)

    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
