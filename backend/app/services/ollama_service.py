"""
Service Ollama générique pour les appels de chat (dialogue, idéation, etc.)

Différence avec OllamaClient:
- OllamaClient: Spécialisé pour la génération de code avec Task objects
- OllamaService: Générique pour tout type de chat/dialogue
"""
import logging
from app.services.model_registry import resolve_model, think_kwargs
from typing import List, Dict, Any, AsyncGenerator, Optional
import ollama

logger = logging.getLogger(__name__)


class OllamaService:
    """
    Service générique pour les appels de chat à Ollama.

    Utilisé pour:
    - Dialogue socratique d'idéation
    - Extraction de contexte
    - Tout autre usage conversationnel
    """

    def __init__(self, host: str = "http://host.docker.internal:11434"):
        """
        Initialise le service Ollama.

        Args:
            host: URL de l'instance Ollama (défaut: host.docker.internal depuis Docker)
        """
        self.host = host
        self.client = ollama.Client(host=host)
        logger.info(f"OllamaService initialized: {host}")

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Envoie une requête de chat à Ollama (version NON-STREAMING).

        Args:
            model: Nom du modèle Ollama (ex: "mistral:7b-instruct-q4_K_M")
            messages: Liste de messages au format [{"role": "user|assistant|system", "content": "..."}]
            stream: Si True, retourne un générateur (utiliser chat_stream à la place)
            options: Options supplémentaires pour Ollama (temperature, etc.)
            tools: Liste optionnelle de tools (function calling) format OpenAI

        Returns:
            Réponse complète d'Ollama avec format:
            {
                "message": {"role": "assistant", "content": "...", "tool_calls": [...]},
                "done": true,
                "eval_count": 123,
                "prompt_eval_count": 45,
                ...
            }
        """
        default_options = {
            "temperature": 0.7,
            "num_ctx": 4096,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1,
        }

        # Merge options with defaults
        final_options = {**default_options, **(options or {})}

        try:
            logger.info(f"Sending chat request to {model} ({len(messages)} messages, tools={bool(tools)})")

            # Préparer les arguments pour l'appel Ollama
            chat_args = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": final_options
            }
            # Désactive le thinking natif (qwen3.x) pour une réponse directe
            chat_args["model"] = resolve_model(model, "idéation")
            chat_args.update(think_kwargs(chat_args["model"]))

            # Ajouter les tools si fournis
            if tools:
                chat_args["tools"] = tools
                logger.info(f"Using {len(tools)} tool(s) for function calling")

            response = self.client.chat(**chat_args)

            logger.info(
                f"Received response from {model} "
                f"({response.get('eval_count', 0)} tokens generated)"
            )

            # Vérifier si le modèle a appelé des tools
            if "message" in response and "tool_calls" in response["message"]:
                logger.info(f"Model called {len(response['message']['tool_calls'])} tool(s)")

            return response

        except Exception as e:
            logger.error(f"Chat request failed for {model}: {e}")
            raise

    async def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Envoie une requête de chat à Ollama en mode STREAMING.

        Args:
            model: Nom du modèle Ollama
            messages: Liste de messages au format chat
            options: Options supplémentaires pour Ollama
            tools: Liste optionnelle de tools (function calling)

        Yields:
            Chunks de réponse au fur et à mesure de la génération.
            Chaque chunk a le format:
            {
                "message": {"role": "assistant", "content": "chunk_text", "tool_calls": [...]},
                "done": false,
                ...
            }
            Le dernier chunk aura "done": true
        """
        default_options = {
            "temperature": 0.7,
            "num_ctx": 4096,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1,
        }

        final_options = {**default_options, **(options or {})}

        try:
            logger.info(f"Starting streaming chat with {model} ({len(messages)} messages, tools={bool(tools)})")

            # Préparer les arguments pour l'appel Ollama
            chat_args = {
                "model": model,
                "messages": messages,
                "stream": True,
                "options": final_options
            }
            chat_args["model"] = resolve_model(model, "idéation")
            chat_args.update(think_kwargs(chat_args["model"]))

            # Ajouter les tools si fournis
            if tools:
                chat_args["tools"] = tools
                logger.info(f"Using {len(tools)} tool(s) for streaming function calling")

            stream = self.client.chat(**chat_args)

            chunk_count = 0
            for chunk in stream:
                chunk_count += 1
                yield chunk

                # Log quand c'est terminé
                if chunk.get("done", False):
                    logger.info(
                        f"Streaming complete for {model}: "
                        f"{chunk_count} chunks, "
                        f"{chunk.get('eval_count', 0)} tokens"
                    )

        except Exception as e:
            logger.error(f"Streaming chat failed for {model}: {e}")
            raise

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Génère une complétion simple (sans format chat multi-messages).

        Args:
            model: Nom du modèle
            prompt: Prompt utilisateur
            system: Prompt système optionnel
            stream: Si True, utiliser generate_stream() à la place
            options: Options Ollama

        Returns:
            Réponse complète d'Ollama
        """
        default_options = {
            "temperature": 0.7,
            "num_ctx": 4096,
        }

        final_options = {**default_options, **(options or {})}

        try:
            logger.info(f"Generating with {model} (prompt: {len(prompt)} chars)")

            response = self.client.generate(
                model=model,
                prompt=prompt,
                system=system,
                stream=False,
                options=final_options
            )

            logger.info(f"Generation complete ({response.get('eval_count', 0)} tokens)")
            return response

        except Exception as e:
            logger.error(f"Generation failed for {model}: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Vérifie que Ollama est accessible.

        Returns:
            True si Ollama répond, False sinon
        """
        try:
            self.client.list()
            logger.info("Ollama health check: OK")
            return True
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    def list_models(self) -> List[str]:
        """
        Liste les modèles disponibles sur Ollama.

        Returns:
            Liste des noms de modèles
        """
        try:
            models = self.client.list()
            model_names = [model['name'] for model in models.get('models', [])]
            logger.info(f"Found {len(model_names)} Ollama models")
            return model_names
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []
