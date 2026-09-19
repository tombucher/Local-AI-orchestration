"""
Script de seeding données démo.

Usage:
    docker exec -it orchestrator-backend python scripts/seed_demo_data.py

Crée:
- 1 user demo (demo@example.com / demo123)
- 3 projets variés (PRO, perso, research)
- 15 tâches avec différents status
- Time entries pour projet PRO
- Task logs
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Ajouter le chemin parent pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models import User, Project, Task, TaskLog, TimeEntry
from app.core.security import get_password_hash
from sqlalchemy import select


async def seed_demo_data():
    """Créer les données de démonstration."""

    async with AsyncSessionLocal() as db:
        print("🌱 Démarrage du seeding des données démo...")

        # Vérifier si l'utilisateur demo existe déjà
        result = await db.execute(
            select(User).where(User.email == "demo@example.com")
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print("⚠️  L'utilisateur demo existe déjà. Nettoyage...")
            # Supprimer toutes les données associées
            result = await db.execute(
                select(Project).where(Project.user_id == existing_user.id)
            )
            projects = result.scalars().all()

            for project in projects:
                # Supprimer les tâches
                result = await db.execute(
                    select(Task).where(Task.project_id == project.id)
                )
                tasks = result.scalars().all()
                for task in tasks:
                    await db.delete(task)

                # Supprimer le projet
                await db.delete(project)

            # Supprimer l'utilisateur
            await db.delete(existing_user)
            await db.commit()
            print("✅ Nettoyage terminé")

        # 1. Créer user demo
        print("\n👤 Création utilisateur demo...")
        user = User(
            email="demo@example.com",
            hashed_password=get_password_hash("demo123"),
            full_name="Demo User"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"✅ User créé: {user.email}")

        # 2. Projet PRO : Client A - E-commerce
        print("\n📁 Création projet PRO: Client A - E-commerce...")
        project_pro = Project(
            user_id=user.id,
            name="Client A - E-commerce",
            description="Refonte complète plateforme e-commerce avec paiements Stripe et gestion catalogue produits",
            type="professional",
            status="active",
            features={
                "code_gen": True,
                "veille": True,
                "git_auto": False
            },
            financial_config={
                "hourly_rate": 80.0,
                "budget": 8000.0,
                "currency": "EUR"
            }
        )
        db.add(project_pro)

        # 3. Projet Perso : Mon site web
        print("📁 Création projet Perso: Mon Site Web...")
        project_perso = Project(
            user_id=user.id,
            name="Mon Site Web",
            description="Portfolio personnel + blog tech avec MDX et React",
            type="personal",
            status="active",
            features={
                "code_gen": True,
                "veille": True,
                "git_auto": True
            }
        )
        db.add(project_perso)

        # 4. Projet Research : Compostage de données
        print("📁 Création projet Research: Compostage de Données...")
        project_research = Project(
            user_id=user.id,
            name="Compostage de Données",
            description="Recherche algorithmes compression/décomposition inspirés du compostage naturel",
            type="research",
            status="active",
            features={
                "code_gen": True,
                "veille": True,
                "git_auto": False
            }
        )
        db.add(project_research)

        await db.commit()
        await db.refresh(project_pro)
        await db.refresh(project_perso)
        await db.refresh(project_research)

        print(f"✅ 3 projets créés")

        # 5. Tâches Projet PRO (variées)
        print("\n📝 Création tâches projet PRO...")
        tasks_pro = [
            Task(
                project_id=project_pro.id,
                title="API REST produits",
                description="CRUD complet gestion produits avec filtres, pagination et recherche",
                priority="P1",
                status="completed",
                llm_prompt="Génère une API FastAPI avec endpoints CRUD pour produits. Utilise SQLAlchemy async, Pydantic pour validation, inclus filtres par catégorie et recherche full-text.",
                generated_code="""# Code généré par Ollama
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional

from app.core.database import get_db
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.models.product import Product

