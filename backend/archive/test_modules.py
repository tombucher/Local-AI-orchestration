"""
Script de test pour les modules de l'orchestrateur

Usage:
    docker-compose exec backend python test_modules.py
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.modules import WebResearchModule, AnalyzerModule, PromptGeneratorModule, DocumentGeneratorModule


async def test_web_research():
    """Test du module de recherche web"""
    print("\n" + "="*60)
    print("TEST: WebResearchModule")
    print("="*60)

    async with WebResearchModule() as research:
        # Test recherche GitHub
        print("\n🔍 Recherche GitHub: FastAPI...")
        results = await research.search_github(
            keywords=["FastAPI"],
            language="Python",
            min_stars=1000
        )
        print(f"✓ Trouvé {len(results)} repositories")
        if results:
            print(f"  Exemple: {results[0]['title']} ({results[0]['stars']} stars)")

        # Test Hacker News
        print("\n🔍 Recherche Hacker News: AI...")
        hn_results = await research.search_hackernews(
            keywords=["artificial intelligence"],
            days=7
        )
        print(f"✓ Trouvé {len(hn_results)} articles HN")
        if hn_results:
            print(f"  Exemple: {hn_results[0]['title']} ({hn_results[0]['points']} points)")


async def test_analyzer():
    """Test du module d'analyse"""
    print("\n" + "="*60)
    print("TEST: AnalyzerModule")
    print("="*60)

    analyzer = AnalyzerModule()

    # Test analyse de pertinence
    print("\n🧠 Analyse de pertinence...")
    content = {
        "title": "FastAPI for building APIs with AI integration",
        "description": "A modern Python framework for building APIs with machine learning models",
        "url": "https://example.com"
    }

    project_context = {
        "name": "API de Gestion de Tâches IA",
        "description": "API REST avec génération de code assistée par IA",
        "type": "technical"
    }

    analysis = await analyzer.analyze_relevance(
        content=content,
        project_context=project_context,
        keywords=["FastAPI", "AI", "API"]
    )

    print(f"✓ Score de pertinence: {analysis['relevance_score']:.0%}")
    print(f"✓ Raison: {analysis['reason'][:100]}...")
    print(f"✓ Points clés: {len(analysis['key_points'])} points")
    print(f"✓ Action recommandée: {analysis['recommended_action']}")

    # Test génération de résumé
    print("\n📝 Génération de résumé...")
    long_text = """
    FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.7+
    based on standard Python type hints. The key features are: Fast to code, fewer bugs, intuitive,
    easy, short, robust, and standards-based. It's one of the fastest Python frameworks available,
    on par with NodeJS and Go. It's based on Pydantic and type hints.
    """

    summary = await analyzer.generate_summary(long_text, max_words=50)
    print(f"✓ Résumé: {summary}")


async def test_prompt_generator():
    """Test du module de génération de prompts"""
    print("\n" + "="*60)
    print("TEST: PromptGeneratorModule")
    print("="*60)

    prompt_gen = PromptGeneratorModule()

    # Test génération de prompt de code
    print("\n💻 Génération de prompt pour code...")
    task = {
        "title": "Créer une API REST pour les utilisateurs",
        "description": "Endpoints CRUD pour gérer les utilisateurs",
        "priority": "P1"
    }

    project_context = {
        "name": "Mon API",
        "type": "technical",
        "description": "API REST avec FastAPI"
    }

    code_prompt = prompt_gen.generate_code_prompt(
        task=task,
        project_context=project_context,
        coding_style={"language": "Python", "framework": "FastAPI"}
    )

    print(f"✓ Prompt généré ({len(code_prompt)} caractères)")
    print(f"  Extrait: {code_prompt[:200]}...")

    # Test génération de prompt de compréhension
    print("\n🤔 Génération de prompt de compréhension...")
    project = {
        "name": "Association Arts Numériques",
        "type": "association",
        "status": "active",
        "description": "Association promouvant l'art numérique et l'écologie",
        "features": {"veille": True, "doc_automation": True}
    }

    comprehension_prompt = prompt_gen.generate_project_comprehension_prompt(
        project=project,
        focus_areas=["objectifs", "public cible", "besoins"]
    )

    print(f"✓ Prompt généré ({len(comprehension_prompt)} caractères)")


async def test_document_generator():
    """Test du module de génération de documents"""
    print("\n" + "="*60)
    print("TEST: DocumentGeneratorModule")
    print("="*60)

    doc_gen = DocumentGeneratorModule()

    # Test génération de budget
    print("\n💰 Génération de budget...")
    project_data = {
        "project_name": "Compostage de Données Numériques",
        "type": "artistic",
        "description": "Installation artistique interactive",
        "duration": "18 mois"
    }

    budget = await doc_gen.generate_budget(
        project_data=project_data,
        budget_items=[
            {"name": "Développement installation", "amount": 15000},
            {"name": "Matériel électronique", "amount": 8000}
        ]
    )

    print(f"✓ Budget généré ({len(budget)} caractères)")
    print("  Extrait:")
    print(budget[:300] + "...")


async def main():
    """Lance tous les tests"""
    print("\n" + "🧪"*30)
    print("TESTS DES MODULES DE L'ORCHESTRATEUR")
    print("🧪"*30)

    try:
        await test_web_research()
        await test_analyzer()
        await test_prompt_generator()
        await test_document_generator()

        print("\n" + "="*60)
        print("✅ TOUS LES TESTS SONT PASSÉS !")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
