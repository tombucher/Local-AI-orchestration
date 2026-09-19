"""
Modules fonctionnels réutilisables

Architecture modulaire où chaque module a une responsabilité unique :
- WebResearchModule : Recherche et extraction d'informations sur le web
- PromptGeneratorModule : Génération intelligente de prompts contextuels
- AnalyzerModule : Analyse de pertinence et scoring
- DocumentGeneratorModule : Rédaction assistée de documents
- CodeGeneratorModule : Génération de code (refactorisé)
"""

from app.services.modules.web_research import WebResearchModule
from app.services.modules.prompt_generator import PromptGeneratorModule
from app.services.modules.analyzer import AnalyzerModule
from app.services.modules.document_generator import DocumentGeneratorModule

__all__ = [
    "WebResearchModule",
    "PromptGeneratorModule",
    "AnalyzerModule",
    "DocumentGeneratorModule",
]
