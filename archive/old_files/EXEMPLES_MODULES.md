# Exemples d'Utilisation des Modules

## Architecture Modulaire

Les modules sont **indépendants et réutilisables**. Vous pouvez les combiner pour créer des workflows complexes.

```
WebResearchModule → AnalyzerModule → DocumentGeneratorModule
                         ↓
                  PromptGeneratorModule
```

---

## 1. Cas d'Usage : Veille pour une Association

### Objectif
Trouver des opportunités de financement pour une association culturelle.

### Workflow

```python
from app.services.modules import WebResearchModule, AnalyzerModule
from app.models import VeilleTopic, VeilleResult, VeilleScope, VeilleResultType

# Configuration du sujet de veille
topic = VeilleTopic(
    project_id=1,
    name="Financements culture numérique",
    scope=VeilleScope.FUNDING,
    keywords=["subvention", "association", "culture numérique", "innovation"],
    min_relevance_score=70  # Seuil de pertinence
)

# 1. RECHERCHE WEB
async with WebResearchModule() as research:
    # Recherche sur data.gouv.fr
    results_datagouv = await research.search_data_gouv(
        keywords=topic.keywords,
        organization="ministere-culture"
    )

    # Recherche sur d'autres sources (RSS, APIs, etc.)
    rss_results = await research.fetch_rss_feed(
        "https://www.culture.gouv.fr/rss/appels-projets.xml"
    )

# 2. ANALYSE DE PERTINENCE
analyzer = AnalyzerModule()

filtered_results = []
for result in results_datagouv:
    # Analyse la pertinence
    analysis = await analyzer.analyze_relevance(
        content=result,
        project_context={
            "name": "Association Arts Numériques",
            "description": "Association promouvant l'art numérique et l'écologie",
            "type": "association"
        },
        keywords=topic.keywords
    )

    # Filtrage selon le score
    if analysis['relevance_score'] >= 0.7:
        # Extraction des détails du financement
        funding_details = await analyzer.extract_key_information(
            content=result['description'],
            info_type="funding_details"
        )

        # Sauvegarde en BDD
        veille_result = VeilleResult(
            topic_id=topic.id,
            result_type=VeilleResultType.FUNDING_OPPORTUNITY,
            title=result['title'],
            url=result['url'],
            description=result['description'],
            ai_summary=await analyzer.generate_summary(result['description']),
            relevance_score=analysis['relevance_score'] * 100,
            key_points=analysis['key_points'],
            relevance_reason=analysis['reason'],
            result_metadata=funding_details,
            status=analysis['recommended_action']
        )

        filtered_results.append(veille_result)

print(f"✓ Trouvé {len(filtered_results)} opportunités pertinentes")
```

---

## 2. Cas d'Usage : Veille Culturelle pour Projet Artistique

### Objectif
Trouver des festivals et expositions pour un projet de "compostage numérique".

### Workflow

```python
from app.services.modules import WebResearchModule, AnalyzerModule

# Configuration
keywords = ["compostage", "art numérique", "data art", "écologie", "média art"]
location_filters = {
    "country": "FR",
    "region": "IDF",  # Île-de-France
    "radius_km": 200
}

# 1. RECHERCHE WEB
async with WebResearchModule() as research:
    # Recherche de festivals (via scraping ou APIs)
    festivals = await research.scrape_multiple(
        urls=[
            "https://www.artsy.net/shows",
            "https://www.festivals-fr.com/art-numerique"
        ],
        selectors={
            "title": "h2.event-title",
            "date": "span.event-date",
            "location": "span.event-location",
            "description": "div.event-description"
        }
    )

    # Flux RSS spécialisés
    rss_events = await research.fetch_rss_feed(
        "https://www.artfairs.net/rss/digital-art"
    )

# 2. ANALYSE ET FILTRAGE
analyzer = AnalyzerModule()

relevant_events = []
for event in festivals + rss_events:
    analysis = await analyzer.analyze_relevance(
        content=event,
        project_context={
            "name": "Compostage de Données Numériques",
            "description": "Installation artistique questionnant la vie et la mort des données numériques à travers une métaphore du compostage",
            "type": "artistic"
        },
        keywords=keywords
    )

    if analysis['relevance_score'] >= 0.6:
        # Extraction des détails de l'événement
        event_details = await analyzer.extract_key_information(
            content=event['description'],
            info_type="event_details"
        )

        # Filtrage géographique
        if location_filters and event_details.get('location'):
            location = event_details['location']
            # Vérifier si dans le périmètre (simplifié ici)
            if location_filters['country'] in location:
                relevant_events.append({
                    **event,
                    **event_details,
                    "relevance_score": analysis['relevance_score'],
                    "reason": analysis['reason']
                })

print(f"✓ Trouvé {len(relevant_events)} événements pertinents")

# Tri par score de pertinence
relevant_events.sort(key=lambda x: x['relevance_score'], reverse=True)

# Affichage des top 5
for event in relevant_events[:5]:
    print(f"\n{event['title']} (Score: {event['relevance_score']:.0%})")
    print(f"  📍 {event.get('location', 'N/A')}")
    print(f"  📅 {event.get('event_date', 'N/A')}")
    print(f"  💡 {event['reason']}")
```

