# Architecture des Agents IA Multi-Domaines

## Vision

Transformer l'orchestrateur actuel (focalisé code) en système multi-agents capable de gérer :
- Projets techniques (code)
- Projets associatifs (financements, administratif)
- Projets artistiques/culturels (veille créative, événements)
- Projets de recherche (veille scientifique)

---

## 1. Modèles de Données

### A. Enrichissement du modèle `Task`

```python
class TaskType(str, enum.Enum):
    """Types de tâches selon le domaine"""
    CODE_GENERATION = "code_generation"      # Génération de code
    DOCUMENT_WRITING = "document_writing"    # Rédaction de documents
    FUNDING_SEARCH = "funding_search"        # Recherche de financements
    VEILLE_TECH = "veille_tech"             # Veille technologique
    VEILLE_CULTURAL = "veille_cultural"      # Veille culturelle/artistique
    VEILLE_EVENTS = "veille_events"          # Recherche d'événements
    ADMINISTRATIVE = "administrative"        # Tâches administratives
    RESEARCH = "research"                    # Recherche générique

class Task(Base):
    # ... champs existants ...
    task_type = Column(SQLEnum(TaskType), nullable=False, index=True)

    # Métadonnées spécifiques au type
    task_config = Column(JSON, nullable=True)  # Config spécifique par type
    # Exemples:
    # - CODE: {"language": "python", "framework": "fastapi"}
    # - FUNDING: {"amount_needed": 50000, "deadline": "2026-06-01", "domain": "tech"}
    # - VEILLE_CULTURAL: {"keywords": ["compostage", "art numérique"], "radius_km": 100}
```

### B. Nouveau modèle `VeilleTopic`

```python
class VeilleScope(str, enum.Enum):
    TECH = "tech"                    # GitHub, Stack Overflow, HN
    FUNDING = "funding"              # Appels d'offres, subventions
    CULTURAL = "cultural"            # Festivals, expositions
    ACADEMIC = "academic"            # Publications scientifiques
    NEWS = "news"                    # Actualités généralistes

class VeilleTopic(Base):
    """Sujets de veille configurés par projet"""
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))

    name = Column(String(255))  # "Financements association"
    scope = Column(SQLEnum(VeilleScope))

    # Configuration de recherche
    keywords = Column(JSON)  # ["compostage", "art numérique", "données"]
    excluded_keywords = Column(JSON)  # ["compost physique"]

    # Filtres géographiques/temporels
    location_filters = Column(JSON)  # {"country": "FR", "region": "IDF", "radius_km": 100}
    date_filters = Column(JSON)      # {"min_date": "2026-01-01", "max_date": "2026-12-31"}

    # Sources spécifiques
    sources = Column(JSON)  # ["artsy.net", "culture.gouv.fr", "festivals.fr"]

    # Fréquence de scan
    scan_frequency = Column(String(50))  # "daily", "weekly", "monthly"
    last_scan = Column(DateTime)
    next_scan = Column(DateTime)

    enabled = Column(Boolean, default=True)

    # Relation
    project = relationship("Project", back_populates="veille_topics")
```

### C. Nouveau modèle `VeilleResult`

```python
class VeilleResultType(str, enum.Enum):
    FUNDING_OPPORTUNITY = "funding_opportunity"
    TECH_ARTICLE = "tech_article"
    EVENT = "event"                   # Festival, exposition
    COLLABORATION = "collaboration"   # Opportunité de collaboration
    ACADEMIC_PAPER = "academic_paper"
    NEWS_ARTICLE = "news_article"

class VeilleResult(Base):
    """Résultat d'une veille (opportunité trouvée)"""
    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey("veille_topics.id"))

    result_type = Column(SQLEnum(VeilleResultType))

    # Contenu
    title = Column(String(500))
    url = Column(String(1000))
    description = Column(Text)

    # Analyse IA
    ai_summary = Column(Text)              # Résumé généré par LLM
    relevance_score = Column(Float)        # 0-1 (calculé par LLM)
    key_points = Column(JSON)              # Points clés extraits

    # Métadonnées spécifiques
    metadata = Column(JSON)
    # Exemples:
    # - FUNDING: {"amount": 50000, "deadline": "2026-06-01", "eligibility": "..."}
    # - EVENT: {"date": "2026-05-15", "location": "Paris", "type": "festival"}
    # - TECH: {"github_stars": 1500, "last_commit": "2026-01-01"}

    # Source et dates
    source = Column(String(255))
    found_at = Column(DateTime, default=datetime.utcnow)

    # Statut utilisateur
    status = Column(String(50), default="new")  # new, read, saved, dismissed
    user_notes = Column(Text)

    # Relations
    topic = relationship("VeilleTopic", back_populates="results")
```

