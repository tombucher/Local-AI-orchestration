"""
Espace de travail partagé entre les tâches de code d'un même projet.

Sans cela, chaque tâche génère son fichier en aveugle : la tâche « structure HTML »
ignore qu'une autre tâche produira `styles.css`, donc elle n'ajoute aucun <link>,
et la tâche d'intégration finit par tout réécrire dans un seul fichier.

Deux garanties ici :
1. un **plan de fichiers** déterministe, identique pour toutes les tâches du projet,
   calculé à partir des titres/descriptions (donc disponible avant toute génération) ;
2. l'injection du **code déjà produit** par les tâches dont dépend la tâche courante,
   pour que les noms de classes, d'id et de fonctions soient réellement partagés.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.task import Task, TaskStatus, TaskType, task_dependencies
from app.services.code_cleanup import split_multi_file
from app.services.code_contract import extract_contract, format_contract
from app.services.code_language import effective_path, file_slug

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceContext:
    """Contexte d'atelier d'une tâche de code."""

    text: str                                  # Bloc à injecter dans le prompt
    own_path: Optional[str] = None             # Fichier attribué à la tâche courante
    file_plan: Dict[int, Optional[str]] = field(default_factory=dict)
    # Page autonome écrite en trois fichiers (HTML, CSS, JS), un appel au
    # modèle chacun ; vide si la tâche produit un seul fichier
    bundle: List[str] = field(default_factory=list)

# Budget de caractères pour le code des autres tâches injecté dans le prompt.
# 4 000 par fichier coupait un HTML ordinaire en deux : le CSS et le JS ne
# voyaient pas la moitié des éléments et en inventaient d'autres. Les modèles
# tournent avec 16 à 32 k tokens de contexte, ces valeurs y tiennent largement.
MAX_CONTEXT_CHARS = 20000
MAX_CHARS_PER_FILE = 12000
# Les fichiers d'une même page se voient en entier (ou presque) : ce sont trois
# morceaux d'un seul livrable
MAX_CHARS_PAGE = 40000

EXTENSIONS = (
    'html', 'htm', 'css', 'scss', 'sass', 'js', 'mjs', 'cjs', 'jsx', 'ts', 'tsx',
    'py', 'json', 'yaml', 'yml', 'md', 'sh', 'sql', 'toml', 'ini', 'env',
    'vue', 'svelte', 'c', 'cpp', 'h', 'hpp', 'rs', 'go', 'java', 'rb', 'php', 'svg',
)

_QUOTED_FILE_RE = re.compile(
    r'[`"\'«]\s*([\w][\w\-./]*\.(?:' + '|'.join(EXTENSIONS) + r'))\s*[`"\'»]',
    re.IGNORECASE,
)
_BARE_FILE_RE = re.compile(
    r'(?<![\w/.-])([\w][\w\-./]*\.(?:' + '|'.join(EXTENSIONS) + r'))(?![\w])',
    re.IGNORECASE,
)

# Noms de bibliothèques qui ressemblent à des fichiers mais n'en sont pas
NOT_FILENAMES = {
    'node.js', 'next.js', 'nuxt.js', 'vue.js', 'react.js', 'three.js', 'd3.js',
    'p5.js', 'chart.js', 'express.js', 'alpine.js', 'htmx.js', 'gsap.js',
    'socket.io', 'tone.js', 'anime.js', 'ml5.js', 'paper.js', 'matter.js',
}

# Devine l'extension quand aucun nom de fichier n'est écrit noir sur blanc.
# L'ordre compte : la première règle qui matche gagne.
KEYWORD_RULES: List[tuple] = [
    (r'\bdockerfile\b', 'Dockerfile'),
    (r'\bread\s*me\b', 'README.md'),
    (r'\b(sql|schéma\s+de\s+la\s+base|schema\s+de\s+la\s+base|migration)\b', 'schema.sql'),
    # Fichier nommé sans ambiguïté par sa technique : il gagne sur le sujet
    (r'\b(css|feuille\s+de\s+style)\b', 'styles.css'),
    (r'(?<![\w.])(javascript|js)\b|\bscript\s+client\b|\blogique\s+client\b', 'app.js'),
    # Ce qui se regarde est une page : « animation » ou « style » dans la
    # description d'un visuel génératif en faisaient un app.js ou un styles.css
    # sans page, donc sans aperçu possible
    (r'\b(visuel|g[ée]n[ée]rati(?:f|ve)|generative|affiche|poster|maquette|mock-?ups?|prototype|'
     r'illustration|p5(?:\.js)?|canvas|motif|typographique)\b', 'PAGE'),
    (r'\b(style|styliser|stylis|mise\s+en\s+forme|responsive|charte\s+graphique)\b', 'styles.css'),
    (r'\b(serveur|server|node(?:\.js)?|express)\b', 'server.js'),
    (r'\b(javascript|\bjs\b|interactivit|interaction|script\s+client|animation|dom|logique\s+client)\b', 'app.js'),
    (r'\b(html|structure\s+de\s+la\s+page|maquette|markup|page\s+web|squelette)\b', 'index.html'),
    (r'\b(python|fastapi|flask|django|script\s+python|backend\s+python)\b', 'main.py'),
    (r'\b(typescript)\b', 'main.ts'),
]

# Types MIME approximatifs pour l'annotation des blocs de code dans le prompt
LANG_BY_EXT = {
    'html': 'html', 'htm': 'html', 'css': 'css', 'scss': 'scss', 'js': 'javascript',
    'mjs': 'javascript', 'jsx': 'jsx', 'ts': 'typescript', 'tsx': 'tsx', 'py': 'python',
    'json': 'json', 'yaml': 'yaml', 'yml': 'yaml', 'md': 'markdown', 'sh': 'bash',
    'sql': 'sql', 'vue': 'vue', 'svelte': 'svelte', 'rs': 'rust', 'go': 'go',
}


def _slugify(text: str, max_length: int = 32) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')
    return (slug[:max_length].rstrip('-') or 'fichier')


def _explicit_path(text: Optional[str]) -> Optional[str]:
    """Nom de fichier écrit explicitement dans le texte (entre quotes de préférence)."""
    if not text:
        return None
    for regex in (_QUOTED_FILE_RE, _BARE_FILE_RE):
        for match in regex.finditer(text):
            candidate = match.group(1).strip('./')
            if candidate.lower() in NOT_FILENAMES:
                continue
            if candidate.lower().startswith(('www.', 'http')):
                continue
            return candidate
    return None


def infer_artifact_path(task: Task) -> Optional[str]:
    """Déduit le fichier que cette tâche est censée produire.

    Priorité : metadata explicite > nom de fichier cité > mot-clé du titre/description.
    """
    metadata = task.task_metadata or {}
    stored = metadata.get('artifact_path')
    if stored:
        return str(stored)

    for field in (task.title, task.description, task.llm_prompt):
        found = _explicit_path(field)
        if found:
            return found

    haystack = ' '.join(filter(None, [task.title, task.description])).lower()
    for pattern, default_name in KEYWORD_RULES:
        if re.search(pattern, haystack):
            if default_name == 'PAGE':
                return f"{file_slug(task.title, 40)}.html"  # sans accents : moteur-generatif.html
            if default_name in ('main.py', 'main.ts'):
                extension = default_name.rsplit('.', 1)[1]
                return f"{_slugify(task.title)}.{extension}"
            return default_name
    return None


# Une tâche qui CRÉE une partie nouvelle (« Développement de la première
# expérience 3D ») n'est pas une tâche transverse : sans fichier à elle, elle
# réécrivait app.js en entier et effaçait le travail de la précédente
_CREATION = re.compile(
    r'^\s*(d[ée]velopp|cr[ée]ation|cr[ée]er|r[ée]alis|impl[ée]ment|programm|cod(?:er|age)|ajout|construction)',
    re.IGNORECASE)
_WEB = ('.html', '.htm', '.css', '.js', '.mjs')


def build_file_plan(tasks: List[Task]) -> Dict[int, Optional[str]]:
    """Associe à chaque tâche de code son fichier, sans collision.

    Déterministe : même entrée (tâches triées par id) ⇒ même plan, donc toutes les
    tâches du projet voient exactement les mêmes chemins.
    """
    plan: Dict[int, Optional[str]] = {}
    used: Dict[str, int] = {}
    deduits = {t.id: infer_artifact_path(t) for t in tasks}
    projet_web = any(p and p.lower().endswith(_WEB) for p in deduits.values())

    for task in sorted(tasks, key=lambda t: t.id):
        path = deduits[task.id]
        if not path and projet_web and _CREATION.match(task.title or ''):
            path = f"{file_slug(task.title, 40)}.js"
        if not path:
            plan[task.id] = None
            continue
        if path in used:
            stem, _, extension = path.rpartition('.')
            counter = 2
            candidate = path
            while candidate in used:
                candidate = f"{stem}-{counter}.{extension}" if extension else f"{path}-{counter}"
                counter += 1
            path = candidate
        used[path] = task.id
        plan[task.id] = path
    return plan


PAGE_EXTENSIONS = ('.html', '.htm')
STYLE_SCRIPT_EXTENSIONS = ('.css', '.scss', '.sass', '.js', '.mjs', '.cjs', '.jsx', '.ts', '.tsx')


def bundle_paths(own_path: Optional[str], plan: Dict[int, Optional[str]], task_id: int) -> List[str]:
    """Les trois fichiers d'une page qu'aucune autre tâche ne stylise ni n'anime.

    Une tâche « moteur génératif » ou « maquette » rendait une seule page de
    30 000 caractères, styles et script compris : illisible à la revue, et au
    bord de la limite de sortie du modèle. Elle écrit désormais `x.html`,
    `x.css` et `x.js`, un appel chacun. Si une autre tâche du projet produit
    déjà le CSS ou le JS (projet découpé en tâches HTML / CSS / JS), rien ne
    change : chaque tâche garde son fichier.
    """
    if not own_path or not own_path.lower().endswith(PAGE_EXTENSIONS):
        return []
    autres = [p for tid, p in plan.items() if tid != task_id and p]
    if any(p.lower().endswith(STYLE_SCRIPT_EXTENSIONS) for p in autres):
        return []
    racine = own_path.rsplit('.', 1)[0]
    return [own_path, f"{racine}.css", f"{racine}.js"]


ROLES_BUNDLE = {
    'html': (
        "la STRUCTURE de la page : balisage et contenus. Aucune balise <style>, aucun attribut style, "
        "aucun script écrit dans la page. Dans le <head> : `<link rel=\"stylesheet\" href=\"{css}\">`, "
        "et les bibliothèques via CDN (p5.js…) par `<script src=\"https://…\">`. Avant `</body>` : "
        "`<script src=\"{js}\" defer></script>`. Donne un id ou une classe explicite à chaque élément "
        "que les styles ou le script utiliseront (boutons, réglages, conteneurs, canvas)."
    ),
    'css': (
        "les STYLES : tous les éléments, id et classes du HTML ci-dessus, et les classes que le script "
        "créera. Variables CSS en tête (`:root`) pour les couleurs et les polices. Rien d'autre que du CSS."
    ),
    'js': (
        "le COMPORTEMENT : branche les éléments du HTML ci-dessus par leurs id et classes exacts "
        "(n'en crée pas d'autres à leur place), dessin, interactions, export. Le fichier est chargé avec "
        "`defer` : le DOM est prêt. Rien d'autre que du JavaScript."
    ),
}


def bundle_step_context(base: str, bundle: List[str], cible: str, deja: Dict[str, str],
                        ajustement: bool = False) -> str:
    """Contexte d'un des trois appels : ce qui est déjà écrit, et le fichier à écrire."""
    html, css, js = bundle
    role = 'html' if cible == html else 'css' if cible == css else 'js'
    lignes = [base, "", "### Cette tâche : une page en trois fichiers",
              f"`{html}` (structure), `{css}` (styles), `{js}` (comportement), écrits un par un."]
    for chemin, contenu in deja.items():
        if chemin == cible and not ajustement:
            continue
        if role == 'js' and chemin == css:
            # Le script n'a besoin que des noms que la feuille stylise : la
            # feuille entière alourdissait le prompt de 7 000 caractères, et un
            # prompt trop long laisse le modèle local muet plus de 5 minutes
            contrat = extract_contract(chemin, contenu)
            if not contrat.is_empty():
                lignes += ["", f"#### `{chemin}` (déjà écrit, résumé : noms à réutiliser)",
                           format_contract(chemin, contrat)]
            continue
        etiquette = "version actuelle, à corriger" if chemin == cible else "déjà écrit, fait foi"
        # En entier : coupé à 12 000 caractères, le script à corriger semblait
        # inachevé et le modèle le « complétait » au lieu de le corriger
        corps = contenu.strip()
        if len(corps) > MAX_CHARS_PAGE:
            corps = corps[:MAX_CHARS_PAGE] + "\n… (tronqué ici pour la place, le fichier continue)"
        lignes += ["", f"#### `{chemin}` ({etiquette})", f"```{_language_for(chemin)}", corps, "```"]
    consigne = ROLES_BUNDLE[role].format(css=css, js=js)
    if ajustement:
        lignes += ["", f"### À faire maintenant : réécris `{cible}` en entier, corrigé selon le feedback.",
                   "Ne change que ce que le feedback demande ; garde les id, classes et noms de fonctions "
                   "que les autres fichiers utilisent.", f"Ce fichier contient {consigne}"]
    else:
        lignes += ["", f"### À faire maintenant : écris `{cible}`, et lui seul.", f"Ce fichier contient {consigne}"]
    lignes.append("Réponds avec le contenu brut de ce fichier, sans marqueur `===`, sans phrase ni balises ```.")
    return "\n".join(lignes)


