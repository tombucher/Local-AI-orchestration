"""
Service de gestion du dialogue d'idéation socratique

Ce service orchestre les conversations entre l'utilisateur et Mistral 7B
pendant la phase d'idéation, en utilisant la méthode socratique.
"""
from typing import List, Dict, Any, AsyncGenerator, Optional
from datetime import datetime
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.project import Project, ProjectStatus
from app.models.ideation_message import IdeationMessage, MessageRole
from app.prompts.ideation_prompts import (
    get_socratic_system_prompt,
    get_welcome_message,
    get_extraction_system_prompt
)
from app.services.ollama_service import OllamaService
from app.services.model_registry import resolve_model
from app.services.web_search_service import WebSearchService


class IdeationService:
    """
    Service pour gérer le dialogue socratique d'idéation de projet.

    Responsabilités:
    - Récupérer l'historique des messages d'un projet
    - Envoyer des messages à Mistral 7B avec le prompt socratique
    - Sauvegarder les messages (utilisateur et assistant) dans la DB
    - Gérer le streaming des réponses pour une interface fluide
    """

    def __init__(self, db: AsyncSession, user_id: Optional[int] = None):
        self.db = db
        self.ollama = OllamaService()
        self.web_search = WebSearchService()
        self.user_id = user_id
        self.model = resolve_model("devstral-small-2:latest", "idéation")

        # Définir les tools disponibles pour le LLM (format OpenAI)
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Recherche sur Internet pour trouver des références visuelles, exemples de projets, tendances actuelles, ou informations pertinentes. Utilise cette fonction quand tu as besoin d'enrichir ta réponse avec des exemples concrets, des inspirations ou des informations récentes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "La requête de recherche (ex: 'cartes de voeux 2026 design tendances', 'canvas creative coding examples')"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Nombre maximum de résultats (défaut: 3)",
                                "default": 3
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    def _model_supports_tools(self, model: str) -> bool:
        """
        Détermine si un modèle supporte les tools (function calling).

        Args:
            model: Nom du modèle

        Returns:
            True si le modèle supporte les tools, False sinon
        """
        # Liste des modèles connus pour supporter les tools
        tools_supported_models = [
            "devstral",
            "mistral-large",
            "mistral-medium",
            "qwen2.5-coder",
            "deepseek-coder-v2"
        ]

        # Vérifier si le modèle contient un des noms supportés
        model_lower = model.lower()
        return any(supported in model_lower for supported in tools_supported_models)

    async def _load_user_model_preference(self):
        """
        Charge les préférences de modèle de l'utilisateur.
        Met à jour self.model avec le modèle d'idéation de l'utilisateur.
        """
        if not self.user_id:
            return

        from app.models.user_settings import UserSettings

        result = await self.db.execute(
            select(UserSettings).where(UserSettings.user_id == self.user_id)
        )
        user_settings = result.scalar_one_or_none()

        if user_settings and user_settings.ollama_model_ideation:
            self.model = resolve_model(user_settings.ollama_model_ideation, "idéation")

    async def start_ideation(self, project_id: int) -> Dict[str, IdeationMessage]:
        """
        Démarre la phase d'idéation pour un projet.

        Utilise le titre et la description du projet comme contexte initial,
        puis génère automatiquement la première question socratique de l'IA.

        Args:
            project_id: ID du projet

        Returns:
            Dict avec 'welcome_message' (système) et 'initial_response' (assistant)

        Raises:
            ValueError: Si le projet n'existe pas ou n'est pas en statut IDEATION
        """
        # Charger les préférences de modèle de l'utilisateur
        await self._load_user_model_preference()

        # Récupérer le projet
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        if project.status != ProjectStatus.IDEATION:
            raise ValueError(
                f"Project {project_id} must be in IDEATION status to start ideation. "
                f"Current status: {project.status}"
            )

        # Créer le message de bienvenue système
        welcome_msg = IdeationMessage(
            project_id=project_id,
            role=MessageRole.SYSTEM,
            content=get_welcome_message(),
            meta={"type": "welcome"}
        )
        self.db.add(welcome_msg)

        # Créer un message utilisateur "fantôme" avec le contexte du projet
        # Si le projet n'a pas encore de nom/description (mode dialogue unifié),
        # on crée un message vide qui sera rempli par l'utilisateur
        if project.name and project.name != "Nouveau projet":
            project_context = f"Je souhaite lancer le projet '{project.name}'"
            if project.description:
                project_context += f" avec la description suivante : {project.description}"
            else:
                project_context += "."

            context_msg = IdeationMessage(
                project_id=project_id,
                role=MessageRole.USER,
                content=project_context,
                meta={"type": "initial_context", "auto_generated": True}
            )
            self.db.add(context_msg)
        else:
            # Mode dialogue unifié : pas de contexte initial,
            # l'utilisateur va décrire son projet dans le premier message
            context_msg = IdeationMessage(
                project_id=project_id,
                role=MessageRole.USER,
                content="Je veux créer un nouveau projet.",
                meta={"type": "initial_context", "auto_generated": True, "unified_mode": True}
            )
            self.db.add(context_msg)

        await self.db.commit()
        await self.db.refresh(welcome_msg)
        await self.db.refresh(context_msg)

        # Générer automatiquement la première réponse de l'IA basée sur ce contexte
        initial_response = await self.generate_assistant_response(project_id)

        return {
            "welcome_message": welcome_msg,
            "initial_response": initial_response
        }

    async def get_conversation_history(
        self,
        project_id: int,
        limit: Optional[int] = None
    ) -> List[IdeationMessage]:
        """
        Récupère l'historique complet des messages d'un projet.

        Args:
            project_id: ID du projet
            limit: Nombre maximum de messages à récupérer (None = tous)

        Returns:
            Liste des messages triés par date de création (ancien -> récent)
        """
        query = (
            select(IdeationMessage)
            .where(IdeationMessage.project_id == project_id)
            .order_by(IdeationMessage.created_at.asc())
        )

        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    def _format_messages_for_ollama(
        self,
        history: List[IdeationMessage]
    ) -> List[Dict[str, str]]:
        """
        Convertit l'historique des messages au format attendu par Ollama.

        Args:
            history: Liste des messages de la conversation

        Returns:
            Liste de dicts avec format {"role": "user|assistant|system", "content": "..."}
        """
        # Ajouter le prompt système en premier
        messages = [
            {
                "role": "system",
                "content": get_socratic_system_prompt()
            }
        ]

        # Ajouter les messages de l'historique
        for msg in history:
            # Convertir MessageRole enum vers format Ollama
            role = msg.role.value.lower()  # "USER" -> "user", "ASSISTANT" -> "assistant", "SYSTEM" -> "system"

            # Skip les messages système de type "welcome" (déjà gérés par le prompt)
            if msg.role == MessageRole.SYSTEM and msg.meta.get("type") == "welcome":
                continue

            messages.append({
                "role": role,
                "content": msg.content
            })

        return messages

    async def _execute_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """
        Exécute un appel de fonction (tool call) demandé par le LLM.

        Args:
            tool_name: Nom de la fonction à appeler
            tool_args: Arguments de la fonction

        Returns:
            Résultat de l'appel de fonction formaté en texte
        """
        if tool_name == "web_search":
            query = tool_args.get("query", "")
            max_results = tool_args.get("max_results", 3)

            # Effectuer la recherche
            results = await self.web_search.search_text(query, max_results=max_results)

            if not results:
                return f"Aucun résultat trouvé pour '{query}'"

            # Formater les résultats
            formatted = self.web_search.format_search_results_for_llm(results, "text")
            return f"Résultats de recherche pour '{query}':\n\n{formatted}"

        else:
            return f"Fonction '{tool_name}' non supportée"

    async def send_user_message(
        self,
        project_id: int,
        user_message: str
    ) -> IdeationMessage:
        """
        Enregistre un message utilisateur dans la conversation.

        Args:
            project_id: ID du projet
            user_message: Contenu du message utilisateur

        Returns:
            Message utilisateur créé
        """
        # Créer et sauvegarder le message utilisateur
        msg = IdeationMessage(
            project_id=project_id,
            role=MessageRole.USER,
            content=user_message,
            meta={}
        )

        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)

        return msg

    async def generate_assistant_response(
        self,
        project_id: int
    ) -> IdeationMessage:
        """
        Génère une réponse de l'assistant basée sur l'historique de conversation.
        Version NON-STREAMING (simple).

        Args:
            project_id: ID du projet

        Returns:
            Message assistant créé
        """
        # Charger les préférences de modèle de l'utilisateur
        await self._load_user_model_preference()

        # Récupérer l'historique complet
        history = await self.get_conversation_history(project_id)

        # Formater pour Ollama
        messages = self._format_messages_for_ollama(history)

        # Appeler Ollama avec les tools disponibles (seulement si le modèle les supporte)
        start_time = datetime.now()
        tools = self.tools if self._model_supports_tools(self.model) else None
        response = await self.ollama.chat(
            model=self.model,
            messages=messages,
            stream=False,
            tools=tools
        )
        end_time = datetime.now()

        # Vérifier si le modèle a demandé d'appeler des tools
        tool_calls = response.get("message", {}).get("tool_calls", [])

        if tool_calls:
            # Exécuter tous les tool calls
            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])

                # Exécuter le tool
                tool_result = await self._execute_tool_call(tool_name, tool_args)

                # Ajouter le résultat du tool au contexte
                messages.append({
                    "role": "tool",
                    "content": tool_result
                })

            # Appeler à nouveau le LLM avec les résultats des tools
            response = await self.ollama.chat(
                model=self.model,
                messages=messages,
                stream=False,
                tools=self.tools
            )

        # Extraire le contenu de la réponse finale
        assistant_content = response.get("message", {}).get("content", "")

        # Vérifier que le contenu n'est pas vide
        if not assistant_content or not assistant_content.strip():
            raise ValueError(
                f"AI generated empty response for project {project_id}. "
                f"This might indicate a model error."
            )

        # Calculer les métadonnées
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        meta = {
            "model": self.model,
            "response_time_ms": response_time_ms,
            "tokens_used": response.get("eval_count", 0),
            "prompt_tokens": response.get("prompt_eval_count", 0)
        }

        # Sauvegarder la réponse de l'assistant
        assistant_msg = IdeationMessage(
            project_id=project_id,
            role=MessageRole.ASSISTANT,
            content=assistant_content.strip(),
            meta=meta
        )

        self.db.add(assistant_msg)
        await self.db.commit()
        await self.db.refresh(assistant_msg)

        return assistant_msg

    async def generate_assistant_response_stream(
        self,
        project_id: int
    ) -> AsyncGenerator[str, None]:
        """
        Génère une réponse de l'assistant avec streaming.
        Version STREAMING pour interface fluide.

        Args:
            project_id: ID du projet

        Yields:
            Chunks de texte au fur et à mesure de la génération

        Note:
            Le message complet sera sauvegardé en DB à la fin du streaming.
        """
        # Charger les préférences de modèle de l'utilisateur
        await self._load_user_model_preference()

        # Récupérer l'historique complet
        history = await self.get_conversation_history(project_id)

        # Formater pour Ollama
        messages = self._format_messages_for_ollama(history)

        # Appeler Ollama en mode streaming
        # Note: Les tools sont activés seulement si le modèle les supporte
        start_time = datetime.now()
        full_content = ""
        total_tokens = 0
        tools = self.tools if self._model_supports_tools(self.model) else None

        async for chunk in self.ollama.chat_stream(
            model=self.model,
            messages=messages,
            tools=tools
        ):
            # Extraire le contenu du chunk
            content = chunk.get("message", {}).get("content", "")

            if content:
                full_content += content
                yield content

            # Accumuler les tokens si disponibles
            if "eval_count" in chunk:
                total_tokens = chunk["eval_count"]

        end_time = datetime.now()

        # Vérifier que le contenu n'est pas vide
        if not full_content or not full_content.strip():
            raise ValueError(
                f"AI generated empty response for project {project_id}. "
                f"This might indicate a model error."
            )

        # Sauvegarder le message complet à la fin
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        meta = {
            "model": self.model,
            "response_time_ms": response_time_ms,
            "tokens_used": total_tokens,
            "streaming": True
        }

        assistant_msg = IdeationMessage(
            project_id=project_id,
            role=MessageRole.ASSISTANT,
            content=full_content.strip(),
            meta=meta
        )

        self.db.add(assistant_msg)
        await self.db.commit()

    async def extract_project_info(self, project_id: int) -> Dict[str, Any]:
        """
        Extrait les informations du projet depuis l'historique du dialogue.

        Utilise le prompt d'extraction pour analyser la conversation complète
        et extraire : name, description, type, features.

        Args:
            project_id: ID du projet

        Returns:
            Dict avec les infos extraites : {name, description, type, features}
        """
        # Récupérer l'historique complet
        history = await self.get_conversation_history(project_id)

        # Formatter l'historique pour l'extraction
        conversation_text = "\n\n".join([
            f"{msg.role.value}: {msg.content}"
            for msg in history
            if msg.role != MessageRole.SYSTEM  # Ignorer les messages système
        ])

        # Construire le prompt d'extraction
        extraction_prompt = f"""Voici l'historique complet de la conversation d'idéation :

{conversation_text}

Analyse cette conversation et extrais les informations clés du projet au format JSON."""

        # Appeler Ollama pour l'extraction
        response = await self.ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": get_extraction_system_prompt()
                },
                {
                    "role": "user",
                    "content": extraction_prompt
                }
            ],
            stream=False
        )

        # Extraire le contenu
        content = response.get("message", {}).get("content", "").strip()

        # Nettoyer le markdown si présent
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()

        # Parser le JSON
        try:
            extracted_info = json.loads(content)
            return extracted_info
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse extracted project info: {e}\n"
                f"Content: {content[:200]}"
            )

    def detect_generate_tasks_signal(self, message_content: str) -> bool:
        """
        Détecte si le message contient le signal GENERATE_TASKS.

        Args:
            message_content: Contenu du message de l'assistant

        Returns:
            True si le signal est détecté, False sinon
        """
        # Chercher le signal exact
        if "GENERATE_TASKS" in message_content:
            return True

        # Chercher des variations
        variations = [
            "génération des tâches",
            "générer les tâches",
            "créer le plan de tâches",
            "je génère le plan",
            "passage à la génération"
        ]

        content_lower = message_content.lower()
        return any(variation in content_lower for variation in variations)

    async def complete_ideation(self, project_id: int) -> Project:
        """
        Marque la phase d'idéation comme terminée.

        Args:
            project_id: ID du projet

        Returns:
            Projet mis à jour avec statut PLANNING

        Raises:
            ValueError: Si le projet n'existe pas
        """
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Récupérer tout l'historique pour le sauvegarder en cache
        history = await self.get_conversation_history(project_id)

        # Convertir en format JSON sérialisable
        transcript = [
            {
                "role": msg.role.value,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "meta": msg.meta
            }
            for msg in history
        ]

        # Mettre à jour le projet
        project.status = ProjectStatus.PLANNING
        project.ideation_transcript = transcript
        project.ideation_completed_at = datetime.now()

        await self.db.commit()
        await self.db.refresh(project)

        return project