router = APIRouter()

@router.post("/products/", response_model=ProductResponse, status_code=201)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_db)
):
    \"\"\"Créer un nouveau produit.\"\"\"
    db_product = Product(**product.dict())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

@router.get("/products/", response_model=List[ProductResponse])
async def list_products(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    \"\"\"Lister tous les produits avec filtres.\"\"\"
    query = select(Product)

    if category:
        query = query.where(Product.category == category)

    if search:
        query = query.where(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%")
            )
        )

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    products = result.scalars().all()
    return products
""",
                started_at=datetime.utcnow() - timedelta(days=5),
                completed_at=datetime.utcnow() - timedelta(days=4)
            ),
            Task(
                project_id=project_pro.id,
                title="Système de paiement Stripe",
                description="Intégration Stripe checkout avec webhooks",
                priority="P1",
                status="manual_review",
                llm_prompt="Intègre Stripe avec création de checkout session, gestion webhooks pour confirmer paiement, et gestion des erreurs.",
                generated_code="""# Code généré par Ollama
import stripe
from fastapi import APIRouter, HTTPException, Request
from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter()

@router.post("/create-checkout-session")
async def create_checkout_session(amount: int, currency: str = "eur"):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'product_data': {'name': 'Purchase'},
                    'unit_amount': amount,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='https://example.com/success',
            cancel_url='https://example.com/cancel',
        )
        return {"sessionId": session.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            # Traiter le paiement réussi
            pass

        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
""",
                started_at=datetime.utcnow() - timedelta(hours=2)
            ),
            Task(
                project_id=project_pro.id,
                title="Dashboard admin",
                description="Interface admin avec statistiques ventes et produits",
                priority="P2",
                status="ready",
                llm_prompt="Crée un dashboard React avec TailwindCSS affichant stats de ventes (graphiques), top produits, et commandes récentes."
            ),
            Task(
                project_id=project_pro.id,
                title="Tests unitaires API produits",
                description="Tests pytest avec coverage 80%+",
                priority="P2",
                status="created",
                llm_prompt="Génère des tests pytest pour l'API produits: test création, lecture, update, delete, filtres, et cas d'erreur."
            ),
            Task(
                project_id=project_pro.id,
                title="Système de notifications email",
                description="Envoyer emails confirmation commande",
                priority="P3",
                status="created",
                llm_prompt="Implémente envoi emails avec SendGrid: template confirmation commande, gestion erreurs, et retry logic."
            ),
        ]

        # 6. Tâches Projet Perso
        print("📝 Création tâches projet Perso...")
        tasks_perso = [
            Task(
                project_id=project_perso.id,
                title="Blog markdown avec MDX",
                description="Système blog avec MDX, syntax highlighting et SEO",
                priority="P2",
                status="completed",
                llm_prompt="Crée composants Next.js pour blog MDX: parser markdown, syntax highlighting avec Prism, meta tags SEO.",
                generated_code="""// Code généré
import { MDXRemote } from 'next-mdx-remote/rsc'
import Prism from 'prismjs'

export default function BlogPost({ source, frontmatter }) {
  return (
    <article className="prose lg:prose-xl">
      <h1>{frontmatter.title}</h1>
      <time>{frontmatter.date}</time>
      <MDXRemote source={source} />
    </article>
  )
}""",
                completed_at=datetime.utcnow() - timedelta(days=10)
            ),
            Task(
                project_id=project_perso.id,
                title="Portfolio projets avec filtres",
                description="Galerie projets avec filtres par techno et catégorie",
                priority="P3",
                status="generating",
                llm_prompt="Crée galerie projets React avec filtres (React, Python, etc), grid responsive, et animations.",
                started_at=datetime.utcnow() - timedelta(minutes=30)
            ),
            Task(
                project_id=project_perso.id,
                title="Page contact avec formulaire",
                description="Formulaire contact avec validation et reCAPTCHA",
                priority="P3",
                status="ready",
                llm_prompt="Formulaire contact React avec validation Zod, intégration reCAPTCHA v3, et envoi via API."
            ),
        ]

        # 7. Tâches Projet Research
        print("📝 Création tâches projet Research...")
        tasks_research = [
            Task(
                project_id=project_research.id,
                title="Algorithme LZ77 optimisé",
                description="Implémentation LZ77 custom avec optimisations",
                priority="P1",
                status="failed",
                llm_prompt="Implémente algorithme compression LZ77 en Python avec optimisations (sliding window, hash table).",
                started_at=datetime.utcnow() - timedelta(days=3),
                metadata={"error": "Timeout Ollama après 5 minutes"}
            ),
            Task(
                project_id=project_research.id,
                title="Benchmark compression",
                description="Comparer LZ77, LZ78, LZMA, Brotli, Zstandard",
                priority="P2",
                status="ready",
                llm_prompt="Script Python pour benchmarker 5 algos compression: temps, ratio, mémoire. Graphiques avec matplotlib."
            ),
            Task(
                project_id=project_research.id,
                title="Visualisation décomposition",
                description="Interface web pour visualiser processus compression",
                priority="P3",
                status="created",
                llm_prompt="App React avec D3.js pour visualiser étapes compression/décomposition en temps réel."
            ),
        ]

        all_tasks = tasks_pro + tasks_perso + tasks_research
        for task in all_tasks:
            db.add(task)

        await db.commit()

        # Rafraîchir toutes les tâches
        for task in all_tasks:
            await db.refresh(task)

        print(f"✅ {len(all_tasks)} tâches créées")

        # 8. Time Entries (projet PRO seulement)
        print("\n⏱️  Création time entries...")
        time_entries = [
            TimeEntry(
                project_id=project_pro.id,
                task_id=tasks_pro[0].id,
                user_id=user.id,
                started_at=datetime.utcnow() - timedelta(days=5, hours=2),
                ended_at=datetime.utcnow() - timedelta(days=5),
                duration_seconds=7200,  # 2h
                notes="Développement initial API produits avec tests"
            ),
            TimeEntry(
                project_id=project_pro.id,
                task_id=tasks_pro[0].id,
                user_id=user.id,
                started_at=datetime.utcnow() - timedelta(days=4, hours=3),
                ended_at=datetime.utcnow() - timedelta(days=4, hours=1),
                duration_seconds=7200,  # 2h
                notes="Ajout filtres et pagination"
            ),
            TimeEntry(
                project_id=project_pro.id,
                task_id=tasks_pro[1].id,
                user_id=user.id,
                started_at=datetime.utcnow() - timedelta(hours=3),
                ended_at=datetime.utcnow() - timedelta(hours=1),
                duration_seconds=7200,  # 2h
                notes="Intégration Stripe checkout en cours"
            ),
            TimeEntry(
                project_id=project_pro.id,
                task_id=tasks_pro[1].id,
                user_id=user.id,
                started_at=datetime.utcnow() - timedelta(days=1, hours=4),
                ended_at=datetime.utcnow() - timedelta(days=1, hours=2, minutes=30),
                duration_seconds=5400,  # 1.5h
                notes="Configuration webhooks Stripe"
            ),
        ]

        for entry in time_entries:
            db.add(entry)

        await db.commit()
        print(f"✅ {len(time_entries)} time entries créées")

        # 9. Task Logs
        print("\n📋 Création task logs...")
        from app.models.task_log import TaskEventType

        logs = [
            # Logs pour tâche API REST (completed)
            TaskLog(
                task_id=tasks_pro[0].id,
                timestamp=datetime.utcnow() - timedelta(days=5, hours=2),
                event_type=TaskEventType.CREATED,
                details={"user_action": True, "user_id": user.id}
            ),
            TaskLog(
                task_id=tasks_pro[0].id,
                timestamp=datetime.utcnow() - timedelta(days=5, hours=1, minutes=30),
                event_type=TaskEventType.STATUS_CHANGED,
                details={"from": "created", "to": "ready"}
            ),
            TaskLog(
                task_id=tasks_pro[0].id,
                timestamp=datetime.utcnow() - timedelta(days=5, hours=1),
                event_type=TaskEventType.CODE_GENERATED,
                details={
                    "model": "devstral-small-2",
                    "tokens": 1523,
                    "generation_time_seconds": 45
                }
            ),
            TaskLog(
                task_id=tasks_pro[0].id,
                timestamp=datetime.utcnow() - timedelta(days=4, hours=23),
                event_type=TaskEventType.STATUS_CHANGED,
                details={"from": "generating", "to": "manual_review"}
            ),
            TaskLog(
                task_id=tasks_pro[0].id,
                timestamp=datetime.utcnow() - timedelta(days=4),
                event_type=TaskEventType.VALIDATED,
                details={
                    "approved": True,
                    "user_id": user.id,
                    "notes": "Code validé, prêt pour intégration"
                }
            ),

            # Logs pour tâche Stripe (manual_review)
            TaskLog(
                task_id=tasks_pro[1].id,
                timestamp=datetime.utcnow() - timedelta(hours=3),
                event_type=TaskEventType.CREATED,
                details={"user_action": True}
            ),
            TaskLog(
                task_id=tasks_pro[1].id,
                timestamp=datetime.utcnow() - timedelta(hours=2, minutes=45),
                event_type=TaskEventType.CODE_GENERATED,
                details={
                    "model": "devstral-small-2",
                    "tokens": 987,
                    "generation_time_seconds": 38
                }
            ),
            TaskLog(
                task_id=tasks_pro[1].id,
                timestamp=datetime.utcnow() - timedelta(hours=2, minutes=30),
                event_type=TaskEventType.STATUS_CHANGED,
                details={"from": "generating", "to": "manual_review"}
            ),

            # Log pour tâche failed
            TaskLog(
                task_id=tasks_research[0].id,
                timestamp=datetime.utcnow() - timedelta(days=3),
                event_type=TaskEventType.FAILED,
                details={
                    "error": "Timeout Ollama après 5 minutes",
                    "model": "devstral-small-2",
                    "retry_count": 3
                }
            ),
        ]

        for log in logs:
            db.add(log)

        await db.commit()
        print(f"✅ {len(logs)} task logs créés")

        # Statistiques finales
        print("\n" + "="*60)
        print("✅ Données démo créées avec succès!")
        print("="*60)
        print(f"\n📧 Credentials:")
        print(f"   Email: demo@example.com")
        print(f"   Password: demo123")
        print(f"\n📁 Projets: {len([project_pro, project_perso, project_research])}")
        print(f"   - {project_pro.name} (PRO)")
        print(f"   - {project_perso.name} (Personal)")
        print(f"   - {project_research.name} (Research)")
        print(f"\n📝 Tâches: {len(all_tasks)}")
        print(f"   - Completed: {len([t for t in all_tasks if t.status == 'completed'])}")
        print(f"   - Manual Review: {len([t for t in all_tasks if t.status == 'manual_review'])}")
        print(f"   - Ready: {len([t for t in all_tasks if t.status == 'ready'])}")
        print(f"   - Generating: {len([t for t in all_tasks if t.status == 'generating'])}")
        print(f"   - Created: {len([t for t in all_tasks if t.status == 'created'])}")
        print(f"   - Failed: {len([t for t in all_tasks if t.status == 'failed'])}")
        print(f"\n⏱️  Time entries: {len(time_entries)}")
        total_hours = sum(e.duration_seconds for e in time_entries) / 3600
        print(f"   Total: {total_hours:.1f}h")
        print(f"\n📋 Task logs: {len(logs)}")
        print("\n🌐 Accès:")
        print("   Frontend: http://localhost:5173")
        print("   Backend: http://localhost:8000/docs")
        print("\n")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
