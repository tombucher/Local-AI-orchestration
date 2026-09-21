"""
Module de génération de documents

Responsabilités :
- Rédaction de documents structurés
- Génération de budgets
- Création de rapports
- Adaptation du contenu selon le type de document
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
import ollama
from app.services.model_registry import resolve_model, think_kwargs
from app.services.modules.prompt_generator import PromptGeneratorModule, PromptTone

logger = logging.getLogger(__name__)


class DocumentGeneratorModule:
    """
    Module de génération de documents

    Utilisable pour :
    - Dossiers de financement
    - Rapports d'activité
    - Propositions de partenariat
    - Documentation technique
    """

    def __init__(self, ollama_host: str = "http://host.docker.internal:11434"):
        self.client = ollama.Client(host=ollama_host)
        self.prompt_generator = PromptGeneratorModule()
        logger.info(f"✅ DocumentGeneratorModule initialized")

    @staticmethod
    def _is_thinking_model(model: str) -> bool:
        """Modèles avec mode raisonnement natif (qwen3.x, deepseek-r1...)."""
        m = model.lower()
        return 'qwen3' in m or 'deepseek-r1' in m

    def _generate_with_llm(
        self,
        prompt: str,
        model: str = "mistral:7b-instruct-q4_K_M",
        max_tokens: int = 2000
    ) -> str:
        """Génère du texte avec le LLM"""
        model = resolve_model(model, "document")
        try:
            response = self.client.chat(
                model=model,
                messages=[
                    {
                        'role': 'system',
                        'content': 'Tu es un rédacteur professionnel expert en documents institutionnels et techniques.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                options={
                    'temperature': 0.7,
                    'num_predict': max_tokens,
                },
                # Désactive le mode thinking (qwen3.x) — sinon la réponse
                # part dans le champ thinking et le document sort vide
                **think_kwargs(model),
            )

            content = response['message'].get('content') or ''
            if not content.strip():
                thinking = response['message'].get('thinking') or ''
                raise RuntimeError(
                    f"Le modèle n'a produit aucun contenu (thinking: {len(thinking)} chars). "
                    "Essayez un autre modèle dans les paramètres."
                )
            return content

        except Exception as e:
            logger.error(f"Document generation failed: {e}")
            raise

    async def generate_document(
        self,
        document_type: str,
        context: Dict[str, Any],
        sections: List[Dict[str, Any]],
        tone: PromptTone = PromptTone.PROFESSIONAL,
        model: Optional[str] = None
    ) -> str:
        """
        Génère un document complet

        Args:
            document_type: Type de document
            context: Contexte (projet, organisation, etc.)
            sections: Liste de sections à générer
            tone: Ton du document
            model: Modèle LLM à utiliser (optionnel)

        Returns:
            Document généré au format Markdown
        """
        logger.info(f"Generating {document_type} document with {len(sections)} sections")

        # Génère le prompt
        prompt = self.prompt_generator.generate_document_prompt(
            document_type=document_type,
            context=context,
            sections=sections,
            tone=tone
        )

        # Calcul du nombre de tokens nécessaires
        total_words = sum(section.get('max_words', 500) for section in sections)
        max_tokens = int(total_words * 2)  # Marge de sécurité

        # Génération
        # Appel bloquant déporté dans un thread : sinon la rédaction d'un document
        # gèle toute l'API pendant plusieurs minutes.
        document = await asyncio.to_thread(
            self._generate_with_llm,
            prompt=prompt,
            model=model or "mistral",
            max_tokens=max_tokens
        )

        logger.info(f"✓ Generated {document_type} document ({len(document)} chars)")

        return document

    async def generate_funding_application(
        self,
        project_data: Dict[str, Any],
        funding_opportunity: Dict[str, Any],
        model: Optional[str] = None
    ) -> str:
        """
        Génère un dossier de demande de financement

        Args:
            project_data: Données du projet
            funding_opportunity: Détails de l'opportunité de financement
            model: Modèle LLM

        Returns:
            Dossier de demande
        """
        sections = [
            {
                "name": "Présentation de l'organisation",
                "max_words": 300,
                "required": True,
                "description": "Historique, mission, valeurs"
            },
            {
                "name": "Description du projet",
                "max_words": 600,
                "required": True,
                "description": "Objectifs, public cible, innovation"
            },
            {
                "name": "Méthodologie et plan d'action",
                "max_words": 500,
                "required": True,
                "description": "Étapes, calendrier, ressources"
            },
            {
                "name": "Budget prévisionnel",
                "max_words": 400,
                "required": True,
                "description": "Dépenses détaillées et sources de financement"
            },
            {
                "name": "Impact attendu et indicateurs",
                "max_words": 300,
                "required": True,
                "description": "Résultats mesurables, bénéficiaires"
            },
            {
                "name": "Pérennité du projet",
                "max_words": 200,
                "required": False,
                "description": "Stratégie de durabilité après financement"
            }
        ]

        context = {
            "organization": project_data.get("organization_name", ""),
            "project_name": project_data.get("project_name", ""),
            "funding_amount": funding_opportunity.get("amount", ""),
            "target_audience": "Commission de sélection",
            **project_data
        }

        return await self.generate_document(
            document_type="funding_application",
            context=context,
            sections=sections,
            tone=PromptTone.FORMAL,
            model=model
        )

    async def generate_activity_report(
        self,
        project_data: Dict[str, Any],
        period: Dict[str, str],
        activities: List[Dict[str, Any]],
        model: Optional[str] = None
    ) -> str:
        """
        Génère un rapport d'activité

        Args:
            project_data: Données du projet
            period: Période du rapport (start_date, end_date)
            activities: Liste des activités réalisées
            model: Modèle LLM

        Returns:
            Rapport d'activité
        """
        sections = [
            {
                "name": "Résumé exécutif",
                "max_words": 200,
                "required": True
            },
            {
                "name": "Activités réalisées",
                "max_words": 800,
                "required": True,
                "description": "Liste détaillée avec indicateurs"
            },
            {
                "name": "Résultats et impact",
                "max_words": 400,
                "required": True
            },
            {
                "name": "Difficultés rencontrées et solutions",
                "max_words": 300,
                "required": True
            },
            {
                "name": "Perspectives",
                "max_words": 200,
                "required": True
            }
        ]

        context = {
            "project_name": project_data.get("project_name", ""),
            "period_start": period.get("start_date", ""),
            "period_end": period.get("end_date", ""),
            "activities_count": len(activities),
            "target_audience": "Partenaires et financeurs",
            **project_data
        }

        return await self.generate_document(
            document_type="activity_report",
            context=context,
            sections=sections,
            tone=PromptTone.PROFESSIONAL,
            model=model
        )

    async def generate_budget(
        self,
        project_data: Dict[str, Any],
        budget_items: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Génère un budget prévisionnel au format tableau Markdown

        Args:
            project_data: Données du projet
            budget_items: Items de budget existants (optionnel)

        Returns:
            Budget au format Markdown
        """
        prompt = f"""Crée un budget prévisionnel détaillé pour ce projet.

## PROJET

Nom: {project_data.get('project_name', 'N/A')}
Type: {project_data.get('type', 'N/A')}
Durée: {project_data.get('duration', '12 mois')}
Description: {project_data.get('description', 'N/A')[:300]}

{self._format_existing_budget_items(budget_items)}

## FORMAT ATTENDU

Tableau Markdown avec les colonnes suivantes:
| Poste | Quantité | Prix unitaire (€) | Total (€) | Justification |

Catégories à inclure:
1. **Ressources Humaines** (salaires, honoraires)
2. **Matériel et équipement**
3. **Prestations externes**
4. **Communication et diffusion**
5. **Frais de fonctionnement**
6. **Imprévus** (10% du total)

Ajoute:
- Sous-total par catégorie
- **TOTAL GÉNÉRAL**

Sois réaliste et détaillé. Justifie brièvement chaque poste important.
"""

        budget = await asyncio.to_thread(self._generate_with_llm, prompt, max_tokens=1500)

        logger.info("✓ Generated budget")

        return budget

    async def generate_section(
        self,
        section_name: str,
        requirements: Dict[str, Any],
        context: Dict[str, Any],
        model: Optional[str] = None
    ) -> str:
        """
        Génère une section individuelle

        Args:
            section_name: Nom de la section
            requirements: Contraintes (max_words, tone, etc.)
            context: Contexte pour la génération
            model: Modèle LLM

        Returns:
            Contenu de la section
        """
        max_words = requirements.get('max_words', 500)
        tone = requirements.get('tone', 'professional')

        prompt = f"""Rédige la section "{section_name}" avec les contraintes suivantes.

## CONTEXTE

{self._format_context(context)}

## CONTRAINTES

- Longueur maximale: {max_words} mots
- Ton: {tone}
- Format: {requirements.get('format', 'paragraphe')}

{self._format_additional_requirements(requirements)}

## CONTENU

Rédige la section en respectant toutes les contraintes.
"""

        section = await asyncio.to_thread(
            self._generate_with_llm, prompt, max_tokens=max_words * 2, model=model or "mistral"
        )

        logger.info(f"✓ Generated section '{section_name}' ({len(section)} chars)")

        return section

    def _format_existing_budget_items(self, items: Optional[List[Dict[str, Any]]]) -> str:
        """Formate les items de budget existants"""
        if not items:
            return "## INSTRUCTIONS\n\nCrée un budget complet basé sur le projet."

        lines = ["## ITEMS DE BUDGET EXISTANTS\n"]
        for item in items:
            lines.append(f"- {item.get('name', 'N/A')}: {item.get('amount', 0)}€")

        lines.append("\nIntègre ces éléments dans le budget final.")

        return "\n".join(lines)

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Formate le contexte pour un prompt"""
        lines = []
        for key, value in context.items():
            if value:
                lines.append(f"**{key.replace('_', ' ').title()}:** {value}")

        return "\n".join(lines)

    def _format_additional_requirements(self, requirements: Dict[str, Any]) -> str:
        """Formate les exigences additionnelles"""
        lines = []

        if requirements.get('include_data'):
            lines.append("- Inclure des données chiffrées")

        if requirements.get('include_examples'):
            lines.append("- Fournir des exemples concrets")

        if requirements.get('focus_points'):
            lines.append(f"- Points à mettre en avant: {', '.join(requirements['focus_points'])}")

        return "\n".join(lines) if lines else ""
