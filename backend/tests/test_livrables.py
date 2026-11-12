"""
Livrables utilisables : documents sans gabarit, recherche qui cherche.

Constat du 11/11/2026 : sur un vrai appel d'offres, huit tâches terminées et
rien d'utilisable — mémoire en trois paragraphes, devis sans montant,
« recherche » réduite à un plan, cahier des charges tronqué.
"""

import inspect

from app.services.livrables import parser_requetes, prompt_document, prompt_synthese
from app.services import project_documents


def test_prompt_document_porte_brief_plan_documents_et_regles():
    prompt = prompt_document(
        project_name="Festival", project_description="Identité visuelle d'un festival.",
        brief="Rédiger l'offre financière", plan=["Conception", "Moteur génératif"],
        documents="## Documents de référence\nCAHIER DES CHARGES : date limite 18 novembre",
        upstream="## Résultats des tâches précédentes\nConcept : contenant stable",
        feedback="Trop vague la dernière fois",
    )
    for attendu in ("Rédiger l'offre financière", "- Conception", "- Moteur génératif",
                    "date limite 18 novembre", "contenant stable", "Trop vague",
                    "[À COMPLÉTER", "tableau Markdown", "hexadécimal"):
        assert attendu in prompt
    # Plus de gabarit imposé ni de plafond par section
    assert "Introduction" not in prompt and "mots" not in prompt.lower().split("longueur")[0]


def test_parser_requetes_nettoie_puces_numeros_et_bavardage():
    texte = """Voici les requêtes :
1. appel d'offres Vénissieux festival identité visuelle 2026
- "Fêtes Escales Vénissieux affiche 2025"
• BOAMP Vénissieux graphisme festival
ok
"""
    assert parser_requetes(texte) == [
        "appel d'offres Vénissieux festival identité visuelle 2026",
        "Fêtes Escales Vénissieux affiche 2025",
        "BOAMP Vénissieux graphisme festival",
    ]
    assert parser_requetes("") == []


def test_prompt_synthese_numerote_les_sources_et_interdit_le_plan():
    prompt = prompt_synthese(
        project_name="Festival", project_description="",
        brief="Quelle était l'identité des Fêtes Escales ?",
        requetes=["Fêtes Escales Vénissieux"],
        sources=[{"title": "Vénissieux.fr", "url": "https://venissieux.fr/fetes", "text": "Les Fêtes Escales 2025…"},
                 {"title": "", "url": "https://leprogres.fr/a", "text": "Article"}],
    )
    assert "[1] Vénissieux.fr — https://venissieux.fr/fetes" in prompt
    assert "[2] https://leprogres.fr/a — https://leprogres.fr/a" in prompt
    assert "Ce que les sources ne disent pas" in prompt
    assert "ni plan de recherche" in prompt

    sans = prompt_synthese(project_name="P", project_description=None, brief="b", requetes=[], sources=[])
    assert "Aucune page exploitable" in sans


def test_recherche_cherche_vraiment_et_redaction_sans_gabarit():
    from app.services.unified_orchestrator import UnifiedOrchestrator

    recherche = inspect.getsource(UnifiedOrchestrator._handle_research)
    assert "_collect_sources" in recherche and "prompt_synthese" in recherche
    assert "plan de recherche structuré" not in recherche

    redaction = inspect.getsource(UnifiedOrchestrator._handle_document_writing)
    assert "write_deliverable" in redaction and "generate_document(" not in redaction


def test_un_cahier_des_charges_entier_tient_dans_le_contexte():
    # 8 361 caractères : la taille du vrai cahier des charges qui arrivait tronqué
    assert project_documents.MAX_CHARS_PER_DOCUMENT >= 8361
    assert project_documents.MAX_CONTEXT_CHARS >= project_documents.MAX_CHARS_PER_DOCUMENT
