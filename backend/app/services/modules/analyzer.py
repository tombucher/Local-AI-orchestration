"""
Module d'analyse de pertinence et scoring

Responsabilités :
- Analyse de pertinence par LLM
- Scoring et ranking
- Extraction d'informations clés
- Classification de contenu
"""
import asyncio
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
import ollama
from app.core.config import settings
from app.services.model_registry import resolve_model, think_kwargs

logger = logging.getLogger(__name__)


class AnalyzerModule:
    """
    Module d'analyse réutilisable

    Utilisable pour :
    - Scorer la pertinence d'un contenu par rapport à un projet
    - Extraire les points clés d'un texte
    - Classifier du contenu
    - Générer des résumés
    """

    def __init__(self, ollama_host: str = "http://host.docker.internal:11434"):
        self.client = ollama.Client(host=ollama_host)
        logger.info(f"✅ AnalyzerModule initialized with Ollama at {ollama_host}")

    @property
    def _FAST_FALLBACK_MODEL(self) -> str:
        """Modèle rapide pour les tâches courtes et structurées (requêtes, scoring),
        résolu vers un modèle réellement installé."""
        return resolve_model(settings.OLLAMA_MODEL_PROMPT, "rapide")

    def _generate_text(self, prompt: str, model: str = "mistral:7b-instruct-q4_K_M") -> str:
        """
        Génère du texte avec Ollama (SYNCHRONE — bloque le thread appelant)

        Pour les modèles thinking (qwen3.x), le contenu réel peut se retrouver dans
        le champ `thinking` plutôt que `content` avec l'ancienne API Ollama.
        Dans ce cas on fait un fallback sur mistral:7b qui répond de manière fiable
        en format structuré sans phase de raisonnement.

        Args:
            prompt: Prompt pour le LLM
            model: Modèle à utiliser

        Returns:
            Texte généré
        """
        # Les modèles thinking (qwen3, deepseek-r1) routent tout dans `thinking` avec
        # les vieilles versions Ollama (<0.7) et laissent `content` vide.
        # Pour les tâches structurées de l'analyzer (SCORE/RAISON/POINTS/ACTION),
        # on utilise directement le modèle rapide — plus fiable et 3x plus rapide.
        # Modèle réellement installé ; thinking désactivé nativement si supporté
        effective_model = resolve_model(model, "analyzer")

        try:
            response = self.client.chat(
                model=effective_model,
                messages=[
                    {
                        'role': 'system',
                        'content': 'Tu es un assistant d\'analyse intelligent et concis.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                options={
                    'temperature': 0.3,  # Bas pour plus de cohérence
                    'num_predict': 800,
                },
                **think_kwargs(effective_model),
            )
            content = response['message'].get('content') or ''
            if not content.strip():
                raise RuntimeError(f"Le modèle {effective_model} n'a produit aucun contenu")
            return content
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    async def _generate_text_async(self, prompt: str, model: str = "mistral:7b-instruct-q4_K_M") -> str:
        """
        Version async de _generate_text — exécute l'appel sync Ollama dans un thread
        pour ne pas bloquer l'event loop asyncio.
        """
        return await asyncio.to_thread(self._generate_text, prompt, model)

    async def analyze_relevance(
        self,
        content: Dict[str, Any],
        project_context: Dict[str, Any],
        keywords: List[str],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyse la pertinence d'un contenu par rapport à un projet

        Args:
            content: Contenu à analyser (avec title, description, etc.)
            project_context: Contexte du projet (name, description, type, etc.)
            keywords: Mots-clés du projet

        Returns:
            Dict avec score, raison, et points clés
            {
                "relevance_score": 0.85,  # 0-1
                "reason": "Ce contenu est pertinent car...",
                "key_points": ["point 1", "point 2"],
                "recommended_action": "saved" | "actionable" | "dismissed"
            }
        """
        # Prompt universel — s'adapte dynamiquement aux keywords et contexte du projet
        excluded = project_context.get('excluded_keywords', [])
        excluded_str = f"\nMots-clés EXCLUS (pénaliser fortement): {', '.join(excluded)}" if excluded else ""

        # L'objectif précis de la tâche de veille prend le dessus sur la description du projet
        task_objective = project_context.get('task_objective', '')
        if task_objective:
            objective_block = f"""
OBJECTIF PRÉCIS DE CETTE VEILLE :
{task_objective}

⚠ CONSIGNE PRIORITAIRE : Évalue la pertinence UNIQUEMENT par rapport à cet objectif précis.
- SCORE 0-30 : contenu hors-sujet (définitions génériques, tutoriels débutants, contenu non lié)
- SCORE 30-60 : contenu tangentiellement lié mais ne répond pas à l'objectif
- SCORE 60-80 : contenu utile et lié à l'objectif
- SCORE 80-100 : contenu qui répond directement à l'objectif (ressource, outil, exemple concret)
- Pénalise FORTEMENT : définitions Wikipédia, guides "comment débuter", publicités, contenu générique
"""
        else:
            objective_block = f"""
⚠ CONSIGNE STRICTE: Évalue la pertinence UNIQUEMENT par rapport aux mots-clés cibles et au contexte du projet.
- Pénalise FORTEMENT tout contenu hors-sujet, même s'il est de haute qualité.
- Un contenu n'est pertinent QUE s'il est directement lié aux mots-clés recherchés.
"""

        prompt = f"""Analyse la pertinence de ce contenu pour la veille suivante.
{objective_block}
PROJET:
Nom: {project_context.get('name', 'N/A')}
Type: {project_context.get('type', 'N/A')}
Mots-clés cibles: {', '.join(keywords)}{excluded_str}

CONTENU TROUVÉ:
Titre: {content.get('title', 'N/A')}
Description: {content.get('description', 'N/A')[:500]}
Source: {content.get('url', 'N/A')}

CONSIGNES:
1. Évalue la pertinence sur une échelle de 0 à 100 (STRICT — ne pas donner 50 par défaut)
2. Explique POURQUOI ce contenu est ou n'est pas pertinent pour l'objectif
3. Liste 2-3 points clés à retenir (ou pourquoi ce contenu est écarté)
4. Recommande une action: SAVE (très pertinent), ACTION (nécessite une action), ou DISMISS (peu pertinent)

FORMAT DE RÉPONSE (STRICT):
SCORE: [0-100]
RAISON: [explication courte]
POINTS:
- [point 1]
- [point 2]
- [point 3]
ACTION: [SAVE|ACTION|DISMISS]
"""

        response = await self._generate_text_async(prompt, model=model) if model else await self._generate_text_async(prompt)

        # Parse la réponse
        result = self._parse_relevance_response(response)

        logger.info(
            f"✓ Analyzed '{content.get('title', 'N/A')[:50]}...' → "
            f"Score: {result['relevance_score']}, Action: {result['recommended_action']}"
        )

        return result

    def _parse_relevance_response(self, response: str) -> Dict[str, Any]:
        """Parse la réponse LLM de l'analyse de pertinence"""

        # Extraction du score
        score_match = re.search(r'SCORE:\s*(\d+)', response, re.IGNORECASE)
        score = int(score_match.group(1)) if score_match else 50
        score = min(100, max(0, score))  # Clamp entre 0 et 100

        # Extraction de la raison
        reason_match = re.search(r'RAISON:\s*(.+?)(?=\nPOINTS:|$)', response, re.IGNORECASE | re.DOTALL)
        reason = reason_match.group(1).strip() if reason_match else "Analyse non disponible"

        # Extraction des points
        points_section = re.search(r'POINTS:\s*(.+?)(?=\nACTION:|$)', response, re.IGNORECASE | re.DOTALL)
        points = []
        if points_section:
            points_text = points_section.group(1)
            points = [
                line.strip().lstrip('-•*').strip()
                for line in points_text.split('\n')
                if line.strip() and line.strip().startswith(('-', '•', '*'))
            ]

        # Extraction de l'action
        action_match = re.search(r'ACTION:\s*(SAVE|ACTION|DISMISS)', response, re.IGNORECASE)
        action_map = {"SAVE": "saved", "ACTION": "actionable", "DISMISS": "dismissed"}
        action = action_map.get(action_match.group(1).upper() if action_match else "DISMISS", "dismissed")

        return {
            "relevance_score": score / 100.0,  # Normalize to 0-1
            "reason": reason,
            "key_points": points,
            "recommended_action": action
        }

    async def extract_key_information(
        self,
        content: str,
        info_type: str,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extrait des informations clés d'un contenu

        Args:
            content: Texte à analyser
            info_type: Type d'info ("funding_details", "event_details", "tech_specs", etc.)
            context: Contexte additionnel

        Returns:
            Dict avec informations extraites
        """
        if info_type == "funding_details":
            return await self._extract_funding_details(content, model=model)
        elif info_type == "event_details":
            return await self._extract_event_details(content, model=model)
        elif info_type == "tech_specs":
            return await self._extract_tech_specs(content, model=model)
        else:
            logger.warning(f"Unknown info_type: {info_type}")
            return {}

    async def _extract_funding_details(self, content: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Extrait les détails d'un appel d'offres / financement"""

        prompt = f"""Extrait les informations clés de cet appel d'offres ou financement.

CONTENU:
{content[:2000]}

Extrait et formate ces informations:
- Montant (en euros)
- Date limite de candidature
- Critères d'éligibilité
- Documents requis
- Thématiques / domaines concernés

FORMAT DE RÉPONSE (JSON):
{{
    "amount": "montant en euros ou 'non spécifié'",
    "deadline": "date au format YYYY-MM-DD ou 'non spécifié'",
    "eligibility": ["critère 1", "critère 2"],
    "required_documents": ["doc 1", "doc 2"],
    "themes": ["thème 1", "thème 2"]
}}
"""

        response = await self._generate_text_async(prompt, model=model) if model else await self._generate_text_async(prompt)

        import json
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            logger.warning("Failed to parse funding details JSON")

        return {
            "amount": "non spécifié",
            "deadline": "non spécifié",
            "eligibility": [],
            "required_documents": [],
            "themes": []
        }

    async def _extract_event_details(self, content: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Extrait les détails d'un événement (festival, expo, etc.)"""

        prompt = f"""Extrait les informations clés de cet événement.

CONTENU:
{content[:2000]}

Extrait et formate ces informations:
- Date de l'événement
- Lieu (ville, pays)
- Type d'événement (festival, exposition, conférence, etc.)
- Date limite de candidature (si applicable)
- Thématiques

FORMAT DE RÉPONSE (JSON):
{{
    "event_date": "YYYY-MM-DD ou période",
    "location": "ville, pays",
    "event_type": "type",
    "submission_deadline": "YYYY-MM-DD ou null",
    "themes": ["thème 1", "thème 2"]
}}
"""

        response = await self._generate_text_async(prompt, model=model) if model else await self._generate_text_async(prompt)

        import json
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            logger.warning("Failed to parse event details JSON")

        return {
            "event_date": "non spécifié",
            "location": "non spécifié",
            "event_type": "événement",
            "submission_deadline": None,
            "themes": []
        }

    async def _extract_tech_specs(self, content: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Extrait les specs techniques d'un outil/library"""

        prompt = f"""Extrait les informations techniques de cet outil/bibliothèque.

CONTENU:
{content[:2000]}

Extrait:
- Langage de programmation
- License
- Dernière mise à jour
- Popularité (stars, downloads)
- Cas d'usage principaux

FORMAT DE RÉPONSE (JSON):
{{
    "language": "langage",
    "license": "license",
    "last_update": "date",
    "popularity": "metric",
    "use_cases": ["cas 1", "cas 2"]
}}
"""

        response = await self._generate_text_async(prompt, model=model) if model else await self._generate_text_async(prompt)

        import json
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            logger.warning("Failed to parse tech specs JSON")

        return {
            "language": "non spécifié",
            "license": "non spécifié",
            "last_update": "non spécifié",
            "popularity": "non spécifié",
            "use_cases": []
        }

    async def generate_summary(self, content: str, max_words: int = 100, model: Optional[str] = None) -> str:
        """
        Génère un résumé concis

        Args:
            content: Texte à résumer
            max_words: Nombre max de mots

        Returns:
            Résumé
        """
        prompt = f"""Résume ce contenu en {max_words} mots maximum. Sois concis et précis.

CONTENU:
{content[:2000]}

RÉSUMÉ:"""

        summary = await self._generate_text_async(prompt, model=model) if model else await self._generate_text_async(prompt)
        return summary.strip()

    async def generate_radar_report(
        self,
        analyzed_results: List[Dict[str, Any]],
        project_context: Dict[str, Any],
        keywords: List[str],
        total_scanned: int,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Génère un Rapport Radar structuré à partir des résultats de veille analysés.

        Args:
            analyzed_results: Liste de dicts {title, url, description, relevance_score, reason, key_points, ai_summary}
            project_context: Contexte du projet
            keywords: Mots-clés actuels
            total_scanned: Nombre total de résultats scannés (avant filtrage)
            model: Modèle LLM à utiliser

        Returns:
            Dict structuré Radar: {pepites, stats, affinage}
        """
        if not analyzed_results:
            return self._build_empty_radar(keywords, total_scanned)

        # Construire le résumé des résultats pour le LLM
        results_summary = []
        for i, r in enumerate(analyzed_results[:15], 1):
            results_summary.append(
                f"{i}. [{r.get('relevance_score', 0):.0f}%] {r.get('title', 'N/A')}\n"
                f"   Lien: {r.get('url', 'N/A')}\n"
                f"   Raison: {r.get('reason', 'N/A')}"
            )
        results_text = "\n".join(results_summary)

        excluded = project_context.get('excluded_keywords', [])
        excluded_str = ', '.join(excluded) if excluded else 'aucun'

        prompt = f"""Tu es un assistant de veille. Analyse ces résultats et produis un rapport Radar.

PROJET: {project_context.get('name', 'N/A')}
DESCRIPTION: {project_context.get('description', 'N/A')}
MOTS-CLÉS ACTUELS: {', '.join(keywords)}
MOTS-CLÉS EXCLUS: {excluded_str}

RÉSULTATS TROUVÉS ({len(analyzed_results)} pertinents sur {total_scanned} scannés):
{results_text}

MISSION: Produis un rapport Radar JSON avec:
1. "pepites": les 5 meilleurs résultats (ou moins si pas assez), avec name, synthesis (2 phrases max), link, relevance_score
2. "suggested_additions": 2-3 mots-clés à AJOUTER pour affiner les prochaines recherches (basé sur les tendances observées)
3. "suggested_exclusions": 1-2 mots-clés à EXCLURE pour filtrer le bruit
4. "reasoning": 1 phrase expliquant la logique d'affinage

RÉPONDS UNIQUEMENT avec du JSON valide, sans texte avant ou après:
{{
    "pepites": [
        {{"name": "...", "synthesis": "...", "link": "...", "relevance_score": 85}}
    ],
    "suggested_additions": ["mot1", "mot2"],
    "suggested_exclusions": ["mot3"],
    "reasoning": "..."
}}"""

        try:
            response = await self._generate_text_async(prompt, model=model) if model else await self._generate_text_async(prompt)

            # Nettoyer les tags <think> si qwen3
            response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)

            # Extraire le JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                llm_data = json.loads(json_match.group())
            else:
                logger.warning("No JSON found in Radar LLM response, using fallback")
                llm_data = {}
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse Radar report JSON: {e}")
            llm_data = {}

        # Construire le rapport final (combiner LLM + données réelles)
        pepites_from_llm = llm_data.get('pepites', [])

        # Si le LLM n'a pas produit de pépites, construire depuis les résultats triés
        if not pepites_from_llm:
            sorted_results = sorted(analyzed_results, key=lambda x: x.get('relevance_score', 0), reverse=True)
            pepites_from_llm = [
                {
                    "name": r.get('title', 'Sans titre'),
                    "synthesis": r.get('ai_summary', r.get('reason', 'Résultat pertinent')),
                    "link": r.get('url', ''),
                    "relevance_score": r.get('relevance_score', 0) * 100 if r.get('relevance_score', 0) <= 1 else r.get('relevance_score', 0)
                }
                for r in sorted_results[:5]
            ]

        # Associer les result_id si possible
        for pepite in pepites_from_llm:
            pepite_link = pepite.get('link', '')
            for r in analyzed_results:
                if r.get('url') == pepite_link and 'result_id' in r:
                    pepite['result_id'] = r['result_id']
                    break

        # Stats calculées depuis les données réelles
        scores = [r.get('relevance_score', 0) for r in analyzed_results]
        # Normaliser les scores (peuvent être 0-1 ou 0-100)
        scores_100 = [s * 100 if s <= 1 else s for s in scores]
        avg_score = sum(scores_100) / len(scores_100) if scores_100 else 0

        sources = list(set(r.get('source_platform', 'Web') for r in analyzed_results if r.get('source_platform')))

        radar = {
            "pepites": pepites_from_llm[:5],
            "stats": {
                "total_scanned": total_scanned,
                "total_relevant": len(analyzed_results),
                "avg_score": round(avg_score, 1),
                "top_sources": sources or ["DuckDuckGo"],
                "scan_date": datetime.utcnow().strftime("%Y-%m-%d")
            },
            "affinage": {
                "current_keywords": keywords,
                "suggested_additions": llm_data.get('suggested_additions', []),
                "suggested_removals": [],
                "suggested_exclusions": llm_data.get('suggested_exclusions', []),
                "reasoning": llm_data.get('reasoning', "Affinage automatique basé sur les résultats observés.")
            }
        }

        logger.info(
            f"📊 Radar report generated: {len(radar['pepites'])} pépites, "
            f"avg score {avg_score:.0f}%, {total_scanned} scanned"
        )

        return radar

    def _build_empty_radar(self, keywords: List[str], total_scanned: int) -> Dict[str, Any]:
        """Construit un Radar vide quand aucun résultat pertinent"""
        return {
            "pepites": [],
            "stats": {
                "total_scanned": total_scanned,
                "total_relevant": 0,
                "avg_score": 0,
                "top_sources": [],
                "scan_date": datetime.utcnow().strftime("%Y-%m-%d")
            },
            "affinage": {
                "current_keywords": keywords,
                "suggested_additions": [],
                "suggested_removals": [],
                "suggested_exclusions": [],
                "reasoning": "Aucun résultat pertinent trouvé. Essayez d'élargir vos mots-clés."
            }
        }