### D. Nouveau modèle `DocumentTemplate`

```python
class DocumentType(str, enum.Enum):
    FUNDING_APPLICATION = "funding_application"     # Dossier de demande de financement
    PROJECT_DESCRIPTION = "project_description"     # Description de projet
    BUDGET_PLAN = "budget_plan"                    # Plan budgétaire
    ACTIVITY_REPORT = "activity_report"            # Rapport d'activité
    PARTNERSHIP_PROPOSAL = "partnership_proposal"   # Proposition de partenariat
    TECHNICAL_SPEC = "technical_spec"              # Spécification technique
    CUSTOM = "custom"

class DocumentTemplate(Base):
    """Templates de documents avec sections pré-définies"""
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))

    name = Column(String(255))
    document_type = Column(SQLEnum(DocumentType))

    # Structure du document
    sections = Column(JSON)
    # Exemple pour FUNDING_APPLICATION:
    # [
    #   {"name": "Présentation de l'association", "required": true, "max_words": 500},
    #   {"name": "Description du projet", "required": true, "max_words": 1000},
    #   {"name": "Budget prévisionnel", "required": true, "format": "table"},
    #   {"name": "Impact attendu", "required": true, "max_words": 300}
    # ]

    # Données du projet pour remplir le template
    project_data = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## 2. Agents Spécialisés

### A. VeilleAgent (générique)

**Fichier**: `app/services/agents/veille_agent.py`

```python
class VeilleAgent:
    """
    Agent de veille générique, configurable par scope

    Capacités:
    - Scrape sources web (HTTP, RSS, APIs)
    - Analyse de pertinence avec LLM
    - Extraction d'informations structurées
    - Génération de résumés
    - Scoring de pertinence
    """

    def __init__(self, db: AsyncSession, llm_client: OllamaClient):
        self.db = db
        self.llm = llm_client
        self.scrapers = {
            VeilleScope.TECH: TechScraper(),
            VeilleScope.FUNDING: FundingScraper(),
            VeilleScope.CULTURAL: CulturalScraper(),
            VeilleScope.ACADEMIC: AcademicScraper()
        }

    async def scan_topic(self, topic: VeilleTopic) -> List[VeilleResult]:
        """Scanne un sujet de veille"""
        scraper = self.scrapers[topic.scope]
        raw_results = await scraper.fetch(topic)

        # Analyse chaque résultat avec LLM
        filtered_results = []
        for raw in raw_results:
            score = await self.analyze_relevance(raw, topic)
            if score >= 0.6:  # Seuil de pertinence
                result = await self.create_result(raw, topic, score)
                filtered_results.append(result)

        return filtered_results

    async def analyze_relevance(self, content: dict, topic: VeilleTopic) -> float:
        """Calcul de pertinence par LLM"""
        prompt = f"""
        Projet: {topic.project.name}
        Description: {topic.project.description}
        Mots-clés recherchés: {', '.join(topic.keywords)}

        Contenu trouvé:
        Titre: {content['title']}
        Description: {content['description']}

        Question: Ce contenu est-il pertinent pour le projet ?
        Réponds avec un score de 0 à 1 et une justification courte.
        Format: SCORE: 0.X | JUSTIFICATION: ...
        """

        response = await self.llm.generate_text(prompt)
        # Parse le score
        score = self._extract_score(response)
        return score

    async def generate_summary(self, content: str, topic: VeilleTopic) -> str:
        """Génère un résumé intelligent"""
        prompt = f"""
        Résume ce contenu en 3-5 points clés pour le projet "{topic.project.name}":

        {content}

        Focus sur: {', '.join(topic.keywords)}
        """
        return await self.llm.generate_text(prompt)

    async def create_digest(self, project_id: int, period: str = "week") -> str:
        """Crée un digest des résultats de veille"""
        # Récupère tous les résultats de la période
        results = await self._get_recent_results(project_id, period)

        # Génère un digest structuré
        prompt = f"""
        Crée un rapport de veille hebdomadaire structuré avec ces {len(results)} découvertes:

        {self._format_results(results)}

        Structure:
        1. Résumé exécutif (2-3 phrases)
        2. Top 3 des opportunités prioritaires
        3. Veille technologique (si applicable)
        4. Événements à venir (si applicable)
        5. Financements disponibles (si applicable)
        """

        return await self.llm.generate_text(prompt)
