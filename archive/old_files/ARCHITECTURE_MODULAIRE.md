# Architecture Modulaire - Orchestrateur IA

## 🎯 Vision

Transformer l'orchestrateur d'un simple générateur de code en **assistant IA polyvalent** capable de gérer des projets très variés :

- 🏢 Projets associatifs (recherche de financements, rédaction de dossiers)
- 🎨 Projets artistiques (veille culturelle, recherche d'événements)
- 💻 Projets techniques (génération de code, veille technologique)
- 📚 Projets de recherche (veille académique, analyse de publications)

---

## 📦 Modules Fonctionnels

### Principe
Au lieu d'agents spécialisés par domaine, nous avons des **modules fonctionnels réutilisables**:

```
┌─────────────────────┐
│  WebResearchModule  │  Recherche et extraction web
├─────────────────────┤
│  AnalyzerModule     │  Analyse de pertinence, scoring
├─────────────────────┤
│ PromptGenerator     │  Génération de prompts contextuels
├─────────────────────┤
│ DocumentGenerator   │  Rédaction assistée
├─────────────────────┤
│  CodeGenerator      │  Génération de code (existant)
└─────────────────────┘
```

### Avantages

✅ **Réutilisabilité** : Un module = une responsabilité
✅ **Maintenabilité** : Code organisé et testé
✅ **Flexibilité** : Combinable selon les besoins
✅ **Extensibilité** : Facile d'ajouter de nouveaux modules

---

## 🔧 Description des Modules

### 1. WebResearchModule

**Responsabilité** : Recherche et extraction d'informations sur le web

**Capacités** :
- Scraping HTML avec sélecteurs CSS
- Récupération de flux RSS/Atom
- Intégration APIs (GitHub, Hacker News, data.gouv.fr)
- Recherche multi-sources en parallèle
- Gestion des erreurs et timeouts

**Sources supportées** :
- GitHub (repositories, trends)
- Hacker News (via Algolia API)
- data.gouv.fr (datasets publics français)
- Flux RSS personnalisés
- Scraping générique de pages web

**Exemple d'usage** :
```python
async with WebResearchModule() as research:
    # Recherche de financements
    results = await research.search_data_gouv(
        keywords=["subvention", "culture", "numérique"]
    )

    # Veille tech
    repos = await research.search_github(
        keywords=["FastAPI", "LLM"],
        language="Python",
        min_stars=100
    )
```

---

### 2. AnalyzerModule

**Responsabilité** : Analyse de pertinence et scoring par LLM

**Capacités** :
- Scoring de pertinence (0-100)
- Extraction d'informations clés
- Classification de contenu
- Génération de résumés
- Recommandation d'actions (SAVE/ACTION/DISMISS)

**Types d'extraction** :
- `funding_details` : Montant, deadline, éligibilité, documents requis
- `event_details` : Date, lieu, type, deadline candidature
- `tech_specs` : Langage, license, popularité, use cases

**Exemple d'usage** :
```python
analyzer = AnalyzerModule()

analysis = await analyzer.analyze_relevance(
    content=result,
    project_context={"name": "Mon Projet", "description": "..."},
    keywords=["art", "numérique", "écologie"]
)

# Retourne:
# {
#   "relevance_score": 0.85,
#   "reason": "Très pertinent car...",
#   "key_points": ["point 1", "point 2"],
#   "recommended_action": "saved"
# }
```

---

### 3. PromptGeneratorModule

**Responsabilité** : Génération intelligente de prompts contextuels

**Capacités** :
- Prompts de compréhension de projet
- Prompts de génération de code
- Prompts de rédaction de documents
- Prompts d'analyse
- Adaptation du ton et du style

**Types de prompts** :
- `project_comprehension` : Analyse approfondie d'un projet
- `code_generation` : Génération de code avec contexte
- `document_writing` : Rédaction de documents formels
- `search_query` : Optimisation de requêtes de recherche
- `analysis` : Analyse de contenu

**Exemple d'usage** :
```python
prompt_gen = PromptGeneratorModule()

prompt = prompt_gen.generate_code_prompt(
    task={"title": "Créer une API REST", "description": "..."},
    project_context={"name": "Mon API", "type": "technical"},
    coding_style={"language": "Python", "framework": "FastAPI"}
)
```

---

### 4. DocumentGeneratorModule

**Responsabilité** : Génération de documents structurés

**Capacités** :
- Dossiers de financement
- Rapports d'activité
- Propositions de partenariat
- Budgets prévisionnels
- Documentation technique

**Types de documents** :
- `funding_application` : Dossier de demande de financement
- `activity_report` : Rapport d'activité
- `partnership_proposal` : Proposition de partenariat
- `budget` : Budget prévisionnel
- `tech_digest` : Digest technique

**Exemple d'usage** :
```python
doc_gen = DocumentGeneratorModule()

document = await doc_gen.generate_funding_application(
    project_data={
        "organization_name": "Mon Asso",
        "project_name": "Mon Projet",
        "description": "...",
        "budget_requested": 50000
    },
    funding_opportunity={
        "name": "Appel à projet 2026",
        "amount": "50000€",
        "deadline": "2026-06-01"
    }
)
```

---

### 5. CodeGeneratorModule (existant, à refactoriser)

**Responsabilité** : Génération de code

**Capacités** :
- Génération de code via Ollama
- Streaming des tokens
- Détection de fin de génération
- Logs de performance

**À venir** :
- Refactorisation pour s'intégrer dans l'architecture modulaire
- Support multi-langages
- Templates de code réutilisables

---

## 🔄 Workflows Typiques

### Workflow 1 : Veille Automatique

```
┌─────────────────┐
│  VeilleTopic    │  Configuration
│  (en BDD)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ WebResearch     │  Recherche multi-sources
│    Module       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Analyzer       │  Filtrage par pertinence
│    Module       │  + Extraction d'infos
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ VeilleResult    │  Sauvegarde en BDD
│  (en BDD)       │
└─────────────────┘
```

### Workflow 2 : Génération de Document

```
┌─────────────────┐
│  Task           │  Tâche "Rédiger dossier"
│  (en BDD)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ PromptGenerator │  Génère prompt optimisé
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ DocumentGen     │  Génère le document
│    Module       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Task           │  generated_code = document
│  (updated)      │  status = MANUAL_REVIEW
└─────────────────┘
```

### Workflow 3 : Pipeline Complet

```
WebResearch → Analyzer → PromptGenerator → DocumentGen → Notification
     │            │             │               │              │
  Sources     Filtrage     Contexte        Génération      Utilisateur
```

---

## 🗂️ Structure du Projet

```
backend/
├── app/
│   ├── models/
│   │   ├── veille_topic.py          # Configuration de veille
│   │   ├── veille_result.py         # Résultats de veille
│   │   ├── task.py                  # Tâches (enrichi avec TaskType)
│   │   └── ...
│   │
│   ├── services/
│   │   ├── modules/
│   │   │   ├── __init__.py
│   │   │   ├── web_research.py      # ✅ Module de recherche web
│   │   │   ├── analyzer.py          # ✅ Module d'analyse
│   │   │   ├── prompt_generator.py  # ✅ Module de prompts
│   │   │   └── document_generator.py # ✅ Module de documents
│   │   │
│   │   ├── orchestrator.py          # Orchestrateur actuel (code)
│   │   ├── llm_client.py            # Client Ollama existant
│   │   └── scheduler.py             # Scheduler existant
│   │
│   └── ...
│
├── EXEMPLES_MODULES.md              # ✅ Exemples d'utilisation
├── ARCHITECTURE_MODULAIRE.md        # ✅ Ce fichier
└── ARCHITECTURE_AGENTS.md           # Documentation initiale (référence)
```

---

## 🚀 Prochaines Étapes d'Implémentation

### Phase 1 : Intégration (en cours)
- [x] Créer les modules de base
- [x] Documenter l'architecture
- [x] Fournir des exemples d'usage
- [ ] Créer des tests unitaires
- [ ] Intégrer dans l'orchestrateur principal

### Phase 2 : Extension
- [ ] Ajouter plus de sources de données
- [ ] Support multi-langues
- [ ] Cache et optimisation
- [ ] Système de templates

### Phase 3 : API
- [ ] Endpoints REST pour chaque module
- [ ] Documentation OpenAPI
- [ ] Interface d'administration
- [ ] Système de monitoring

---

## 💡 Cas d'Usage Réels

### Association Culturelle
**Besoin** : Trouver des financements et rédiger des dossiers

**Modules utilisés** :
1. `WebResearchModule` → Scrape data.gouv.fr, portails de financements
2. `AnalyzerModule` → Filtre par pertinence, extrait deadlines/montants
3. `DocumentGeneratorModule` → Génère dossier de demande

**Résultat** : Gain de 80% de temps sur la recherche et rédaction

---

### Projet Artistique (Compostage Numérique)
**Besoin** : Veille culturelle, recherche de festivals et résidences

**Modules utilisés** :
1. `WebResearchModule` → Scrape sites de festivals, flux RSS
2. `AnalyzerModule` → Score pertinence thématique, extraction dates/lieux
3. `PromptGeneratorModule` → Génère prompts pour candidature

**Résultat** : Veille automatisée, alertes sur opportunités pertinentes

---

### Projet Technique (API)
**Besoin** : Génération de code + veille technologique

**Modules utilisés** :
1. `WebResearchModule` → GitHub, HN, Stack Overflow
2. `AnalyzerModule` → Filtre nouveaux outils pertinents
3. `CodeGeneratorModule` → Génère code avec contexte enrichi
4. `PromptGeneratorModule` → Prompts optimisés pour le projet

**Résultat** : Code généré + veille tech automatique

---

## 🔬 Tests et Validation

### Tests Unitaires
Chaque module doit avoir ses tests :

```python
# test_web_research.py
async def test_search_github():
    async with WebResearchModule() as research:
        results = await research.search_github(
            keywords=["FastAPI"],
            language="Python",
            min_stars=100
        )
        assert len(results) > 0
        assert all("FastAPI" in r['title'] for r in results)

# test_analyzer.py
async def test_analyze_relevance():
    analyzer = AnalyzerModule()
    analysis = await analyzer.analyze_relevance(
        content={"title": "Test", "description": "..."},
        project_context={"name": "Test Project"},
        keywords=["test"]
    )
    assert 0 <= analysis['relevance_score'] <= 1
    assert 'reason' in analysis
```

### Tests d'Intégration
Tester les workflows complets :

```python
async def test_veille_pipeline():
    """Test complet du pipeline de veille"""
    # 1. Recherche
    async with WebResearchModule() as research:
        results = await research.search_data_gouv(keywords=["test"])

    # 2. Analyse
    analyzer = AnalyzerModule()
    for result in results:
        analysis = await analyzer.analyze_relevance(...)
        assert 'relevance_score' in analysis

    # 3. Sauvegarde
    # ... vérifier que les résultats sont bien sauvegardés
```

---

## 📊 Performance et Optimisation

### Caching
- Cache des requêtes HTTP (avec TTL)
- Cache des analyses LLM (pour éviter re-analyse)
- Cache des résultats de recherche

### Parallélisation
- Recherches multi-sources en parallèle
- Analyses par batch
- Génération de documents async

### Monitoring
- Logs structurés
- Métriques de performance
- Alertes sur erreurs

---

## 🎓 Apprentissage et Amélioration

### Feedback Utilisateur
- Rating des résultats de veille
- Validation des documents générés
- Ajustement des seuils de pertinence

### Amélioration Continue
- Affiner les prompts selon résultats
- Ajouter de nouvelles sources
- Optimiser les scrapers

---

## 📝 Licence et Contribution

Ce système est conçu pour être **modulaire et extensible**.

Contributions bienvenues :
- Nouveaux modules
- Nouvelles sources de données
- Amélioration des prompts
- Tests et documentation
