/**
 * Moodboard du projet — références visuelles collectées par la veille visuelle.
 * - Masonry en CSS columns, lazy loading
 * - Lightbox maison (image + source + licence)
 * - Épingler / écarter (statuts SAVED / DISMISSED)
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Bookmark, X, ExternalLink, Image, ImageOff, Plus, Upload } from 'lucide-react';
import { Navbar } from '../../components/Layout/Navbar';
import { Sidebar } from '../../components/Layout/Sidebar';
import { EmptyState } from '../../components/EmptyState';
import { api } from '../../services/api';
import { documentsApi } from '../../services/documentsApi';
import toast from 'react-hot-toast';
import { tasksService } from '../../services/tasks';
import type { VeilleResult } from '../../types/task.types';
import { TaskType } from '../../types/task.types';
import { VeilleResultStatus } from '../../types/task.types';
import Loader from '../../components/ui/Loader';

/**
 * Vignette du moodboard.
 *
 * Deux origines cohabitent : les images collectées par la veille (URL externes,
 * affichables directement) et celles déposées dans l'espace documents (servies
 * par un endpoint authentifié, qu'une balise <img> ne peut pas appeler — il faut
 * passer par axios puis fabriquer un blob: URL).
 */
const ImageReference = ({
  item, charge, onCharge,
}: {
  item: VeilleResult;
  charge: boolean;
  onCharge: () => void;
}) => {
  const source = item.thumbnail_url || item.image_url || '';
  const authentifiee = source.startsWith('/api/');
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [enEchec, setEnEchec] = useState(false);
  // Une référence collectée par la veille peut disparaître sans bruit : c'est du
  // bruit en moins. Une image que l'utilisateur a ajoutée lui-même, non — la voir
  // s'évaporer laisserait croire que l'ajout a échoué.
  const choisieParLUtilisateur =
    item.source_kind === 'document' || item.source_platform === 'Ajout manuel';

  useEffect(() => {
    if (!authentifiee) return;
    let objectUrl: string | null = null;
    let annule = false;
    api
      .get(source.replace('/api/v1', ''), { responseType: 'blob', silentError: true })
      .then((r) => {
        objectUrl = URL.createObjectURL(r.data as Blob);
        if (annule) URL.revokeObjectURL(objectUrl);
        else {
          setBlobUrl(objectUrl);
          onCharge();
        }
      })
      .catch(() => {});
    return () => {
      annule = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [source, authentifiee]);

  const src = authentifiee ? blobUrl : source;
  const pret = authentifiee ? Boolean(blobUrl) : charge;

  if (enEchec) {
    return (
      <div className="w-full aspect-[4/3] bg-paper-warm border-b border-ink-line flex flex-col items-center justify-center gap-2 px-3 text-center">
        <ImageOff className="w-5 h-5 text-ink-faint" />
        <p className="text-[11px] text-ink-faint leading-snug">
          Image introuvable à cette adresse
        </p>
      </div>
    );
  }

  return (
    <div className="relative">
      {!pret && <div className="w-full aspect-[4/3] bg-paper-warm animate-pulse" />}
      {src && (
        <img
          src={src}
          alt={item.title}
          loading={authentifiee ? undefined : 'lazy'}
          referrerPolicy="no-referrer"
          className={`w-full block transition-opacity duration-300 ${
            pret ? 'opacity-100' : 'absolute inset-0 h-full opacity-0'
          }`}
          onLoad={onCharge}
          onError={(e) => {
            if (choisieParLUtilisateur) {
              setEnEchec(true);   // garder la vignette, signaler le problème
            } else {
              (e.target as HTMLImageElement).closest('figure')!.style.display = 'none';
            }
          }}
        />
      )}
    </div>
  );
};

export const ProjectMoodboard = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [items, setItems] = useState<VeilleResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [lightbox, setLightbox] = useState<VeilleResult | null>(null);
  const [charges, setCharges] = useState<Set<number>>(new Set());
  const [ajoutOuvert, setAjoutOuvert] = useState(false);
  const [urlImage, setUrlImage] = useState('');
  const [titreImage, setTitreImage] = useState('');
  const [ajoutEnCours, setAjoutEnCours] = useState(false);
  const inputFichier = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!id) return;
    api
      .get<{ items: VeilleResult[]; total: number }>(`/projects/${id}/visual-references`)
      .then((r) => setItems(r.data.items))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  const recharger = useCallback(async () => {
    if (!id) return;
    const r = await api.get<{ items: VeilleResult[]; total: number }>(
      `/projects/${id}/visual-references`,
    );
    setItems(r.data.items);
  }, [id]);

  /** Épingle une image trouvée ailleurs, à partir de son adresse */
  const ajouterParUrl = async () => {
    if (!urlImage.trim() || !id) return;
    setAjoutEnCours(true);
    try {
      await api.post(`/projects/${id}/visual-references`, {
        url: urlImage.trim(),
        title: titreImage.trim() || undefined,
      });
      setUrlImage('');
      setTitreImage('');
      await recharger();
      toast.success('Image épinglée au moodboard');
    } catch {
      // Motif déjà affiché par l'intercepteur API
    } finally {
      setAjoutEnCours(false);
    }
  };

  /** Les fichiers passent par l'espace documents : ils servent aussi de contexte à l'IA */
  const televerser = async (fichiers: FileList | null) => {
    if (!fichiers?.length || !id) return;
    setAjoutEnCours(true);
    for (const fichier of Array.from(fichiers)) {
      try {
        await documentsApi.upload(parseInt(id), fichier);
        toast.success(`« ${fichier.name} » ajouté`);
      } catch {
        /* déjà toasté */
      }
    }
    await recharger();
    setAjoutEnCours(false);
    if (inputFichier.current) inputFichier.current.value = '';
  };

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

        <main className="flex-1 min-w-0 p-6 lg:p-10">
          <header className="mb-8">
            <Link
              to={`/projects/${id}`}
              className="inline-flex items-center gap-1.5 text-sm text-ink-soft hover:text-accent transition-colors mb-3"
            >
              <ArrowLeft className="w-4 h-4" /> Retour au projet
            </Link>
            <div className="flex items-baseline justify-between gap-4 flex-wrap">
              <h1 className="font-display text-4xl text-ink tracking-tight">Moodboard</h1>
              <div className="flex items-center gap-3">
                <p className="text-xs text-ink-faint figures">
                  {items.length} référence{items.length > 1 ? 's' : ''}
                  {pinned.length > 0 && ` · ${pinned.length} épinglée${pinned.length > 1 ? 's' : ''}`}
                </p>
                <button
                  onClick={() => setAjoutOuvert((v) => !v)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-ink-line text-ink hover:border-accent hover:text-accent transition-colors text-xs font-medium"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Ajouter une image
                </button>
              </div>
            </div>
            <div className="rule-strong mt-4" />

            {/* Ajout manuel : une veille visuelle remplit le moodboard toute
                seule, ceci sert aux trouvailles faites ailleurs. */}
            {ajoutOuvert && (
              <div className="mt-4 p-4 border border-ink-line bg-paper-card space-y-3">
                <div className="flex flex-col sm:flex-row gap-2">
                  <input
                    value={urlImage}
                    onChange={(e) => setUrlImage(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && ajouterParUrl()}
                    placeholder="https://… (adresse directe de l'image)"
                    className="flex-1 px-3 py-2 bg-paper border border-ink-line text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent font-mono text-sm"
                  />
                  <input
                    value={titreImage}
                    onChange={(e) => setTitreImage(e.target.value)}
                    placeholder="Intitulé (facultatif)"
                    className="sm:w-56 px-3 py-2 bg-paper border border-ink-line text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent text-sm"
                  />
                  <button
                    onClick={ajouterParUrl}
                    disabled={!urlImage.trim() || ajoutEnCours}
                    className="px-4 py-2 bg-accent text-paper hover:opacity-90 disabled:opacity-40 transition-opacity text-sm font-medium whitespace-nowrap"
                  >
                    {ajoutEnCours ? 'Ajout…' : 'Épingler'}
                  </button>
                </div>
                <div className="flex items-center gap-3">
                  <input
                    ref={inputFichier}
                    type="file"
                    multiple
                    accept=".png,.jpg,.jpeg,.webp,.gif"
                    className="hidden"
                    onChange={(e) => televerser(e.target.files)}
                  />
                  <button
                    onClick={() => inputFichier.current?.click()}
                    disabled={ajoutEnCours}
                    className="inline-flex items-center gap-2 px-3 py-1.5 border border-ink-line text-ink-soft hover:border-accent hover:text-accent disabled:opacity-40 transition-colors text-sm"
                  >
                    <Upload className="w-4 h-4" />
                    …ou depuis un fichier
                  </button>
                  <span className="text-xs text-ink-faint">
                    Les fichiers rejoignent aussi les documents du projet, donc le contexte de l'IA.
                  </span>
                </div>
              </div>
            )}
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
            <div className="columns-2 md:columns-3 xl:columns-4 2xl:columns-5 gap-4 [column-fill:_balance] max-w-[1600px]">
              {ordered.map((item) => (
                <figure
                  key={item.id}
                  className={`group relative mb-4 break-inside-avoid border bg-paper-card cursor-zoom-in overflow-hidden
                    ${item.status === VeilleResultStatus.SAVED ? 'border-highlight border-2' : 'border-ink-line'}`}
                  onClick={() => setLightbox(item)}
                >
                  <ImageReference
                    item={item}
                    charge={charges.has(item.id)}
                    onCharge={() => setCharges((prev) => new Set(prev).add(item.id))}
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
                {/* Crédit source : Pexels notamment exige un lien visible vers
                    la plateforme et le nom du photographe. */}
                <p className="text-[11px] text-ink-faint mt-2">
                  {lightbox.url ? (
                    <a
                      href={lightbox.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline decoration-ink-line hover:text-accent transition-colors"
                    >
                      {lightbox.source_platform}
                    </a>
                  ) : (
                    lightbox.source_platform
                  )}
                  {lightbox.license && <> · {lightbox.license}</>}
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