---

## 3. Cas d'Usage : Génération de Dossier de Financement

### Objectif
Générer automatiquement un dossier de demande de financement.

### Workflow

```python
from app.services.modules import DocumentGeneratorModule, PromptGeneratorModule

# Données du projet
project_data = {
    "organization_name": "Association Arts Numériques Paris",
    "project_name": "Compostage de Données Numériques",
    "description": "Installation artistique interactive questionnant la vie et la mort des données numériques...",
    "budget_requested": 50000,
    "duration": "18 mois",
    "team_size": 5,
    "previous_projects": ["Exposition Data Rivers 2024", "Résidence Numérique 2023"]
}

# Détails de l'opportunité de financement (récupérés via veille)
funding_opportunity = {
    "name": "Appel à projet Culture Numérique 2026",
    "amount": "jusqu'à 50000€",
    "deadline": "2026-06-01",
    "themes": ["innovation", "culture numérique", "écologie"]
}

# 1. GÉNÉRATION DU DOSSIER
doc_gen = DocumentGeneratorModule()

funding_application = await doc_gen.generate_funding_application(
    project_data=project_data,
    funding_opportunity=funding_opportunity,
    model="mistral"  # ou "mixtral" pour plus de qualité
)

print("📄 Dossier généré :")
print(funding_application)

# 2. GÉNÉRATION DU BUDGET
budget = await doc_gen.generate_budget(
    project_data=project_data,
    budget_items=[
        {"name": "Développement installation interactive", "amount": 15000},
        {"name": "Matériel électronique", "amount": 8000},
        {"name": "Communication et médiation", "amount": 5000}
    ]
)

print("\n💰 Budget généré :")
print(budget)

# 3. SAUVEGARDE
with open(f"dossier_financement_{project_data['project_name']}.md", "w") as f:
    f.write(funding_application)
    f.write("\n\n---\n\n")
    f.write(budget)

print("✅ Dossier sauvegardé !")
```

---

## 4. Cas d'Usage : Veille Technologique

### Objectif
Suivre les nouvelles technologies pour un projet technique.

### Workflow

