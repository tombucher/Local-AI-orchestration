"""
Module de génération intelligente de prompts

Responsabilités :
- Génération de prompts contextuels
- Adaptation du ton et du style selon le contexte
- Enrichissement automatique avec le contexte du projet
- Templates de prompts réutilisables
"""
import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class PromptTone(str, Enum):
    """Tons de communication disponibles"""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    TECHNICAL = "technical"
    CREATIVE = "creative"
    FORMAL = "formal"


class PromptPurpose(str, Enum):
    """Objectifs des prompts"""
    CODE_GENERATION = "code_generation"
    DOCUMENT_WRITING = "document_writing"
    ANALYSIS = "analysis"
    RESEARCH = "research"
    SUMMARY = "summary"
    COMPREHENSION = "comprehension"


class PromptGeneratorModule:
    """
    Module de génération de prompts intelligents

    Utilisable pour :
    - Générer des prompts pour la compréhension de projet
    - Créer des prompts optimisés pour la génération de code
    - Adapter les prompts selon le contexte et l'objectif
    """

    def __init__(self):
        logger.info("✅ PromptGeneratorModule initialized")

    def generate_project_comprehension_prompt(
        self,
        project: Dict[str, Any],
        focus_areas: Optional[List[str]] = None
    ) -> str:
        """
        Génère un prompt pour comprendre un projet en profondeur

        Args:
            project: Informations du projet
            focus_areas: Domaines spécifiques à approfondir

        Returns:
            Prompt optimisé pour la compréhension
        """
        focus_areas = focus_areas or ["objectifs", "stack technique", "défis"]

        prompt = f"""Analyse en profondeur ce projet et fournis une compréhension structurée.

## INFORMATIONS DU PROJET

**Nom:** {project.get('name', 'N/A')}
**Type:** {project.get('type', 'N/A')}
**Statut:** {project.get('status', 'N/A')}

**Description:**
{project.get('description', 'Aucune description fournie')}

**Fonctionnalités activées:**
{self._format_features(project.get('features', {}))}

## DOMAINES À ANALYSER

{self._format_focus_areas(focus_areas)}

## FORMAT DE RÉPONSE ATTENDU

Structure ta réponse en sections claires:

1. **Vue d'ensemble** (2-3 phrases)
2. **Objectifs principaux** (liste à puces)
3. **Contexte technique** (si applicable)
4. **Enjeux et défis** (liste à puces)
5. **Recommandations** (2-3 suggestions concrètes)

Sois concis mais précis. Identifie les points clés qui guideront les actions futures.
"""

        return prompt

    def generate_code_prompt(
        self,
        task: Dict[str, Any],
        project_context: Dict[str, Any],
        coding_style: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Génère un prompt optimisé pour la génération de code

        Args:
            task: Informations de la tâche
            project_context: Contexte du projet
            coding_style: Préférences de style de code

        Returns:
            Prompt pour génération de code
        """
        coding_style = coding_style or {}

        prompt = f"""Génère du code de qualité production pour cette tâche.

## CONTEXTE DU PROJET

**Projet:** {project_context.get('name', 'N/A')}
**Type:** {project_context.get('type', 'N/A')}
**Description:** {project_context.get('description', 'N/A')[:200]}

## TÂCHE À RÉALISER

**Titre:** {task.get('title', 'N/A')}
**Description:** {task.get('description', 'Aucune description')}
**Priorité:** {task.get('priority', 'P2')}

{self._format_task_context(task)}

## CONSIGNES DE CODE

{self._format_coding_guidelines(coding_style)}

## LIVRABLES

1. Code fonctionnel et testé
2. Commentaires explicatifs (uniquement où nécessaire)
3. Gestion des erreurs appropriée
4. Code respectant les conventions du langage

**IMPORTANT:** Réponds UNIQUEMENT avec le code, sans markdown ni explications supplémentaires.
"""

        return prompt

    def generate_document_prompt(
        self,
        document_type: str,
        context: Dict[str, Any],
        sections: List[Dict[str, Any]],
        tone: PromptTone = PromptTone.PROFESSIONAL
    ) -> str:
        """
        Génère un prompt pour la rédaction de documents

        Args:
            document_type: Type de document (funding_application, report, etc.)
            context: Contexte (projet, organisation, etc.)
            sections: Sections à rédiger
            tone: Ton du document

        Returns:
            Prompt pour génération de document
        """
        prompt = f"""Rédige un document de type "{document_type}" de qualité {tone.value}.

## CONTEXTE

{self._format_document_context(context)}

## SECTIONS À RÉDIGER

{self._format_document_sections(sections)}

## CONSIGNES DE RÉDACTION

- Ton: {self._get_tone_description(tone)}
- Style: Clair, structuré, convaincant
- Longueur: Respecter les limites de mots par section

{self._get_document_type_guidelines(document_type)}

## FORMAT DE SORTIE

Fournis le document complet avec les titres de sections et le contenu rédigé.
"""

        return prompt

    def generate_search_query_prompt(
        self,
        intent: str,
        project_context: Dict[str, Any],
        keywords: List[str],
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Génère un prompt pour optimiser une requête de recherche

        Args:
            intent: Intention de recherche ("funding", "tech", "cultural", etc.)
            project_context: Contexte du projet
            keywords: Mots-clés initiaux
            filters: Filtres supplémentaires

        Returns:
            Prompt pour générer une query optimisée
        """
        prompt = f"""Génère une requête de recherche optimisée pour trouver des résultats pertinents.

## OBJECTIF DE RECHERCHE

Intention: {intent}

## CONTEXTE DU PROJET

Projet: {project_context.get('name', 'N/A')}
Description: {project_context.get('description', 'N/A')[:300]}

## MOTS-CLÉS INITIAUX

{', '.join(keywords)}

## FILTRES SOUHAITÉS

{self._format_filters(filters or {})}

## TÂCHE

Génère:
1. Une liste de mots-clés optimisés (français + anglais si pertinent)
2. Des variations et synonymes pertinents
3. Des mots-clés à exclure pour filtrer le bruit
4. Une requête booléenne si applicable

FORMAT:
KEYWORDS: [liste]
SYNONYMS: [liste]
EXCLUDE: [liste]
BOOLEAN_QUERY: [query]
"""

        return prompt

    def generate_analysis_prompt(
        self,
        content: str,
        analysis_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Génère un prompt pour analyser du contenu

        Args:
            content: Contenu à analyser
            analysis_type: Type d'analyse ("sentiment", "topics", "quality", etc.)
            context: Contexte additionnel

        Returns:
            Prompt d'analyse
        """
        prompt = f"""Analyse ce contenu selon le type d'analyse demandé: {analysis_type}

## CONTENU À ANALYSER

{content[:1500]}

## TYPE D'ANALYSE

{self._get_analysis_instructions(analysis_type)}

{self._format_analysis_context(context or {})}

Fournis une analyse structurée et actionnable.
"""

        return prompt

    # Helper methods

    def _format_features(self, features: Dict[str, Any]) -> str:
        """Formate les fonctionnalités du projet"""
        if not features:
            return "Aucune fonctionnalité spécifiée"

        lines = []
        for key, value in features.items():
            status = "✓" if value else "✗"
            lines.append(f"  {status} {key.replace('_', ' ').title()}")

        return "\n".join(lines)

    def _format_focus_areas(self, areas: List[str]) -> str:
        """Formate les domaines de focus"""
        return "\n".join([f"{i+1}. {area.title()}" for i, area in enumerate(areas)])

    def _format_task_context(self, task: Dict[str, Any]) -> str:
        """Formate le contexte spécifique de la tâche"""
        context_parts = []

        if task.get('llm_prompt'):
            context_parts.append(f"**Contexte additionnel:**\n{task['llm_prompt']}")

        if task.get('task_metadata'):
            metadata = task['task_metadata']
            if metadata:
                context_parts.append(f"**Métadonnées:**\n{self._format_metadata(metadata)}")

        return "\n\n".join(context_parts) if context_parts else ""

    def _format_coding_guidelines(self, style: Dict[str, Any]) -> str:
        """Formate les guidelines de code"""
        guidelines = [
            "- Code propre et maintenable",
            "- Noms de variables explicites",
            "- Fonctions courtes et focalisées",
            "- Gestion d'erreurs robuste"
        ]

        if style.get('language'):
            guidelines.append(f"- Langage: {style['language']}")
        if style.get('framework'):
            guidelines.append(f"- Framework: {style['framework']}")
        if style.get('max_line_length'):
            guidelines.append(f"- Longueur max ligne: {style['max_line_length']} caractères")

        return "\n".join(guidelines)

    def _format_document_context(self, context: Dict[str, Any]) -> str:
        """Formate le contexte du document"""
        parts = []

        if context.get('organization'):
            parts.append(f"**Organisation:** {context['organization']}")
        if context.get('project_name'):
            parts.append(f"**Projet:** {context['project_name']}")
        if context.get('target_audience'):
            parts.append(f"**Audience cible:** {context['target_audience']}")

        return "\n".join(parts)

    def _format_document_sections(self, sections: List[Dict[str, Any]]) -> str:
        """Formate les sections du document"""
        lines = []
        for i, section in enumerate(sections, 1):
            name = section.get('name', f'Section {i}')
            max_words = section.get('max_words', 'non spécifié')
            required = "✓ Requis" if section.get('required', True) else "Optionnel"

            lines.append(f"{i}. **{name}** ({required}, max {max_words} mots)")

            if section.get('description'):
                lines.append(f"   {section['description']}")

        return "\n".join(lines)

    def _get_tone_description(self, tone: PromptTone) -> str:
        """Retourne la description d'un ton"""
        descriptions = {
            PromptTone.PROFESSIONAL: "Professionnel, formel, respectueux",
            PromptTone.CASUAL: "Décontracté, accessible, amical",
            PromptTone.TECHNICAL: "Technique, précis, détaillé",
            PromptTone.CREATIVE: "Créatif, inspirant, innovant",
            PromptTone.FORMAL: "Très formel, institutionnel, protocolaire"
        }
        return descriptions.get(tone, "Professionnel")

    def _get_document_type_guidelines(self, doc_type: str) -> str:
        """Retourne des guidelines spécifiques par type de document"""
        guidelines = {
            "funding_application": "- Focus sur l'impact et la faisabilité\n- Quantifier les bénéfices attendus\n- Mettre en avant l'innovation",
            "activity_report": "- Données factuelles et chiffrées\n- Réalisations concrètes\n- Perspective sur les objectifs futurs",
            "partnership_proposal": "- Valeur ajoutée pour les deux parties\n- Opportunités de collaboration\n- Vision à long terme"
        }
        return guidelines.get(doc_type, "- Clarté et précision\n- Arguments convaincants")

    def _format_filters(self, filters: Dict[str, Any]) -> str:
        """Formate les filtres de recherche"""
        if not filters:
            return "Aucun filtre spécifique"

        lines = []
        for key, value in filters.items():
            lines.append(f"- {key.replace('_', ' ').title()}: {value}")

        return "\n".join(lines)

    def _get_analysis_instructions(self, analysis_type: str) -> str:
        """Retourne les instructions par type d'analyse"""
        instructions = {
            "sentiment": "Analyse le sentiment général (positif/négatif/neutre) et les émotions clés.",
            "topics": "Identifie les thématiques principales et les concepts clés abordés.",
            "quality": "Évalue la qualité du contenu (clarté, précision, utilité).",
            "structure": "Analyse la structure et l'organisation du contenu."
        }
        return instructions.get(analysis_type, "Analyse approfondie du contenu.")

    def _format_analysis_context(self, context: Dict[str, Any]) -> str:
        """Formate le contexte d'analyse"""
        if not context:
            return ""

        parts = ["## CONTEXTE ADDITIONNEL"]
        for key, value in context.items():
            parts.append(f"- {key.replace('_', ' ').title()}: {value}")

        return "\n".join(parts)

    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Formate les métadonnées"""
        lines = []
        for key, value in metadata.items():
            lines.append(f"  - {key}: {value}")
        return "\n".join(lines)
