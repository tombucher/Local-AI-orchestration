/**
 * Moodboard du projet — références visuelles collectées par la veille visuelle.
 * - Masonry en CSS columns, lazy loading
 * - Lightbox maison (image + source + licence)
 * - Épingler / écarter (statuts SAVED / DISMISSED)
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Bookmark, X, ExternalLink, Image } from 'lucide-react';
import { Navbar } from '../../components/Layout/Navbar';
import { Sidebar } from '../../components/Layout/Sidebar';
import { EmptyState } from '../../components/EmptyState';
import { api } from '../../services/api';
import { tasksService } from '../../services/tasks';
import type { VeilleResult } from '../../types/task.types';
import { TaskType } from '../../types/task.types';
import { VeilleResultStatus } from '../../types/task.types';
import Loader from '../../components/ui/Loader';

export const ProjectMoodboard = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [items, setItems] = useState<VeilleResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [lightbox, setLightbox] = useState<VeilleResult | null>(null);

  useEffect(() => {
    if (!id) return;
    api
      .get<{ items: VeilleResult[]; total: number }>(`/projects/${id}/visual-references`)
      .then((r) => setItems(r.data.items))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  const setStatus = useCallback(async (result: VeilleResult, status: VeilleResultStatus) => {
    try {
      const updated = await tasksService.updateVeilleResult(result.id, { status });
      if (status === VeilleResultStatus.DISMISSED) {
        setItems((prev) => prev.filter((i) => i.id !== result.id));
        setLightbox((lb) => (lb?.id === result.id ? null : lb));
      } else {
        setItems((prev) => prev.map((i) => (i.id === result.id ? updated : i)));
        setLightbox((lb) => (lb?.id === result.id ? updated : lb));
      }
    } catch {
      // Erreur déjà toastée par l'intercepteur API
    }
  }, []);

  // Fermer la lightbox sur Échap
  useEffect(() => {
    if (!lightbox) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setLightbox(null);
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [lightbox]);

  const pinned = items.filter((i) => i.status === VeilleResultStatus.SAVED);
  const others = items.filter((i) => i.status !== VeilleResultStatus.SAVED);
  const ordered = [...pinned, ...others];

  return (
    <div className="min-h-screen bg-paper">
      <Navbar />
      <div className="flex">
        <Sidebar />

        <main className="flex-1 p-6 lg:p-10">
          <header className="mb-8">
            <Link
              to={`/projects/${id}`}
              className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-accent transition-colors mb-3"
            >
              <ArrowLeft className="w-4 h-4" /> Retour au projet
            </Link>
            <div className="flex items-baseline justify-between gap-4 flex-wrap">
              <h1 className="font-display text-4xl text-ink tracking-tight">Moodboard</h1>
              <p className="text-xs text-ink-faint figures">
                {items.length} référence{items.length > 1 ? 's' : ''}
                {pinned.length > 0 && ` · ${pinned.length} épinglée${pinned.length > 1 ? 's' : ''}`}
              </p>
            </div>
            <div className="rule-strong mt-4" />
          </header>

          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader size="lg" />
            </div>
          ) : ordered.length === 0 ? (
            <EmptyState
              icon={Image}
              title="Pas encore de références visuelles"
              description="Le moodboard se remplit tout seul à partir d'une veille de type « visuelle ». Une veille d'actualités, elle, ne ramène que des liens d'articles. Sources : Openverse, Wikimedia Commons, Art Institute of Chicago, Met Museum, Are.na et flux design."
              action={{
                label: 'Créer une veille visuelle',
                onClick: () =>
                  navigate(
                    `/tasks/new?project_id=${id}&task_type=${TaskType.VEILLE}&veille_scope=visual`,
                  ),
              }}
            />
          ) : (
            <div className="columns-2 md:columns-3 xl:columns-4 gap-4 [column-fill:_balance]">
              {ordered.map((item) => (
                <figure
                  key={item.id}
                  className={`group relative mb-4 break-inside-avoid border bg-paper-card cursor-zoom-in
                    ${item.status === VeilleResultStatus.SAVED ? 'border-highlight border-2' : 'border-ink-line'}`}
                  onClick={() => setLightbox(item)}
                >
                  <img
                    src={item.thumbnail_url || item.image_url || ''}
                    alt={item.title}
                    loading="lazy"
                    referrerPolicy="no-referrer"
                    className="w-full block"
                    onError={(e) => {
                      (e.target as HTMLImageElement).closest('figure')!.style.display = 'none';
                    }}
                  />
                  {/* Actions au survol */}
                  <div
                    className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      onClick={() =>
                        setStatus(
                          item,
                          item.status === VeilleResultStatus.SAVED
                            ? VeilleResultStatus.READ
                            : VeilleResultStatus.SAVED
                        )
                      }
                      title={item.status === VeilleResultStatus.SAVED ? 'Désépingler' : 'Épingler'}
                      className={`p-1.5 border border-ink-line transition-colors ${
                        item.status === VeilleResultStatus.SAVED
                          ? 'bg-highlight text-ink'
                          : 'bg-paper-card/90 text-ink-soft hover:text-ink'
                      }`}
                    >
                      <Bookmark className={`w-3.5 h-3.5 ${item.status === VeilleResultStatus.SAVED ? 'fill-current' : ''}`} />
                    </button>
                    <button
                      onClick={() => setStatus(item, VeilleResultStatus.DISMISSED)}
                      title="Écarter"
                      className="p-1.5 bg-paper-card/90 border border-ink-line text-ink-soft hover:text-danger transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <figcaption className="px-2.5 py-2 text-[11px] text-ink-faint truncate">
                    {item.title}
                  </figcaption>
                </figure>
              ))}
            </div>
          )}
        </main>
      </div>

      {/* Lightbox */}
      {lightbox && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink/85 p-6"
          onClick={() => setLightbox(null)}
        >
          <div
            className="max-w-4xl max-h-full overflow-auto bg-paper-card border border-ink-line shadow-lifted animate-fade-up"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={lightbox.image_url || lightbox.thumbnail_url || ''}
              alt={lightbox.title}
              referrerPolicy="no-referrer"
              className="max-h-[70vh] w-auto mx-auto block"
            />
            <div className="p-4 flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="font-display text-lg text-ink leading-snug">{lightbox.title}</p>
                {lightbox.description && (
                  <p className="text-sm text-ink-soft mt-1">{lightbox.description}</p>
                )}
                <p className="text-[11px] text-ink-faint mt-2">
                  {lightbox.source_platform}
                  {lightbox.license && <> · Licence : {lightbox.license}</>}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {lightbox.url && (
                  <a
                    href={lightbox.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 text-ink-soft hover:text-accent transition-colors"
                    title="Voir la source"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                )}
                <button
                  onClick={() =>
                    setStatus(
                      lightbox,
                      lightbox.status === VeilleResultStatus.SAVED
                        ? VeilleResultStatus.READ
                        : VeilleResultStatus.SAVED
                    )
                  }
                  className={`p-2 transition-colors ${
                    lightbox.status === VeilleResultStatus.SAVED
                      ? 'text-ink bg-highlight'
                      : 'text-ink-soft hover:text-ink'
                  }`}
                  title="Épingler"
                >
                  <Bookmark className={`w-4 h-4 ${lightbox.status === VeilleResultStatus.SAVED ? 'fill-current' : ''}`} />
                </button>
                <button
                  onClick={() => setLightbox(null)}
                  className="p-2 text-ink-soft hover:text-ink transition-colors"
                  title="Fermer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectMoodboard;