def _language_for(path: Optional[str]) -> str:
    if not path or '.' not in path:
        return ''
    return LANG_BY_EXT.get(path.rsplit('.', 1)[1].lower(), '')


async def _dependency_ids(db: AsyncSession, task_id: int) -> List[int]:
    result = await db.execute(
        select(task_dependencies.c.depends_on_id).where(task_dependencies.c.task_id == task_id)
    )
    return [row[0] for row in result.all()]


async def build_workspace_context(
    db: AsyncSession, task: Task, project: Optional[Project] = None
) -> WorkspaceContext:
    """Construit le contexte partagé injecté dans le prompt de génération."""
    if project is None:
        project = (await db.execute(select(Project).where(Project.id == task.project_id))).scalar_one_or_none()

    siblings = (await db.execute(
        select(Task).where(
            Task.project_id == task.project_id,
            Task.task_type == TaskType.CODE_GENERATION,
            Task.status != TaskStatus.CANCELLED,
        ).order_by(Task.id)
    )).unique().scalars().all()

    if not siblings:
        siblings = [task]
    elif all(sibling.id != task.id for sibling in siblings):
        siblings = list(siblings) + [task]

    plan = build_file_plan(list(siblings))
    # Un fichier déjà écrit dont le contenu contredit l'extension (du Python
    # nommé index.html) : les tâches suivantes doivent le voir sous son vrai nom
    for sibling in siblings:
        if sibling.id != task.id and plan.get(sibling.id) and (sibling.generated_code or '').strip():
            plan[sibling.id] = effective_path(plan[sibling.id], sibling.generated_code,
                                              file_slug(sibling.title))
    own_path = plan.get(task.id)
    bundle = bundle_paths(own_path, plan, task.id)
    dependency_ids = set(await _dependency_ids(db, task.id))

    sections: List[str] = ["## Contexte partagé du projet"]

    if project:
        sections.append(f"Projet : {project.name}")
        if project.description:
            sections.append(f"Objectif : {project.description.strip()[:600]}")

    # --- Plan de fichiers ---------------------------------------------------
    planned = [s for s in siblings if plan.get(s.id)]
    if planned:
        lines = ["", "### Plan de fichiers (une tâche = un fichier)"]
        for sibling in planned:
            marks = []
            if sibling.id == task.id:
                marks.append("← TÂCHE COURANTE")
            elif sibling.id in dependency_ids:
                marks.append("dépendance")
            if sibling.generated_code:
                marks.append("déjà généré")
            suffix = f" [{', '.join(marks)}]" if marks else ""
            chemins = ", ".join(f"`{p}`" for p in bundle) if sibling.id == task.id and bundle \
                else f"`{plan[sibling.id]}`"
            lines.append(f"- {chemins} — {sibling.title}{suffix}")
        sections.append('\n'.join(lines))

    # --- Règles d'intégration ----------------------------------------------
    rules = ["", "### Règles d'intégration (impératives)"]
    if bundle:
        rules.append(f"1. Cette tâche produit trois fichiers, `{bundle[0]}`, `{bundle[1]}` et `{bundle[2]}`, "
                     "écrits un par un : à chaque étape, UNIQUEMENT le fichier demandé.")
    elif own_path:
        rules.append(f"1. Tu produis UNIQUEMENT le contenu de `{own_path}`, rien d'autre.")
    else:
        # Tâche transverse (intégration, relecture…) : elle ne crée pas de fichier,
        # elle en modifie. Sans cette consigne le modèle réécrit tout dans un seul bloc.
        rules.append(
            "1. Cette tâche ne crée AUCUN nouveau fichier : elle corrige ou complète ceux du plan. "
            "Pour chaque fichier modifié, écris une ligne `=== chemin/du/fichier ===` puis son contenu "
            "complet mis à jour. Ne touche pas aux fichiers qui n'ont pas besoin de changer."
        )
    rules += [
        "2. Les autres fichiers du plan existent (ou existeront) : ne les réécris pas et n'inline jamais leur contenu.",
        "3. Dans un fichier HTML, relie les autres fichiers avec les chemins EXACTS du plan : "
        "`<link rel=\"stylesheet\" href=\"styles.css\">` dans le `<head>` et "
        "`<script src=\"app.js\" defer></script>` avant `</body>`.",
        "4. Le contrat d'interface ci-dessous fait foi : réutilise à l'identique ses identifiants, classes "
        "et variables CSS — ne les renomme pas. Une feuille de styles stylise les classes du HTML ET celles "
        "que le script crée ; un script branche les éléments prévus par le HTML (boutons, conteneurs) au "
        "lieu d'en créer d'autres à leur place.",
        "5. Si le code d'une dépendance manque, appuie-toi sur son intitulé et reste cohérent avec le plan.",
        "6. Aucun texte hors du fichier : pas de phrase d'introduction, pas de balises ``` autour du code.",
    ]
    sections.append('\n'.join(rules))

    # --- Contrat d'interface -----------------------------------------------
    # Toujours complet, même quand le code lui-même doit être tronqué plus bas.
    contrats = []
    for sibling in siblings:
        path = plan.get(sibling.id)
        if sibling.id == task.id or not path or not (sibling.generated_code or '').strip():
            continue
        for chemin, contenu in (split_multi_file(sibling.generated_code) or {path: sibling.generated_code}).items():
            contrat = extract_contract(chemin, contenu)
            if not contrat.is_empty():
                contrats.append(format_contract(chemin, contrat))
    if contrats:
        sections.append("\n### Contrat d'interface (liste exhaustive des noms déjà utilisés)\n"
                        + "\n".join(contrats))

    # --- Code déjà produit --------------------------------------------------
    # Les dépendances d'abord : ce sont les contrats que la tâche courante doit respecter.
    with_code = [s for s in siblings if s.id != task.id and (s.generated_code or '').strip()]
    with_code.sort(key=lambda s: (0 if s.id in dependency_ids else 1, s.id))

    budget = MAX_CONTEXT_CHARS
    excerpts: List[str] = []
    for sibling in with_code:
        if budget <= 0:
            break
        path = plan.get(sibling.id) or f"tâche #{sibling.id}"
        code = (sibling.generated_code or '').strip()
        limit = min(MAX_CHARS_PER_FILE, budget)
        truncated = len(code) > limit
        body = code[:limit] + ("\n… (tronqué)" if truncated else "")
        budget -= len(body)
        excerpts.append(f"#### `{path}` — {sibling.title}\n```{_language_for(path)}\n{body}\n```")

    if excerpts:
        sections.append("\n### Code déjà produit par les autres tâches\n" + "\n\n".join(excerpts))
    else:
        sections.append("\n### Code déjà produit par les autres tâches\nAucun pour l'instant : "
                        "respecte strictement le plan de fichiers ci-dessus pour rester compatible.")

    return WorkspaceContext(text='\n'.join(sections), own_path=own_path, file_plan=plan, bundle=bundle)