```

### B. FundingAgent

**Fichier**: `app/services/agents/funding_agent.py`

```python
class FundingAgent:
    """
    Agent spécialisé dans la recherche de financements

    Sources:
    - France: data.gouv.fr, culture.gouv.fr, BPI France
    - Europe: EU funding & tenders portal
    - Fondations privées
    - Appels à projets
    """

    async def search_funding(self, project: Project) -> List[VeilleResult]:
        """Recherche de financements adaptés au projet"""

        # Analyse du projet pour identifier les critères
        criteria = await self.extract_funding_criteria(project)

        # Recherche multi-sources
        results = []
        results.extend(await self.search_public_funding(criteria))
        results.extend(await self.search_private_funding(criteria))
        results.extend(await self.search_european_funding(criteria))

        # Scoring et filtrage
        scored_results = await self.score_opportunities(results, project)

        return scored_results

    async def extract_required_documents(self, funding: VeilleResult) -> List[str]:
        """Analyse un appel d'offres et extrait les documents requis"""
        prompt = f"""
        Analyse cet appel d'offres et liste TOUS les documents requis:

        {funding.description}

        Retourne une liste JSON structurée:
        [
            {{
                "document": "nom du document",
                "required": true/false,
                "deadline": "date si mentionnée",
                "format": "format attendu"
            }},
            ...
        ]
        """

        response = await self.llm.generate_text(prompt)
        return json.loads(response)

    async def check_eligibility(self, funding: VeilleResult, project: Project) -> dict:
        """Vérifie l'éligibilité du projet à un financement"""
        prompt = f"""
        FINANCEMENT:
        {funding.description}
        Critères: {funding.metadata.get('eligibility_criteria', 'Non spécifié')}

        PROJET:
        Type: {project.type}
        Description: {project.description}
        Structure: Association

        Question: Ce projet est-il éligible ? Explique pourquoi.
        Format:
        ELIGIBLE: OUI/NON/INCERTAIN
        RAISONS: [liste]
        POINTS_ATTENTION: [liste]
        """

        response = await self.llm.generate_text(prompt)
        return self._parse_eligibility(response)
```

### C. DocumentAgent

**Fichier**: `app/services/agents/document_agent.py`

```python
class DocumentAgent:
    """
    Agent de rédaction de documents

    Capacités:
    - Rédiger des dossiers de financement
    - Générer des budgets prévisionnels
    - Créer des rapports d'activité
    - Adapter le ton selon le contexte
    """

    async def generate_document(
        self,
        template: DocumentTemplate,
        project: Project
    ) -> str:
        """Génère un document complet à partir d'un template"""

        sections_content = []

        for section in template.sections:
            content = await self.generate_section(
                section_name=section['name'],
                requirements=section,
                project_data=template.project_data,
                project=project
            )
            sections_content.append({
                'name': section['name'],
                'content': content
            })

        # Assemble le document final
        final_doc = self.assemble_document(sections_content, template)
        return final_doc

    async def generate_section(
        self,
        section_name: str,
        requirements: dict,
        project_data: dict,
        project: Project
    ) -> str:
        """Génère une section de document"""

        max_words = requirements.get('max_words', 500)
        tone = requirements.get('tone', 'professional')

        prompt = f"""
        Rédige la section "{section_name}" pour un dossier de demande de financement.

        PROJET:
        Nom: {project.name}
        Type: {project.type}
        Description: {project.description}

        DONNÉES SPÉCIFIQUES:
        {json.dumps(project_data, indent=2, ensure_ascii=False)}

        CONTRAINTES:
        - Maximum {max_words} mots
        - Ton: {tone}
        - Format: {requirements.get('format', 'paragraphe')}

        Sois convaincant, précis, et mets en avant l'impact du projet.
        """

        return await self.llm.generate_text(prompt, max_tokens=max_words * 2)

    async def generate_budget(self, project_data: dict) -> str:
        """Génère un budget prévisionnel au format Markdown table"""
        prompt = f"""
        Crée un budget prévisionnel au format tableau Markdown pour:

        {json.dumps(project_data, indent=2, ensure_ascii=False)}

        Inclus:
        - Ressources humaines
        - Matériel
        - Prestations externes
        - Communication
        - Imprévus (10%)

        Format: Tableau Markdown avec colonnes Poste | Quantité | Prix unitaire | Total
        """

        return await self.llm.generate_text(prompt)