```python
from app.services.modules import WebResearchModule, AnalyzerModule, PromptGeneratorModule

# 1. GÉNÉRATION DE QUERY OPTIMISÉE
prompt_gen = PromptGeneratorModule()

search_query_prompt = prompt_gen.generate_search_query_prompt(
    intent="tech",
    project_context={
        "name": "API de Gestion de Tâches IA",
        "description": "API REST avec génération de code assistée par IA"
    },
    keywords=["FastAPI", "LLM", "code generation", "task management"],
    filters={"language": "Python", "min_stars": 100}
)

# Utiliser le LLM pour optimiser la query
# (simplifié ici)

# 2. RECHERCHE MULTI-SOURCES
async with WebResearchModule() as research:
    # GitHub
    github_results = await research.search_github(
        keywords=["FastAPI", "LLM", "code generation"],
        language="Python",
        min_stars=100
    )

    # Hacker News
    hn_results = await research.search_hackernews(
        keywords=["FastAPI", "LLM integration"],
        days=30
    )

# 3. ANALYSE ET RANKING
analyzer = AnalyzerModule()

tech_findings = []
for repo in github_results:
    analysis = await analyzer.analyze_relevance(
        content=repo,
        project_context={
            "name": "API de Gestion de Tâches IA",
            "type": "technical"
        },
        keywords=["FastAPI", "LLM", "AI", "code generation"]
    )

    if analysis['relevance_score'] >= 0.7:
        tech_specs = await analyzer.extract_key_information(
            content=repo['description'],
            info_type="tech_specs"
        )

        tech_findings.append({
            **repo,
            **tech_specs,
            **analysis
        })

# 4. GÉNÉRATION D'UN DIGEST HEBDOMADAIRE
digest_sections = [
    {"name": "Top 3 des découvertes", "max_words": 200},
    {"name": "Tendances observées", "max_words": 150},
    {"name": "Recommandations", "max_words": 100}
]

doc_gen = DocumentGeneratorModule()
weekly_digest = await doc_gen.generate_document(
    document_type="tech_digest",
    context={
        "project_name": "Veille Tech - API IA",
        "period": "Semaine 1 - Janvier 2026",
        "findings_count": len(tech_findings)
    },
    sections=digest_sections
)

print(weekly_digest)
```

---

## 5. Cas d'Usage : Compréhension de Projet

### Objectif
Analyser en profondeur un projet pour générer des prompts adaptés.

### Workflow

```python
from app.services.modules import PromptGeneratorModule, AnalyzerModule

# Données du projet (depuis BDD)
project = {
    "name": "Association Solidarité Numérique",
    "type": "association",
    "status": "active",
    "description": "Association aidant les personnes en précarité numérique...",
    "features": {
        "code_gen": False,
        "veille": True,
        "doc_automation": True
    }
}

# 1. GÉNÉRATION DE PROMPT DE COMPRÉHENSION
prompt_gen = PromptGeneratorModule()

comprehension_prompt = prompt_gen.generate_project_comprehension_prompt(
    project=project,
    focus_areas=["objectifs", "public cible", "besoins en financement", "partenariats"]
)

# 2. ANALYSE AVEC LLM
analyzer = AnalyzerModule()
# Utiliser le prompt avec le LLM pour obtenir une analyse approfondie
# (le LLM retournerait une analyse structurée)

# 3. GÉNÉRATION DE PROMPTS ADAPTÉS
# Une fois le projet compris, générer des prompts sur mesure

# Pour une tâche de recherche de financement:
funding_search_prompt = prompt_gen.generate_search_query_prompt(
    intent="funding",
    project_context=project,
    keywords=["inclusion numérique", "précarité", "formation"],
    filters={"region": "IDF", "min_amount": 10000}
)

# Pour une tâche de rédaction:
doc_prompt = prompt_gen.generate_document_prompt(
    document_type="partnership_proposal",
    context={
        "organization": project['name'],
        "project_name": "Programme d'Inclusion Numérique 2026",
        "target_audience": "Collectivités territoriales"
    },
    sections=[
        {"name": "Présentation", "max_words": 200},
        {"name": "Proposition de collaboration", "max_words": 400},
        {"name": "Bénéfices mutuels", "max_words": 300}
    ]
)

print("✓ Prompts générés et adaptés au contexte du projet")
```

---

## 6. Combinaison Complète : Pipeline Automatisé

### Objectif
Pipeline complet : Veille → Analyse → Génération de document

