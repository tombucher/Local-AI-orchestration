# ============================================================================
# Dockerfile Backend - Orchestrateur IA
# ============================================================================

FROM python:3.11-slim as base

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ============================================================================
# Stage Development
# ============================================================================
FROM base as development

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    libffi-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copier requirements (dev : + outils de test)
COPY requirements.txt requirements-dev.txt ./

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copier le code (sera overridé par volume en dev)
COPY . .

# Port
EXPOSE 8000

# Commande par défaut (sera overridée par docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================================================
# Stage Production
# ============================================================================
FROM base as production

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    libffi-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copier requirements
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY --chown=appuser:appuser . .

# Changer vers utilisateur non-root
USER appuser

# Port
EXPOSE 8000

# Commande de production (sans --reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