```

### D. CulturalAgent

**Fichier**: `app/services/agents/cultural_agent.py`

```python
class CulturalAgent:
    """
    Agent spécialisé dans la veille culturelle et artistique

    Sources:
    - Festivals (Festiv.fr, art events)
    - Expositions (Artsy, museums)
    - Appels à résidence
    - Appels à artistes
    - Publications artistiques
    """

    async def search_events(
        self,
        keywords: List[str],
        location: dict,
        date_range: dict
    ) -> List[VeilleResult]:
        """Recherche d'événements culturels"""

        # Scraping multi-sources
        events = []
        events.extend(await self.scrape_festivals(keywords, location, date_range))
        events.extend(await self.scrape_exhibitions(keywords, location, date_range))
        events.extend(await self.scrape_artist_calls(keywords, date_range))

        # Analyse de pertinence
        relevant_events = []
        for event in events:
            score = await self.analyze_cultural_relevance(event, keywords)
            if score >= 0.6:
                relevant_events.append(event)

        return relevant_events

    async def analyze_cultural_relevance(self, event: dict, keywords: List[str]) -> float:
        """Analyse si un événement est pertinent pour le projet artistique"""

        prompt = f"""
        PROJET: Compostage de données numériques (art numérique + écologie)
        Mots-clés: {', '.join(keywords)}

        ÉVÉNEMENT:
        Nom: {event['title']}
        Description: {event['description']}
        Type: {event['type']}

        Ce festival/exposition/appel est-il pertinent pour présenter ou développer ce projet ?

        Score de 0 à 1:
        - 0.9-1.0: Parfaitement aligné
        - 0.7-0.8: Très pertinent
        - 0.5-0.6: Potentiellement intéressant
        - <0.5: Peu pertinent

        Format: SCORE: 0.X | RAISON: ...
        """

        response = await self.llm.generate_text(prompt)
        return self._extract_score(response)

    async def find_similar_artists(self, project_description: str) -> List[dict]:
        """Trouve des artistes travaillant sur des thématiques similaires"""
        # Recherche via APIs (Artsy, Discogs, etc.)
        # + analyse LLM pour matching thématique
        pass
```

---

## 3. Orchestrateur Unifié

**Fichier**: `app/services/unified_orchestrator.py`

```python
class UnifiedOrchestrator:
    """
    Orchestrateur qui dispatche les tâches vers les agents appropriés
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = OllamaClient()

        # Initialisation des agents
        self.code_agent = CodeAgent(db, self.llm)
        self.veille_agent = VeilleAgent(db, self.llm)
        self.funding_agent = FundingAgent(db, self.llm)
        self.document_agent = DocumentAgent(db, self.llm)
        self.cultural_agent = CulturalAgent(db, self.llm)

    async def process_all_queues(self):
        """Point d'entrée principal - traite toutes les tâches"""

        # 1. Traiter les tâches selon leur type
        await self.process_tasks_by_type()

        # 2. Exécuter les veilles programmées
        await self.process_scheduled_veille()

        # 3. Générer les digests quotidiens/hebdomadaires
        await self.generate_digests()

    async def process_tasks_by_type(self):
        """Dispatche les tâches vers le bon agent"""

        # Récupère toutes les tâches READY
        stmt = select(Task).where(Task.status == TaskStatus.READY)
        result = await self.db.execute(stmt)
        tasks = result.scalars().all()

        for task in tasks:
            try:
                if task.task_type == TaskType.CODE_GENERATION:
                    await self.code_agent.handle_task(task)

                elif task.task_type == TaskType.FUNDING_SEARCH:
                    await self.funding_agent.search_and_create_results(task)

                elif task.task_type == TaskType.DOCUMENT_WRITING:
                    await self.document_agent.generate_and_save(task)

                elif task.task_type == TaskType.VEILLE_CULTURAL:
                    await self.cultural_agent.search_and_create_results(task)

                elif task.task_type in [TaskType.VEILLE_TECH, TaskType.VEILLE_EVENTS]:
                    await self.veille_agent.scan_and_save(task)

            except Exception as e:
                logger.error(f"Task {task.id} failed: {e}")
                await self.handle_task_failure(task, e)

    async def process_scheduled_veille(self):
        """Exécute les veilles programmées (daily, weekly, etc.)"""

        # Récupère les topics à scanner maintenant
        now = datetime.utcnow()
        stmt = (
            select(VeilleTopic)
            .where(VeilleTopic.enabled == True)
            .where(VeilleTopic.next_scan <= now)
        )
        result = await self.db.execute(stmt)
        topics = result.scalars().all()

        for topic in topics:
            try:
                # Scan selon le scope
                if topic.scope == VeilleScope.FUNDING:
                    results = await self.funding_agent.search_funding_for_topic(topic)
                elif topic.scope == VeilleScope.CULTURAL:
                    results = await self.cultural_agent.search_events_for_topic(topic)
                else:
                    results = await self.veille_agent.scan_topic(topic)

                # Sauvegarde les résultats
                for result in results:
                    self.db.add(result)

                # Update next_scan
                topic.last_scan = now
                topic.next_scan = self._calculate_next_scan(topic.scan_frequency)

                await self.db.commit()

            except Exception as e:
                logger.error(f"Veille topic {topic.id} failed: {e}")

    async def generate_digests(self):
        """Génère des digests de veille pour les projets actifs"""

        # Logique pour identifier quels projets ont besoin d'un digest
        # (ex: tous les lundis matin, digest hebdomadaire)
        pass
