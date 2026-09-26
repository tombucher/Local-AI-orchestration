"""
Configuration de l'application avec Pydantic Settings
"""
from typing import Any, Optional
from pydantic import field_validator, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration de l'application chargée depuis les variables d'environnement
    """
    
    # Application
    APP_NAME: str = "Orchestrateur IA"
    VERSION: str = "0.1.0"
    ENV: str = "development"
    DEBUG: bool = False
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 jours
    
    # Database
    DATABASE_URL: PostgresDsn
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:5199",  # Vite preview (outillage local)
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    
    # Dossier du Mac partagé avec le conteneur (docker-compose : ~/Documents par
    # défaut), où l'on choisit son dossier de projets. PROJECTS_MOUNT_DISPLAY est
    # le même dossier vu depuis le Mac, pour afficher des chemins parlants.
    PROJECTS_MOUNT: str = "/mac"
    PROJECTS_MOUNT_DISPLAY: str = ""

    # Fuseau de l'utilisateur : heure du briefing et « aujourd'hui ». Le conteneur
    # tourne en UTC — le briefing de « 8 h » tombait à 10 h à Paris.
    TIMEZONE: str = "Europe/Paris"
    BRIEFING_HOUR: int = 8

    # Notifications push du briefing via ntfy (app gratuite iOS/Android).
    # NTFY_TOPIC vide = désactivé. Choisir un nom de topic difficile à deviner.
    NTFY_URL: str = "https://ntfy.sh"
    NTFY_TOPIC: str = ""
    NTFY_TOKEN: str = ""          # si serveur ntfy protégé
    APP_PUBLIC_URL: str = ""      # ex. https://mon-mac.tailnet.ts.net — lien dans la notification

    # Aides-Territoires (recherche d'aides publiques FR) — clé gratuite :
    # https://aides-territoires.beta.gouv.fr/api/ ; vide = source ignorée
    AIDES_TERRITOIRES_API_KEY: str = ""

    # Pexels (moodboard) — clé gratuite : https://www.pexels.com/api/
    # Vide = source ignorée. Seules images du lot réellement réutilisables.
    # Unsplash écarté : son API est réservée aux usages « non-automated ».
    PEXELS_API_KEY: str = ""

    # Are.na (moodboard) — jeton perso gratuit : https://dev.are.na/oauth/applications
    # Vide = source ignorée. Les lectures publiques passent même sans jeton, mais
    # le jeton évite les limitations de débit.
    ARENA_ACCESS_TOKEN: str = ""

    # Ollama
    OLLAMA_HOST: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL_MISTRAL: str = "mistral:7b-instruct-q4_K_M"
    OLLAMA_MODEL_DEVSTRAL: str = "devstral-small-2"
    OLLAMA_MODEL_CODE: str = "mistral:7b-instruct-q4_K_M"  # Utilise Mistral qui fonctionne mieux avec le streaming
    OLLAMA_MODEL_PROMPT: str = "gemma4:12b-mlx"  # Modèle rapide : requêtes de veille, scoring, briefing

    # Orchestrator
    ORCHESTRATOR_INTERVAL_MINUTES: int = 2  # Intervalle entre chaque exécution du scheduler
    ORCHESTRATOR_BATCH_SIZE: int = 3  # Nombre de tâches en parallèle (M3 Max supporte 3-5 inférences)

    # Recherche web — SearXNG auto-hébergé (prioritaire s'il est configuré).
    # Métamoteur local : pas de clé, pas de quota, agrège Google/Bing/Qwant.
    # Le service `searxng` du docker-compose écoute sur http://searxng:8080.
    SEARXNG_URL: str = ""

    # Search API — Brave Search (repli ; l'offre gratuite n'existe plus)
    BRAVE_SEARCH_API_KEY: Optional[str] = None

    @field_validator("BRAVE_SEARCH_API_KEY", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: Any) -> Optional[str]:
        """Convertit les chaînes vides en None (utile pour les vars d'env non définies)"""
        if isinstance(v, str) and not v.strip():
            return None
        return v

    # Logging
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: Any) -> str:
        """Valide et retourne l'URL de la base de données"""
        if isinstance(v, str):
            return v
        return str(v)


# Instance globale des settings
settings = Settings()
