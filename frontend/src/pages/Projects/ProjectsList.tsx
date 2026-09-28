/**
 * Page Liste des projets
 * - Grid de cartes
 * - Onglets par espace (dossiers du dossier de projets)
 * - Recherche
 * - Bouton créer projet
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FolderDown, Plus, Search, FolderKanban } from 'lucide-react';
import toast from 'react-hot-toast';
import { projectFoldersApi } from '../../services/projectFoldersApi';
import { useProjectsStore } from '../../stores/projectsStore';
import { Navbar } from '../../components/Layout/Navbar';
import { Sidebar } from '../../components/Layout/Sidebar';
import { ProjectCard } from '../../components/ProjectCard';
import { EmptyState } from '../../components/EmptyState';
import { ProjectStatus } from '../../types/project.types';
import Loader from '../../components/ui/Loader';
import MarkdownImport from '../../components/projects/MarkdownImport';

// Onglets : « Tous », les espaces (dossiers du dossier de projets), « Sans espace »
const TOUS = '__tous__';
const SANS_ESPACE = '__sans__';
const CLE_ONGLET = 'projets-espace';

const lireOnglet = () => {
  try {
    return localStorage.getItem(CLE_ONGLET) || TOUS;
  } catch {
    return TOUS;
  }
};

export const ProjectsList = () => {
  const navigate = useNavigate();
  const { projects, loading, fetchProjects } = useProjectsStore();

  const [onglet, setOnglet] = useState<string>(lireOnglet);
  const [espaces, setEspaces] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // Un dossier créé dans le Finder devient un espace : on relit la liste
  // à chaque rechargement des projets
  useEffect(() => {
    projectFoldersApi.spaces().then((r) => setEspaces(r.spaces)).catch(() => {});
  }, [projects]);

  const choisirOnglet = (valeur: string) => {
    setOnglet(valeur);
    try {
      localStorage.setItem(CLE_ONGLET, valeur);
    } catch {
      // préférence non mémorisée : sans conséquence
    }
  };

  const tous = Array.isArray(projects) ? projects : [];
  const aSansEspace = espaces.length > 0 && tous.some((p) => !p.space);
  const ongletValide =
    onglet === TOUS || (onglet === SANS_ESPACE ? aSansEspace : espaces.includes(onglet)) ? onglet : TOUS;
  const dansOnglet = (p: (typeof tous)[number], o: string) =>
    o === TOUS || (o === SANS_ESPACE ? !p.space : p.space === o);
  const recherche = searchQuery.trim().toLowerCase();
  const visibles = tous.filter(
    (p) =>
      dansOnglet(p, ongletValide) &&
      (!recherche || `${p.name} ${p.description ?? ''}`.toLowerCase().includes(recherche)),
  );
  const onglets = [
    { valeur: TOUS, libelle: 'Tous' },
    ...espaces.map((e) => ({ valeur: e, libelle: e })),
    ...(aSansEspace ? [{ valeur: SANS_ESPACE, libelle: 'Sans espace' }] : []),
  ];

  const [ecriture, setEcriture] = useState(false);
  const sansFiche = (Array.isArray(projects) ? projects : []).filter(
    (p) => !p.source_path && p.status !== ProjectStatus.ARCHIVED,
  ).length;

  // Dossier + fiche .md pour chaque projet de l'outil qui n'en a pas encore
  const ecrireToutesLesFiches = async () => {
    setEcriture(true);
    try {
      const { written } = await projectFoldersApi.writeAll();
      toast.success(
        written.length
          ? `${written.length} fiche(s) écrite(s) dans ton dossier de projets`
          : 'Tous tes projets ont déjà leur fiche',
      );
      fetchProjects();
    } catch {
      // l'intercepteur affiche l'erreur (ex. : aucun dossier de projets choisi)
    } finally {
      setEcriture(false);
    }
  };

  const handleCreateProject = () => {
    // Créé depuis un onglet d'espace : l'espace est prérempli
    const espace = ongletValide !== TOUS && ongletValide !== SANS_ESPACE ? ongletValide : null;
    navigate(espace ? `/projects/new?espace=${encodeURIComponent(espace)}` : '/projects/new');
  };

  const handleViewProject = (id: number) => {
    navigate(`/projects/${id}`);
  };

  return (
    <div className="min-h-screen bg-paper">
      <Navbar />

      <div className="flex">
        <Sidebar />

        <main className="flex-1 p-6 lg:p-8">
          {/* Header */}
          <div className="mb-8">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
              <div>
                <h1 className="text-3xl font-bold text-ink">Projets</h1>
                <p className="mt-2 text-ink-soft">Gérez vos projets et suivez leur progression</p>
              </div>
              <div className="flex flex-wrap gap-2 justify-end">
                {sansFiche > 0 && (
                  <button
                    onClick={ecrireToutesLesFiches}
                    disabled={ecriture}
                    title="Crée un dossier et une fiche .md, dans ton dossier de projets, pour chaque projet qui n'en a pas"
                    className="flex items-center gap-2 px-4 py-2 border border-ink-line text-ink hover:border-accent hover:text-accent disabled:opacity-40 transition-colors font-medium"
                  >
                    <FolderDown className="w-5 h-5" />
                    {ecriture ? 'Écriture…' : `Écrire les fiches (${sansFiche})`}
                  </button>
                )}
                <MarkdownImport />
                <button
                  onClick={handleCreateProject}
                  className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-none hover:bg-primary/90 transition-colors font-medium"
                >
                  <Plus className="w-5 h-5" />
                  Nouveau projet
                </button>
              </div>
            </div>

            {/* Filtres */}
            <div className="flex flex-col sm:flex-row gap-4">
              {/* Recherche */}
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-ink-faint" />
                <input
                  type="text"
                  placeholder="Rechercher un projet..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-ink-line rounded-none focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>

            </div>

            {/* Onglets d'espaces */}
            <div className="mt-4 flex flex-wrap gap-x-1 gap-y-2 border-b border-ink-line" role="tablist">
              {onglets.map(({ valeur, libelle }) => {
                const actif = ongletValide === valeur;
                const nombre = tous.filter((p) => dansOnglet(p, valeur)).length;
                return (
                  <button
                    key={valeur}
                    role="tab"
                    aria-selected={actif}
                    onClick={() => choisirOnglet(valeur)}
                    className={`px-4 py-2 -mb-px text-sm font-medium border-b-2 transition-colors ${
                      actif
                        ? 'border-accent text-ink'
                        : 'border-transparent text-ink-soft hover:text-ink hover:border-ink-line'
                    }`}
                  >
                    {libelle}
                    <span className="ml-1.5 text-xs text-ink-faint figures">{nombre}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center py-12">
              <Loader size="lg" />
            </div>
          )}

          {/* Empty State */}
          {!loading && visibles.length === 0 && (
            <EmptyState
              icon={FolderKanban}
              title={searchQuery ? 'Aucun projet trouvé' : ongletValide === TOUS ? 'Aucun projet' : 'Aucun projet dans cet espace'}
              description={
                searchQuery
                  ? 'Essayez de modifier vos critères de recherche'
                  : 'Créez votre premier projet pour commencer'
              }
              action={
                !searchQuery
                  ? {
                      label: 'Créer un projet',
                      onClick: handleCreateProject,
                    }
                  : undefined
              }
            />
          )}

          {/* Projects Grid */}
          {!loading && visibles.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {visibles.map((project) => (
                <ProjectCard key={project.id} project={project} onView={handleViewProject} />
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