```

---

## 4. Configuration Frontend

### Nouveau panneau "Veille & Automatisation"

Dans l'interface projet, ajouter une section:

```typescript
// ProjectSettings.vue
{
  veille_topics: [
    {
      name: "Financements association",
      scope: "funding",
      keywords: ["subvention", "association", "culture"],
      frequency: "weekly",
      enabled: true
    },
    {
      name: "Art numérique & écologie",
      scope: "cultural",
      keywords: ["compostage", "art numérique", "data art", "écologie"],
      location: { country: "FR", radius_km: 200 },
      frequency: "daily",
      enabled: true
    }
  ],

  document_automation: {
    enabled: true,
    templates: [
      {
        name: "Dossier de financement type",
        type: "funding_application"
      }
    ]
  }
}
```

---

## 5. Priorisation d'Implémentation

**Phase 1 - Fondations** (1-2 semaines)
1. ✅ Nouveaux modèles (VeilleTopic, VeilleResult, DocumentTemplate)
2. ✅ Migration BDD
3. ✅ VeilleAgent générique (structure de base)

**Phase 2 - Agent Financement** (1 semaine)
4. ✅ FundingScraper (data.gouv.fr, etc.)
5. ✅ FundingAgent
6. ✅ Interface de visualisation des opportunités

**Phase 3 - Agent Culturel** (1 semaine)
7. ✅ CulturalScraper
8. ✅ CulturalAgent
9. ✅ Filtres géographiques et temporels

**Phase 4 - Agent Document** (1-2 semaines)
10. ✅ DocumentAgent
11. ✅ Templates de documents
12. ✅ Génération de budgets

**Phase 5 - Orchestration** (3-4 jours)
13. ✅ UnifiedOrchestrator
14. ✅ Scheduler multi-agents
15. ✅ Système de notifications

---

## 6. Exemple de Workflow Complet

### Cas d'usage: Association recherchant un financement

1. **USER** configure un topic de veille:
   - Nom: "Financements pour projet culturel numérique"
   - Scope: FUNDING
   - Keywords: ["culture", "numérique", "innovation"]
   - Fréquence: hebdomadaire

2. **VEILLE AUTO** (tous les lundis):
   - FundingAgent scanne les sources
   - Trouve 5 opportunités
   - Score de pertinence: 0.85, 0.78, 0.65, 0.60, 0.45
   - Sauvegarde les 4 premières (>0.6)

3. **ANALYSE AUTO**:
   - Pour chaque opportunité > 0.75:
     - Extrait les documents requis
     - Vérifie l'éligibilité
     - Calcule la deadline

4. **NOTIFICATION USER**:
   - "2 financements très pertinents trouvés"
   - User clique sur le plus prometteur

5. **USER** demande de l'aide pour le dossier:
   - Crée une tâche: "Rédiger dossier financement XYZ"
   - Type: DOCUMENT_WRITING
   - Template: FUNDING_APPLICATION

6. **DOCUMENT AGENT**:
   - Génère automatiquement:
     - Présentation de l'association
     - Description du projet
     - Budget prévisionnel
     - Impact attendu
   - Status → MANUAL_REVIEW

7. **USER** révise, ajuste, valide ✅

---

Cette architecture permet de gérer:
- ✅ Projets tech (code)
- ✅ Projets associatifs (financements + docs)
- ✅ Projets artistiques (veille culturelle)
- ✅ Projets de recherche (veille académique)
