"""
Consignes pour produire des livrables utilisables, pas des exercices de style.

Constat du 11/11/2026 sur un vrai appel d'offres (identité visuelle d'un
festival) : huit tâches « terminées », rien d'utilisable. Le mémoire technique
tenait en trois paragraphes génériques, l'offre financière n'avait aucun
montant, la « recherche » était la liste des sites qu'il faudrait consulter,
et le cahier des charges fourni par l'utilisateur arrivait tronqué.

Ce module rassemble les prompts des livrables texte (documents, recherches)
pour qu'ils soient lisibles, testables et cohérents entre eux.
"""

from typing import Iterable, List, Optional, Sequence

REGLES_LIVRABLE = """## Règles
- Ce texte sera utilisé tel quel par l'auteur du projet : il doit être prêt à servir.
- Concret et spécifique : des noms (polices, couleurs en hexadécimal, formats, dates, montants, \
quantités), pas des catégories (« une police display audacieuse », « une palette chaleureuse »). \
Quand il faut choisir, tranche et argumente en une phrase ; une proposition nette vaut mieux que \
trois options vagues.
- Réponds aux documents de référence au lieu de les paraphraser : chaque exigence du cahier des \
charges ou du brief a sa réponse, dans l'ordre du document quand c'est pertinent.
- Pas de remplissage : pas d'introduction qui annonce le plan, pas de conclusion qui résume, pas \
de « nous restons à votre disposition », pas de rappel de ce que le lecteur sait déjà.
- Devis, budget, planning, grille : un tableau Markdown avec des lignes, des quantités, des \
montants ou des dates, et un total. Quand une donnée manque (taux horaire, nom, SIRET, délai), \
écris [À COMPLÉTER : ce qui manque] à l'endroit exact, puis liste ces points à la fin sous le \
titre « À compléter par toi ».
- Longueur : celle qu'il faut pour que le document soit utilisable. Un mémoire technique ou une \
réponse à un appel d'offres fait plusieurs pages ; une note tient en une.
- Markdown, en français. Parle à la place de l'auteur du projet (« je » pour un indépendant, \
« nous » pour une structure), jamais « le prestataire »."""

SYSTEME_LIVRABLE = (
    "Tu rédiges pour un créateur indépendant (art numérique, graphisme, tech) les documents "
    "qu'il doit remettre. Tu écris net, précis, sans jargon de cabinet ni formules creuses. "
    "Tu n'inventes pas de faits : ce qui manque est signalé [À COMPLÉTER : …]."
)


def _bloc(titre: str, contenu: Optional[str]) -> str:
    contenu = (contenu or "").strip()
    return f"## {titre}\n{contenu}\n\n" if contenu else ""


def prompt_document(
    *,
    project_name: str,
    project_description: Optional[str],
    brief: str,
    plan: Sequence[str] = (),
    documents: Optional[str] = None,
    upstream: Optional[str] = None,
    feedback: Optional[str] = None,
) -> str:
    """Prompt d'un document à produire pour une tâche de rédaction."""
    parties = [f"Tu produis un livrable pour le projet « {project_name} ».\n\n"]
    parties.append(_bloc("Le projet", project_description))
    parties.append(_bloc("Ce qu'il faut produire", brief))
    if plan:
        parties.append("## Plan attendu\n" + "\n".join(f"- {p}" for p in plan) + "\n\n")
    if documents:
        parties.append(documents.strip() + "\n\n")
    if upstream:
        parties.append(upstream.strip() + "\n\n")
    if feedback:
        parties.append(_bloc("Remarques sur la version précédente (à prendre en compte)", feedback))
    parties.append(REGLES_LIVRABLE)
    parties.append("\n\nÉcris le document, directement, en commençant par son titre.")
    return "".join(parties)


def prompt_requetes(project_name: str, project_description: Optional[str],
                    task_title: str, task_brief: Optional[str]) -> str:
    """Demande au modèle rapide les requêtes web d'une tâche de recherche."""
    return f"""Projet : {project_name}
{(project_description or '').strip()[:800]}

Recherche à mener : {task_title}
{(task_brief or '').strip()[:1200]}

Propose 3 à 5 requêtes pour un moteur de recherche web, qui trouveraient les pages répondant à cette \
recherche. Précises : noms propres, lieux, années, termes exacts du domaine. En français, ou en anglais \
si le sujet est international. Une requête par ligne, sans numéro, sans guillemets, sans commentaire."""


def parser_requetes(texte: str, maximum: int = 5) -> List[str]:
    """Lignes du modèle → requêtes propres (sans puces, numéros ni guillemets)."""
    requetes: List[str] = []
    for ligne in (texte or "").splitlines():
        ligne = ligne.strip().lstrip("-•*0123456789.) ").strip().strip('"«»')
        if len(ligne) < 4 or len(ligne) > 160 or ligne.lower().startswith(("voici", "requête")):
            continue
        if ligne not in requetes:
            requetes.append(ligne)
    return requetes[:maximum]


def prompt_synthese(
    *,
    project_name: str,
    project_description: Optional[str],
    brief: str,
    requetes: Iterable[str],
    sources: Sequence[dict],
    documents: Optional[str] = None,
    upstream: Optional[str] = None,
) -> str:
    """Prompt de synthèse d'une recherche web, sources numérotées."""
    parties = [f"Tu réponds à une recherche pour le projet « {project_name} ».\n\n"]
    parties.append(_bloc("Le projet", project_description))
    parties.append(_bloc("Ce qu'il faut trouver", brief))
    if documents:
        parties.append(documents.strip() + "\n\n")
    if upstream:
        parties.append(upstream.strip() + "\n\n")

    parties.append("## Requêtes lancées\n" + "\n".join(f"- {q}" for q in requetes) + "\n\n")
    if sources:
        parties.append("## Sources lues\n")
        for i, s in enumerate(sources, 1):
            parties.append(f"[{i}] {s.get('title') or s['url']} — {s['url']}\n{(s.get('text') or '').strip()}\n\n")
    else:
        parties.append("## Sources lues\nAucune page exploitable n'a pu être lue.\n\n")

    parties.append("""## Ce que tu rends
Une synthèse en Markdown, en français, qui RÉPOND à la recherche avec ce que disent les sources :
- D'abord l'essentiel : les réponses, chiffrées et datées quand les sources le permettent, chacune suivie \
de sa source entre crochets, par exemple [2].
- Puis le détail utile au projet : ce qui change une décision, ce qu'il faut retenir, toujours sourcé.
- Une partie « Ce que les sources ne disent pas » : les questions restées sans réponse, et où ou auprès \
de qui les obtenir (service, document à demander, adresse précise).
- Termine par « Sources » : la liste numérotée des pages réellement citées, avec leur adresse.
N'invente rien : une information absente des sources est signalée comme manquante. N'écris ni plan de \
recherche ni méthodologie. Si les sources sont vides ou hors sujet, dis-le en une ligne et donne les 3 à 5 \
pistes précises (adresse exacte, interlocuteur) pour obtenir l'information.""")
    return "".join(parties)