```python
async def pipeline_veille_complete(project_id: int, topic: VeilleTopic):
    """
    Pipeline automatisé de veille avec génération de document

    Étapes:
    1. Recherche web sur sources configurées
    2. Analyse et filtrage par pertinence
    3. Extraction d'informations clés
    4. Génération d'un digest hebdomadaire
    5. Notification utilisateur si opportunités hautement pertinentes
    """

    # Modules
    async with WebResearchModule() as research:
        analyzer = AnalyzerModule()
        doc_gen = DocumentGeneratorModule()

        # 1. RECHERCHE
        all_results = []

        if topic.scope == VeilleScope.FUNDING:
            results = await research.search_data_gouv(
                keywords=topic.keywords
            )
            all_results.extend(results)

        elif topic.scope == VeilleScope.CULTURAL:
            # Sources culturelles
            for source_url in topic.sources:
                if source_url.endswith('.xml') or source_url.endswith('.rss'):
                    results = await research.fetch_rss_feed(source_url)
                    all_results.extend(results)

        elif topic.scope == VeilleScope.TECH:
            github_results = await research.search_github(
                keywords=topic.keywords,
                min_stars=50
            )
            hn_results = await research.search_hackernews(
                keywords=topic.keywords,
                days=7
            )
            all_results.extend(github_results + hn_results)

        # 2. ANALYSE
        filtered_results = []
        for result in all_results:
            analysis = await analyzer.analyze_relevance(
                content=result,
                project_context={
                    "name": topic.project.name,
                    "description": topic.project.description,
                    "type": topic.project.type
                },
                keywords=topic.keywords
            )

            score = analysis['relevance_score']

            if score >= topic.min_relevance_score / 100:
                # Extraction d'infos selon le scope
                info_type_map = {
                    VeilleScope.FUNDING: "funding_details",
                    VeilleScope.CULTURAL: "event_details",
                    VeilleScope.TECH: "tech_specs"
                }

                details = await analyzer.extract_key_information(
                    content=result.get('description', ''),
                    info_type=info_type_map.get(topic.scope, "funding_details")
                )

                # Sauvegarde en BDD
                veille_result = VeilleResult(
                    topic_id=topic.id,
                    result_type=_get_result_type(topic.scope),
                    title=result['title'],
                    url=result.get('url'),
                    description=result.get('description'),
                    ai_summary=await analyzer.generate_summary(result.get('description', '')),
                    relevance_score=score * 100,
                    key_points=analysis['key_points'],
                    relevance_reason=analysis['reason'],
                    result_metadata=details,
                    status=analysis['recommended_action']
                )

                filtered_results.append(veille_result)

        # 3. GÉNÉRATION DE DIGEST
        if filtered_results:
            digest = await doc_gen.generate_document(
                document_type="veille_digest",
                context={
                    "project_name": topic.project.name,
                    "topic_name": topic.name,
                    "period": "Cette semaine",
                    "results_count": len(filtered_results)
                },
                sections=[
                    {"name": "Résumé exécutif", "max_words": 150},
                    {"name": "Top 5 des opportunités", "max_words": 400},
                    {"name": "Recommandations d'action", "max_words": 200}
                ]
            )

            # Sauvegarde du digest
            # Notification utilisateur
            pass

        return filtered_results

def _get_result_type(scope: VeilleScope) -> VeilleResultType:
    mapping = {
        VeilleScope.FUNDING: VeilleResultType.FUNDING_OPPORTUNITY,
        VeilleScope.CULTURAL: VeilleResultType.EVENT,
        VeilleScope.TECH: VeilleResultType.TECH_ARTICLE
    }
    return mapping.get(scope, VeilleResultType.NEWS_ARTICLE)
```

---

## Avantages de l'Architecture Modulaire

### ✅ Réutilisabilité
Chaque module peut être utilisé indépendamment ou combiné avec d'autres.

### ✅ Maintenabilité
Logique séparée = plus facile à déboguer et à améliorer.

### ✅ Testabilité
Chaque module peut être testé unitairement.

### ✅ Extensibilité
Facile d'ajouter de nouveaux modules ou d'étendre les existants.

### ✅ Flexibilité
Adaptable à tous types de projets (tech, culturel, associatif, etc.)

---

## Prochaines Étapes

1. Intégrer ces modules dans l'orchestrateur principal
2. Créer des endpoints API pour exposer les fonctionnalités
3. Ajouter des tests unitaires pour chaque module
4. Créer un système de cache pour optimiser les performances
5. Ajouter plus de sources de données (APIs externes)
