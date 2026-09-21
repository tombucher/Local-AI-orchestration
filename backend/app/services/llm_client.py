"""
Client LLM pour génération de code avec Ollama (natif macOS)

Optimisé pour:
- Streaming pour détecter la fin de génération
- Timeouts explicites
- Logs de performance détaillés
- Détection EOS token
- Adaptation automatique selon le modèle (qwen3, mistral, etc.)
"""
import logging
import re
import time
from typing import Optional
import ollama

from app.models.task import Task
from app.core.config import settings
from app.services.model_registry import resolve_model, think_kwargs
from app.services.code_cleanup import strip_code_fences

logger = logging.getLogger(__name__)

class OllamaClient:
    """
    Client pour Ollama natif macOS avec streaming et monitoring

    Se connecte à Ollama tournant nativement sur macOS via host.docker.internal
    depuis le container Docker.
    """

    def __init__(self, host: str = "http://host.docker.internal:11434"):
        """
        Initialise le client Ollama

        Args:
            host: URL de l'instance Ollama (défaut: host.docker.internal depuis Docker)
        """
        self.host = host
        # Configurer le client avec un timeout de 300 secondes (5 minutes)
        self.client = ollama.Client(host=host, timeout=300.0)
        # Client asynchrone pour le streaming : itérer le client synchrone dans une
        # coroutine bloquait la boucle d'événements pendant TOUTE la génération —
        # plusieurs minutes durant lesquelles l'API ne répondait plus à rien, pas
        # même au health check ni au suivi d'avancement.
        self.async_client = ollama.AsyncClient(host=host, timeout=300.0)
        logger.info(f"✅ Ollama client initialized: {host} (timeout: 300s)")

    async def generate_code(
        self,
        task: Task,
        model_override: Optional[str] = None,
        user_settings: Optional[dict] = None,
        workspace_context: Optional[str] = None,
        document_context: Optional[str] = None,
        images: Optional[list] = None,
    ) -> str:
        """
        Génère du code avec streaming pour détecter la fin

        Args:
            task: Tâche avec llm_prompt rempli
            model_override: Modèle spécifique à utiliser (sinon utilise config par défaut)
            user_settings: Paramètres utilisateur avec préférences de modèles
            workspace_context: Plan de fichiers et code des autres tâches du projet
            document_context: Documents de référence déposés par l'utilisateur
            images: Images de référence en base64 (modèles dotés de vision uniquement)

        Returns:
            Code généré (str)

        Raises:
            Exception: Si la génération échoue ou timeout
        """
        model = self._select_model(task, model_override, user_settings)
        is_qwen3 = self._is_qwen3_model(model)
        prompt = self._build_prompt(task, is_qwen3, workspace_context, document_context)
        system_prompt = self._build_system_prompt(is_qwen3)
        options = self._get_llm_options(is_qwen3)

        try:
            start_time = time.time()
            logger.info(f"🤖 [TASK-{task.id}] Starting generation with {model} (qwen3={is_qwen3})")
            logger.info(f"🤖 [TASK-{task.id}] Prompt length: {len(prompt)} chars")

            full_response = ""
            thinking_buffer = ""  # Fallback : certains modèles qwen3 ne sortent que du thinking
            first_token_time = None
            chunk_count = 0

            # Les images vont sur le message utilisateur ; Ollama les attend en base64
            user_message = {'role': 'user', 'content': prompt}
            if images:
                user_message['images'] = images
                logger.info(f"🖼 [TASK-{task.id}] {len(images)} image(s) de référence jointes")

            stream = await self.async_client.chat(
                model=model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    user_message,
                ],
                stream=True,
                options=options,
                # qwen3.6+ ignore le « /no_think » du system prompt : il faut
                # désactiver le thinking nativement (None = omis pour mistral & co)
                **think_kwargs(model),
            )

            # Collecter les chunks en streaming
            async for chunk in stream:
                chunk_count += 1

                logger.debug(f"[TASK-{task.id}] Chunk {chunk_count}: {chunk}")

                if first_token_time is None:
                    first_token_time = time.time()
                    ttft = first_token_time - start_time
                    logger.info(f"⚡ [TASK-{task.id}] First token received in {ttft:.2f}s")

                # Capturer content ET thinking (qwen3 met parfois tout dans thinking)
                if 'message' in chunk:
                    msg = chunk['message']
                    content = msg.get('content') or ''
                    thinking = msg.get('thinking') or ''

                    if content:
                        full_response += content
                        if chunk_count % 10 == 0:
                            elapsed = time.time() - start_time
                            logger.info(f"📝 [TASK-{task.id}] Chunk {chunk_count} | {len(full_response)} chars | {elapsed:.1f}s elapsed")
                    elif thinking:
                        thinking_buffer += thinking
                        # Détection de boucle : si le thinking dépasse 8000 chars sans content,
                        # le modèle est probablement bloqué dans une boucle de raisonnement
                        if len(thinking_buffer) > 8000 and not full_response:
                            logger.error(
                                f"❌ [TASK-{task.id}] Boucle de thinking détectée ({len(thinking_buffer)} chars sans content) — abandon"
                            )
                            raise Exception(
                                "Le modèle est entré dans une boucle de raisonnement infini. "
                                "Essayez avec un modèle non-thinking (mistral) dans les paramètres."
                            )
                else:
                    logger.debug(f"[TASK-{task.id}] No message in chunk {chunk_count}")

                # Vérifier si c'est le dernier chunk (APRÈS avoir collecté le contenu)
                # Note: Ollama envoie plusieurs chunks avec done=True, donc on continue la boucle
                # jusqu'à ce qu'elle se termine naturellement
                if chunk.get('done', False):
                    end_time = time.time()
                    total_time = end_time - start_time
                    logger.info(f"✅ [TASK-{task.id}] Done chunk received ({chunk_count} chunks so far)")
                    logger.info(f"   - Current output: {len(full_response)} chars")

                    # Logs supplémentaires du modèle (seulement dans le dernier chunk final)
                    if 'eval_count' in chunk:
                        logger.info(f"📊 [TASK-{task.id}] Final Stats:")
                        logger.info(f"   - Total time: {total_time:.2f}s")
                        logger.info(f"   - TTFT: {ttft:.2f}s" if first_token_time else "   - TTFT: N/A")
                        logger.info(f"   - Chunks: {chunk_count}")
                        logger.info(f"   - Output: {len(full_response)} chars")
                        if total_time > 0:
                            logger.info(f"   - Speed: {len(full_response)/total_time:.0f} chars/s")
                        logger.info(f"   - Tokens generated: {chunk.get('eval_count', 0)}")
                        if 'eval_duration' in chunk:
                            eval_duration_ms = chunk.get('eval_duration', 0) / 1_000_000
                            logger.info(f"   - Eval duration: {eval_duration_ms:.0f}ms")

            # Si seul thinking est rempli, c'est un échec (pas un fallback) :
            # le thinking contient du raisonnement interne, pas la réponse finale.
            if (not full_response or not full_response.strip()) and thinking_buffer.strip():
                logger.error(
                    f"❌ [TASK-{task.id}] Modèle bloqué en thinking ({len(thinking_buffer)} chars) sans produire de content — "
                    f"essayer un autre modèle ou désactiver le thinking-mode"
                )
                raise Exception(
                    "Le modèle est resté bloqué dans son raisonnement interne sans produire de réponse. "
                    "Essayez avec un autre modèle (mistral) dans les paramètres."
                )

            # Vérification que nous avons bien reçu du contenu
            if not full_response or len(full_response.strip()) == 0:
                logger.error(f"❌ [TASK-{task.id}] No content received. Chunk count: {chunk_count}")
                raise Exception("No content received from Ollama")

            # Nettoyage des tags <think> de qwen3
            if is_qwen3 and '<think>' in full_response:
                full_response = re.sub(r'<think>.*?</think>', '', full_response, flags=re.DOTALL).strip()
                logger.info(f"🧹 [TASK-{task.id}] Cleaned <think> tags from qwen3 response")

            # Les modèles encadrent presque toujours le code par ```lang … ``` :
            # on écrit le fichier tel quel, donc ces marqueurs doivent sauter.
            unfenced = strip_code_fences(full_response)
            if unfenced != full_response.strip():
                logger.info(f"🧹 [TASK-{task.id}] Fences Markdown retirées du code généré")
            full_response = unfenced

            logger.info(f"✅ Code generated for task {task.id} ({len(full_response)} chars)")
            return full_response

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ [TASK-{task.id}] Generation failed after {elapsed:.2f}s: {e}")
            raise

    async def generate_text(self, task: Task, model_override: Optional[str] = None, user_settings: Optional[dict] = None) -> str:
        """
        Génère du contenu texte structuré (PAS du code) — pour research, admin, etc.

        Pour les modèles thinking (qwen3) : double passe
          - Passe 1 : raisonnement libre (capture le thinking)
          - Passe 2 : génération propre en Markdown en utilisant le thinking comme contexte
        Pour les autres modèles : passe unique classique.
        """
        model = self._select_model(task, model_override, user_settings, model_type='text')
        is_qwen3 = self._is_qwen3_model(model)
        prompt = self._build_text_prompt(task, is_qwen3)
        options = self._get_llm_options(is_qwen3)
        start_time = time.time()

        logger.info(f"📝 [TASK-{task.id}] Starting TEXT generation with {model} (qwen3={is_qwen3}, two_pass={is_qwen3})")
        logger.info(f"📝 [TASK-{task.id}] Prompt length: {len(prompt)} chars")

        try:
            if is_qwen3:
                # ================================================================
                # DOUBLE PASSE pour les modèles thinking (qwen3)
                # ================================================================

                # --- PASSE 1 : raisonnement libre ---
                logger.info(f"🧠 [TASK-{task.id}] Passe 1/2 — thinking libre...")
                thinking_buffer = ""

                stream1 = await self.async_client.chat(
                    model=model,
                    messages=[
                        {
                            'role': 'system',
                            'content': (
                                "Tu es un expert. Analyse en profondeur la tâche suivante "
                                "avant de produire ta réponse. Réfléchis méthodiquement."
                            )
                        },
                        {'role': 'user', 'content': prompt}
                    ],
                    stream=True,
                    options={**options, 'num_predict': 4096},
                    think=True,
                )

                async for chunk in stream1:
                    if 'message' in chunk:
                        thinking_buffer += chunk['message'].get('thinking') or ''
                        # Limite le thinking à 5000 chars pour éviter les boucles
                        if len(thinking_buffer) > 5000:
                            logger.warning(f"⚠️ [TASK-{task.id}] Thinking buffer plafonné à 5000 chars")
                            break

                t1_elapsed = time.time() - start_time
                logger.info(f"🧠 [TASK-{task.id}] Passe 1 terminée : {len(thinking_buffer)} chars de thinking en {t1_elapsed:.1f}s")

                # --- PASSE 2 : génération propre avec thinking en contexte ---
                logger.info(f"✍️ [TASK-{task.id}] Passe 2/2 — génération propre...")

                system_clean = self._build_text_system_prompt(True)  # inclut /no_think

                if thinking_buffer.strip():
                    augmented_prompt = (
                        f"{prompt}\n\n"
                        f"[Analyse préalable effectuée] :\n{thinking_buffer[:4000].strip()}\n\n"
                        "Sur la base de cette analyse, rédige le document final structuré en Markdown."
                    )
                else:
                    logger.warning(f"⚠️ [TASK-{task.id}] Aucun thinking capturé en passe 1 — génération directe")
                    augmented_prompt = prompt

                full_response = ""
                chunk_count = 0

                stream2 = await self.async_client.chat(
                    model=model,
                    messages=[
                        {'role': 'system', 'content': system_clean},
                        {'role': 'user', 'content': augmented_prompt}
                    ],
                    stream=True,
                    options=options,
                    think=False,
                )

                async for chunk in stream2:
                    chunk_count += 1
                    if 'message' in chunk:
                        content = chunk['message'].get('content') or ''
                        if content:
                            full_response += content
                            if chunk_count % 20 == 0:
                                elapsed = time.time() - start_time
                                logger.info(f"✍️ [TASK-{task.id}] Passe 2 chunk {chunk_count} | {len(full_response)} chars | {elapsed:.1f}s")

                total_time = time.time() - start_time
                logger.info(f"✅ [TASK-{task.id}] Double-passe TEXT terminée : {len(full_response)} chars en {total_time:.1f}s")

                if not full_response.strip():
                    raise Exception(
                        "La passe 2 n'a produit aucun contenu. "
                        "Essayez un modèle non-thinking (mistral) dans les paramètres."
                    )

                return full_response

            else:
                # ================================================================
                # PASSE UNIQUE pour les modèles classiques (mistral, etc.)
                # ================================================================
                system_prompt = self._build_text_system_prompt(False)
                full_response = ""
                thinking_buffer = ""
                first_token_time = None
                chunk_count = 0

                stream = await self.async_client.chat(
                    model=model,
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': prompt}
                    ],
                    stream=True,
                    options=options,
                    **think_kwargs(model),
                )

                async for chunk in stream:
                    chunk_count += 1

                    if first_token_time is None:
                        first_token_time = time.time()
                        ttft = first_token_time - start_time
                        logger.info(f"⚡ [TASK-{task.id}] First token in {ttft:.2f}s")

                    if 'message' in chunk:
                        msg = chunk['message']
                        content = msg.get('content') or ''
                        thinking = msg.get('thinking') or ''

                        if content:
                            full_response += content
                            if chunk_count % 10 == 0:
                                elapsed = time.time() - start_time
                                logger.info(f"📝 [TASK-{task.id}] Chunk {chunk_count} | {len(full_response)} chars | {elapsed:.1f}s")
                        elif thinking:
                            thinking_buffer += thinking

                    if chunk.get('done', False):
                        total_time = time.time() - start_time
                        logger.info(f"✅ [TASK-{task.id}] Text done ({chunk_count} chunks, {len(full_response)} chars, {total_time:.2f}s)")

                if not full_response.strip() and thinking_buffer.strip():
                    logger.error(f"❌ [TASK-{task.id}] Seulement du thinking reçu — utilisez un modèle non-thinking")
                    raise Exception(
                        "Le modèle est resté en mode thinking sans produire de contenu. "
                        "Essayez un autre modèle dans les paramètres."
                    )

                if not full_response.strip():
                    raise Exception("No content received from Ollama")

                # Nettoyage des tags <think> résiduels
                if '<think>' in full_response:
                    full_response = re.sub(r'<think>.*?</think>', '', full_response, flags=re.DOTALL).strip()

                logger.info(f"✅ Text generated for task {task.id} ({len(full_response)} chars)")
                return full_response

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ [TASK-{task.id}] Text generation failed after {elapsed:.2f}s: {e}")
            raise

    def _is_qwen3_model(self, model: str) -> bool:
        """Détecte si le modèle est un qwen3"""
        return 'qwen3' in model.lower() or 'qwen-3' in model.lower()

    def _build_system_prompt(self, is_qwen3: bool) -> str:
        """Construit le system prompt adapté au modèle (pour code)"""
        if is_qwen3:
            # /no_think désactive le thinking-mode de qwen3
            return (
                "/no_think\n"
                "Tu es un expert en développement logiciel. "
                "Génère directement le code demandé, sans préambule ni explication. "
                "Réponds en FRANÇAIS pour les commentaires de code. "
                "Inclus la gestion d'erreurs et des commentaires clairs. "
                "Ta réponse est écrite telle quelle dans un fichier : n'entoure JAMAIS "
                "le code de balises Markdown ``` et n'ajoute aucun commentaire hors du fichier."
            )
        return (
            "Tu es un expert en développement logiciel. "
            "Tu génères du code de qualité production avec des commentaires en français. "
            "Ta réponse est écrite telle quelle dans un fichier : n'entoure JAMAIS le code "
            "de balises Markdown ``` et n'ajoute ni introduction ni explication."
        )

    def _build_text_system_prompt(self, is_qwen3: bool) -> str:
        """Construit le system prompt pour du contenu texte (pas code)"""
        if is_qwen3:
            return (
                "/no_think\n"
                "Tu es un assistant expert. Réponds DIRECTEMENT en FRANÇAIS, "
                "sans raisonnement interne ni méta-commentaire. "
                "Produis un document structuré en Markdown (titres, listes, paragraphes). "
                "Ne génère PAS de code sauf demande explicite."
            )
        return (
            'Tu es un assistant expert. Génère du contenu structuré et actionnable. '
            'Utilise le format Markdown. Ne génère PAS de code sauf si explicitement demandé.'
        )

    def _get_llm_options(self, is_qwen3: bool) -> dict:
        """Options LLM adaptées au modèle"""
        if is_qwen3:
            return {
                'temperature': 0.6,
                'num_ctx': 32768,
                'num_predict': 8192,
                'top_p': 0.9,
                'top_k': 40,
                'repeat_penalty': 1.05,
                # /no_think bloque le mode thinking de qwen3 — sinon le modèle peut
                # rester bloqué dans le thinking sans jamais émettre de content
                'stop': ['<|im_end|>'],
            }
        return {
            'temperature': 0.7,
            # Le contexte d'atelier (plan de fichiers + code des autres tâches)
            # dépasse largement 4096 tokens : sans ça le prompt est tronqué.
            'num_ctx': 16384,
            'num_predict': 4096,
            'top_p': 0.9,
            'top_k': 40,
            'repeat_penalty': 1.1,
            # Pas de stop '' (coupe au 1er token sur Ollama récent) ni '\n\n\n'
            # (tronque le code contenant deux lignes vides consécutives)
            'stop': ['</s>'],
        }

    def _build_prompt(self, task: Task, is_qwen3: bool = False, workspace_context: Optional[str] = None,
                      document_context: Optional[str] = None) -> str:
        """Construit le prompt adapté au modèle, incluant le contexte d'atelier et le feedback"""
        # Section feedback si validation_notes existe (ajustement demandé)
        feedback_section = ""
        if hasattr(task, 'validation_notes') and task.validation_notes:
            if is_qwen3:
                feedback_section = f"\nPrevious feedback (IMPORTANT - address these points):\n{task.validation_notes}\n"
            else:
                feedback_section = f"\nFeedback précédent (IMPORTANT - prendre en compte ces remarques):\n{task.validation_notes}\n"
            logger.info(f"📝 [TASK-{task.id}] Including validation feedback in prompt: {task.validation_notes[:100]}...")

        # Contexte d'atelier : plan de fichiers du projet + code déjà produit par
        # les autres tâches. C'est ce qui permet au HTML de référencer le bon CSS.
        workspace_section = f"{workspace_context}\n\n---\n\n" if workspace_context else ""
        # Les documents de l'utilisateur passent AVANT le plan de fichiers : ils
        # font autorité sur tout le reste.
        if document_context:
            workspace_section = f"{document_context}\n\n---\n\n{workspace_section}"

        if is_qwen3:
            return f"""{workspace_section}Task: {task.title}
Description: {task.description or 'Not specified'}
Context: {task.llm_prompt or 'None'}
{feedback_section}
Generate production-quality code. Include error handling and clear comments.
Output ONLY the raw file content, with no explanations and no Markdown code fences."""
        return f"""{workspace_section}Tâche: {task.title}

Description: {task.description or 'Non spécifiée'}

Contexte: {task.llm_prompt}
{feedback_section}
Génère du code de qualité avec commentaires et gestion des erreurs.
Réponds UNIQUEMENT avec le contenu brut du fichier, sans phrase d'introduction et sans balises ```."""

    def _build_text_prompt(self, task: Task, is_qwen3: bool = False) -> str:
        """Construit le prompt pour du contenu texte (pas code) — research, admin, etc."""
        feedback_section = ""
        if hasattr(task, 'validation_notes') and task.validation_notes:
            if is_qwen3:
                feedback_section = f"\nPrevious feedback (IMPORTANT - address these points):\n{task.validation_notes}\n"
            else:
                feedback_section = f"\nFeedback précédent (IMPORTANT - prendre en compte ces remarques):\n{task.validation_notes}\n"
            logger.info(f"📝 [TASK-{task.id}] Including validation feedback in text prompt: {task.validation_notes[:100]}...")

        if is_qwen3:
            return f"""Task: {task.title}
Description: {task.description or 'Not specified'}
Context: {task.llm_prompt or 'None'}
{feedback_section}
Generate well-structured content in Markdown format. Be thorough, concrete and actionable.
Do NOT generate code unless explicitly asked. Focus on practical, human-readable content."""
        return f"""Tâche: {task.title}

Description: {task.description or 'Non spécifiée'}

Contexte: {task.llm_prompt}
{feedback_section}
Génère du contenu structuré en format Markdown. Sois complet, concret et actionnable.
Ne génère PAS de code sauf si explicitement demandé. Produis du contenu pratique et lisible."""

    def _select_model(self, task: Task, model_override: Optional[str] = None, user_settings: Optional[dict] = None, model_type: str = 'code') -> str:
        """
        Sélectionne le modèle selon les préférences utilisateur ou la config

        Args:
            task: Tâche à traiter
            model_override: Modèle spécifique à utiliser (priorité sur config)
            user_settings: Paramètres utilisateur avec préférences de modèles
            model_type: 'code' ou 'text' — détermine quelle préférence consulter

        Returns:
            Nom du modèle Ollama
        """
        # Priorité: model_override > user_settings > config globale
        if model_override:
            model = model_override
        elif user_settings:
            if model_type == 'text' and user_settings.get('ollama_model_text'):
                model = user_settings['ollama_model_text']
            elif 'ollama_model_code' in user_settings:
                model = user_settings['ollama_model_code']
            else:
                model = settings.OLLAMA_MODEL_CODE
        else:
            model = settings.OLLAMA_MODEL_CODE

        model = resolve_model(model, model_type)
        logger.info(f"📦 [TASK-{task.id}] Selected model ({model_type}): {model}")
        return model

    async def health_check(self) -> bool:
        """
        Vérifie que Ollama répond correctement

        Returns:
            True si Ollama est accessible, False sinon
        """
        try:
            start = time.time()
            self.client.list()
            elapsed = time.time() - start
            logger.info(f"✅ Ollama health check: OK ({elapsed*1000:.0f}ms)")
            return True
        except Exception as e:
            logger.error(f"❌ Ollama health check failed: {e}")
            return False

    def list_models(self) -> list[str]:
        """
        Liste les modèles disponibles sur Ollama avec un cache TTL de 5 minutes

        Returns:
            Liste des noms de modèles
        """
        if not hasattr(self, '_model_cache'):
            self._model_cache = {}

        current_time = time.time()
        ttl = 300  # 5 minutes in seconds

        if 'models' in self._model_cache and current_time - self._model_cache['timestamp'] < ttl:
            logger.info("Using cached models list")
            return self._model_cache['models']

        try:
            models = self.client.list()
            model_names = [model['name'] for model in models.get('models', [])]
            self._model_cache = {
                'models': model_names,
                'timestamp': current_time
            }
            logger.info(f"✅ Fetched and cached models list: {model_names}")
            return model_names
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []