# Production Readiness Checklist

Liste de vérification complète avant mise en production de l'Orchestrateur IA.

---

## 🔐 Sécurité

### Authentification & Autorisation

- [ ] **SECRET_KEY changée** - Générer une clé aléatoire de 64+ caractères
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(64))"
  ```
- [ ] **Mots de passe DB forts** - Utiliser des mots de passe générés aléatoirement
- [ ] **JWT expiration configurée** - Vérifier `ACCESS_TOKEN_EXPIRE_MINUTES` adapté (pas 7 jours en prod)
- [ ] **Rate limiting activé** - Limiter les requêtes par IP/utilisateur
- [ ] **Protection contre brute force** - Limiter tentatives de login
- [ ] **Validation des entrées** - Tous les endpoints validés avec Pydantic/Zod
- [ ] **Permissions testées** - Utilisateur ne peut accéder qu'à ses données

### Configuration

- [ ] **DEBUG=False** - Désactiver le mode debug partout
- [ ] **CORS restrictifs** - Uniquement domaines de production autorisés
- [ ] **HTTPS forcé** - Redirection automatique HTTP → HTTPS
- [ ] **Certificats SSL valides** - Let's Encrypt ou certificat commercial
- [ ] **Headers de sécurité** - HSTS, CSP, X-Frame-Options, etc.
  ```python
  # backend/app/main.py
  from fastapi.middleware.trustedhost import TrustedHostMiddleware
  app.add_middleware(TrustedHostMiddleware, allowed_hosts=["yourdomain.com"])
  ```
- [ ] **Secrets externalisés** - Variables sensibles dans secrets manager (pas `.env`)

### Code & Dépendances

- [ ] **Scan de vulnérabilités** - `safety check` sur requirements.txt
  ```bash
  pip install safety
  safety check -r backend/requirements.txt
  ```
- [ ] **Dépendances à jour** - Vérifier CVE connues
- [ ] **SQL Injection testé** - ORM utilisé partout (pas de raw SQL)
- [ ] **XSS testé** - Frontend échappe toutes les entrées utilisateur
- [ ] **CSRF protection** - Tokens CSRF sur formulaires critiques

---

## 🗄️ Base de Données

### Configuration PostgreSQL

- [ ] **Version stable** - PostgreSQL 15+ en production
- [ ] **Backups automatiques** - Quotidiens minimum, testés mensuellement
- [ ] **Restore procedure testée** - DR testé au moins 1x
- [ ] **Connexions pooling** - SQLAlchemy pool configuré
  ```python
  # backend/app/core/database.py
  engine = create_async_engine(
      DATABASE_URL,
      pool_size=10,
      max_overflow=20,
      pool_pre_ping=True
  )
  ```
- [ ] **Indexes optimisés** - Sur colonnes fréquemment requêtées
- [ ] **Migrations versionnées** - Alembic à jour, testées en staging
- [ ] **Monitoring queries lentes** - pg_stat_statements activé
- [ ] **Retention logs** - Logs PostgreSQL rotés et archivés

### Données

- [ ] **Données sensibles chiffrées** - Passwords, tokens, etc.
- [ ] **GDPR compliance** - Procédure de suppression utilisateur
- [ ] **Archivage configuré** - Soft delete pour projets/tâches
- [ ] **Nettoyage des logs** - TaskLogs purgés après N mois

---

## ⚙️ Backend (FastAPI)

### Performance

- [ ] **Workers configurés** - Uvicorn multi-workers
  ```bash
  uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
  ```
- [ ] **Async/await partout** - DB queries async
- [ ] **Pagination activée** - Tous les endpoints de liste
- [ ] **Caching configuré** - Redis pour cache si nécessaire
- [ ] **Connection pooling** - DB et HTTP clients
- [ ] **Timeouts configurés** - Sur appels Ollama et API externes

### Monitoring & Logs

- [ ] **Logging structuré** - JSON logs pour agrégation
  ```python
  import structlog
  logger = structlog.get_logger()
  ```
- [ ] **Niveaux de logs** - INFO en prod, DEBUG désactivé
- [ ] **Rotation des logs** - Quotidienne, compression après 7j
- [ ] **Health checks** - `/health` répond en <200ms
- [ ] **Métriques exposées** - Prometheus metrics si possible
- [ ] **Alerting configuré** - Sur erreurs critiques, disk space, etc.
- [ ] **Tracing distribué** - OpenTelemetry si microservices

### Orchestrator

- [ ] **Intervalle adapté** - 5min par défaut, ajuster selon charge
- [ ] **Batch size testé** - Pas de surcharge Ollama
- [ ] **Error handling robuste** - Retry avec exponential backoff
- [ ] **Dead letter queue** - Tâches failed après N tentatives
- [ ] **Monitoring orchestrator** - Alertes si stoppé
- [ ] **Graceful shutdown** - Signal SIGTERM géré proprement

---

## 🎨 Frontend (React)

### Build & Performance

- [ ] **Build optimisé** - `npm run build` sans warnings
- [ ] **Code splitting** - Routes lazy loaded
  ```tsx
  const Dashboard = lazy(() => import('./pages/Dashboard'))
  ```
- [ ] **Assets optimisés** - Images compressées, minification
- [ ] **Bundle size** - <500KB initial, analysé avec `vite-bundle-visualizer`
- [ ] **Service Worker** - PWA si nécessaire
- [ ] **CDN configuré** - Assets statiques sur CDN

### Sécurité

- [ ] **Tokens sécurisés** - Stockage JWT dans httpOnly cookie (pas localStorage)
- [ ] **XSS prevention** - React échappe par défaut, vérifier dangerouslySetInnerHTML
- [ ] **CSP headers** - Content Security Policy configurée
- [ ] **Inputs sanitisés** - Validation Zod sur tous les forms

### UX

- [ ] **Loading states** - Skeletons ou spinners partout
- [ ] **Error boundaries** - Catch errors React
  ```tsx
  <ErrorBoundary fallback={<ErrorPage />}>
    <App />
  </ErrorBoundary>
  ```
- [ ] **Offline handling** - Message si pas de connexion
- [ ] **Mobile responsive** - Testé sur iOS/Android
- [ ] **Accessibilité** - ARIA labels, contraste, navigation clavier

---

## 🤖 Ollama & LLM

### Configuration

- [ ] **Modèles optimisés** - Q4 quantization minimum pour prod
- [ ] **Modèles pré-chargés** - `ollama serve` avec modèles en mémoire
- [ ] **Timeouts** - 5min max par génération
- [ ] **Retry logic** - 3 tentatives avec backoff
- [ ] **Fallback model** - Si Devstral fail, utiliser Mistral

### Monitoring

- [ ] **Uptime monitoring** - Ollama healthcheck toutes les 30s
- [ ] **Latency tracking** - Temps de génération moyen <60s
- [ ] **Utilisation GPU** - Monitoring VRAM si GPU utilisé
- [ ] **Rate limiting** - Max 10 générations concurrentes

---

## 🐳 Infrastructure Docker

### Production Setup

- [ ] **Multi-stage builds** - Images légères
- [ ] **Non-root user** - Containers run as user 1000:1000
- [ ] **Health checks** - Tous les services
  ```yaml
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
  ```
- [ ] **Resource limits** - CPU/Memory limits sur containers
  ```yaml
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
  ```
- [ ] **Restart policy** - `restart: unless-stopped`
- [ ] **Volumes persistents** - DB data, uploads, logs

### Sécurité Docker

- [ ] **Images scannées** - `docker scan` ou Trivy
  ```bash
  trivy image orchestrator-backend:latest
  ```
- [ ] **Base images officielles** - python:3.11-slim, postgres:15-alpine
- [ ] **Secrets Docker** - Utiliser secrets au lieu d'ENV vars
- [ ] **Network isolation** - Services isolés dans network privé
- [ ] **Registry privé** - Images stockées dans registry privé si possible

---

## 📊 Monitoring & Observabilité

### Logs

- [ ] **Agrégation centralisée** - ELK, Loki, ou CloudWatch
- [ ] **Retention policy** - 30-90 jours selon réglementation
- [ ] **Log queries** - Dashboards pour erreurs fréquentes
- [ ] **Alertes logs** - Sur patterns d'erreur critiques

### Métriques

- [ ] **System metrics** - CPU, RAM, Disk, Network
- [ ] **Application metrics** - Request rate, latency, errors
- [ ] **Business metrics** - Tâches créées/jour, taux de validation, etc.
- [ ] **Dashboards** - Grafana ou équivalent

### Tracing

- [ ] **Distributed tracing** - Si microservices (OpenTelemetry)
- [ ] **Request ID** - Propagé dans tous les logs
- [ ] **Performance profiling** - Identifier bottlenecks

### Alerting

- [ ] **On-call rotation** - PagerDuty ou équivalent
- [ ] **Alert rules** - Error rate >5%, latency >2s, disk >80%, etc.
- [ ] **Escalation policy** - Après 15min, escalade
- [ ] **Runbooks** - Documentation pour chaque alerte

---

## 🧪 Tests & QA

### Tests Automatisés

- [ ] **Unit tests** - >70% coverage backend
- [ ] **Integration tests** - Workflow complet testé
- [ ] **E2E tests** - Playwright ou Cypress pour frontend
- [ ] **Load testing** - K6 ou Locust, 100+ users concurrents
  ```bash
  # Exemple k6
  k6 run --vus 100 --duration 5m load_test.js
  ```
- [ ] **Security testing** - OWASP ZAP scan
- [ ] **CI/CD** - Tests run automatiquement sur PR

### Environnements

- [ ] **Staging identique** - Config quasi-identique à prod
- [ ] **Smoke tests** - Tests critiques post-deploy
- [ ] **Rollback procedure** - Testée et documentée
- [ ] **Blue/Green deployment** - Zero-downtime si possible

---

## 🔄 CI/CD

### Pipeline

- [ ] **Automated build** - GitHub Actions, GitLab CI, etc.
- [ ] **Linting** - Black, isort, eslint run automatiquement
- [ ] **Tests run** - Toutes les suites de tests
- [ ] **Security scan** - Dependabot, Snyk
- [ ] **Docker build** - Images buildées et pushées
- [ ] **Deployment automated** - Deploy sur merge main

### Versioning

- [ ] **Semantic versioning** - v1.0.0, v1.1.0, etc.
- [ ] **Changelog** - CHANGELOG.md à jour
- [ ] **Git tags** - Chaque release taguée
- [ ] **Release notes** - Documentation pour chaque release

---

## 📚 Documentation

### Technique

- [ ] **README complet** - Installation, usage, architecture
- [ ] **API documentation** - Swagger/OpenAPI à jour
- [ ] **Architecture diagrams** - Schémas à jour
- [ ] **Database schema** - ERD documenté
- [ ] **Deployment guide** - DEPLOYMENT.md complet
- [ ] **Runbook** - Procédures d'incident

### Utilisateur

- [ ] **User guide** - Guide d'utilisation complet
- [ ] **FAQ** - Questions fréquentes
- [ ] **Tutorials** - Vidéos ou screenshots
- [ ] **Release notes** - Changelog user-friendly

---

## 🚨 Disaster Recovery

### Backup

- [ ] **DB backups** - Quotidiens, testés mensuellement
- [ ] **Backup encryption** - Backups chiffrés
- [ ] **Offsite storage** - Backups sur cloud séparé
- [ ] **Retention policy** - 30 jours min, 1 an pour critiques

### Recovery

- [ ] **RTO défini** - Recovery Time Objective (ex: 4h)
- [ ] **RPO défini** - Recovery Point Objective (ex: 1h de data)
- [ ] **Restore testé** - Test complet 1x par trimestre
- [ ] **Disaster recovery plan** - Document détaillé
- [ ] **Incident response** - Playbook pour incidents majeurs

---

## 📈 Performance

### Benchmarks

- [ ] **Load tests passés** - 100+ users, <2s latency p99
- [ ] **Database queries** - <100ms p95
- [ ] **Code generation** - <60s moyenne Ollama
- [ ] **Page load** - <3s First Contentful Paint

### Optimizations

- [ ] **Database indexes** - Sur colonnes WHERE/JOIN
- [ ] **Query optimization** - N+1 queries éliminées
- [ ] **Caching strategy** - Cache warming si nécessaire
- [ ] **CDN configured** - Assets statiques sur CDN

---

## 🔧 Maintenance

### Procedures

- [ ] **Update procedure** - Documentation mise à jour dépendances
- [ ] **Scaling plan** - Comment scale horizontalement
- [ ] **Monitoring review** - Metrics revues mensuellement
- [ ] **Security patches** - Process pour patches critiques

### Documentation

- [ ] **Runbook complet** - Incidents courants documentés
- [ ] **Oncall guide** - Comment gérer on-call
- [ ] **Escalation matrix** - Qui contacter quand
- [ ] **Post-mortems** - Template pour incidents

---

## ✅ Final Checks

### Pre-Deployment

- [ ] **Staging déployé** - Testé pendant 1 semaine min
- [ ] **Load test passé** - Sur staging avec data prod-like
- [ ] **Security audit** - Pen-test ou audit externe
- [ ] **Performance validated** - Benchmarks OK
- [ ] **Backup/restore testé** - DR validé
- [ ] **Monitoring configured** - Alertes testées
- [ ] **Documentation complète** - Tout est documenté
- [ ] **Team trained** - Équipe formée sur le système

### Post-Deployment

- [ ] **Smoke tests** - Tests critiques après deploy
- [ ] **Monitoring actif** - Dashboards surveillés 24h
- [ ] **Backup vérifié** - Premier backup post-deploy OK
- [ ] **Performance baseline** - Metrics de référence établies
- [ ] **Incident response ready** - Oncall en place
- [ ] **Rollback plan** - Prêt à rollback si problème

---

## 🎯 Critères de Go/No-Go

**GO si** :
- ✅ Tous les items Sécurité cochés
- ✅ Tous les items Database cochés
- ✅ Tests >70% coverage et passent
- ✅ Load test passé (100 users)
- ✅ Staging stable 1 semaine
- ✅ Backup/restore testé
- ✅ Monitoring et alerting opérationnels
- ✅ Documentation complète

**NO-GO si** :
- ❌ Vulnérabilités critiques non patchées
- ❌ Tests échouent
- ❌ Pas de backup fonctionnel
- ❌ Pas de monitoring
- ❌ Performance non validée

---

## 📞 Support

**Contacts** :
- Oncall : [number]
- Escalation : [email]
- Status page : [url]

**Resources** :
- Runbook : `/docs/runbook.md`
- Monitoring : [dashboard url]
- Logs : [logs url]

---

**Production ready !** 🚀

Dernière révision : 2025-12-31
Version checklist : 1.0.0
