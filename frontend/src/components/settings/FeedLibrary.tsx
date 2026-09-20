/**
 * Bibliothèque de flux RSS.
 *
 * Un catalogue de sources figé ne peut pas couvrir des projets arbitraires :
 * c'est l'utilisateur qui ajoute les flux qu'il découvre. Chaque flux est vérifié
 * à l'ajout (un flux mort est refusé tout de suite) et ses thèmes sont déduits de
 * son contenu, pour que la veille choisisse les bonnes sources selon le sujet.
 */

import { useEffect, useState } from 'react';
import {
  AlertCircle, CheckCircle, Plus, RefreshCw, Rss, Trash2, XCircle,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { feedsApi } from '../../services/settingsApi';
import type { FeedCheckResult, RssFeed } from '../../types/settings';
import { extractErrorMessage } from '../../services/api';
import Loader from '../ui/Loader';
import ConfirmDialog from '../ui/ConfirmDialog';

const formatDate = (iso: string | null) =>
  iso ? new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' }) : '—';

const Tag = ({ label }: { label: string }) => (
  <span className="px-1.5 py-0.5 text-xs font-mono text-ink-soft bg-paper-warm border border-ink-line">
    {label}
  </span>
);

export const FeedLibrary = () => {
  const [feeds, setFeeds] = useState<RssFeed[]>([]);
  const [loading, setLoading] = useState(true);
  const [url, setUrl] = useState('');
  const [preview, setPreview] = useState<FeedCheckResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [adding, setAdding] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [toDelete, setToDelete] = useState<RssFeed | null>(null);

  useEffect(() => {
    feedsApi
      .list()
      .then(setFeeds)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  /** Vérifie le flux avant de l'ajouter : l'utilisateur voit ce qu'il enregistre */
  const handlePreview = async () => {
    if (!url.trim()) return;
    setChecking(true);
    setPreview(null);
    try {
      setPreview(await feedsApi.preview(url.trim()));
    } catch (error) {
      setPreview({
        ok: false,
        status: extractErrorMessage(error),
        title: '',
        tags: [],
        entry_count: 0,
        sample: [],
      });
    } finally {
      setChecking(false);
    }
  };

  const handleAdd = async () => {
    if (!url.trim()) return;
    setAdding(true);
    try {
      const feed = await feedsApi.add({ url: url.trim() });
      setFeeds((prev) => [feed, ...prev]);
      setUrl('');
      setPreview(null);
      toast.success(`« ${feed.title} » ajouté — ${feed.last_entry_count} entrées`);
    } catch {
      // Message déjà affiché par l'intercepteur API
    } finally {
      setAdding(false);
    }
  };

  const handleToggle = async (feed: RssFeed) => {
    setBusyId(feed.id);
    try {
      const updated = await feedsApi.update(feed.id, { enabled: !feed.enabled });
      setFeeds((prev) => prev.map((f) => (f.id === feed.id ? updated : f)));
    } catch {
      /* déjà toasté */
    } finally {
      setBusyId(null);
    }
  };

  const handleCheck = async (feed: RssFeed) => {
    setBusyId(feed.id);
    try {
      const updated = await feedsApi.check(feed.id);
      setFeeds((prev) => prev.map((f) => (f.id === feed.id ? updated : f)));
      const ok = updated.last_status === 'ok';
      toast[ok ? 'success' : 'error'](
        ok
          ? `« ${updated.title} » : ${updated.last_entry_count} entrées`
          : `« ${updated.title} » : ${updated.last_status}`,
      );
    } catch {
      /* déjà toasté */
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async () => {
    if (!toDelete) return;
    try {
      await feedsApi.remove(toDelete.id);
      setFeeds((prev) => prev.filter((f) => f.id !== toDelete.id));
      toast.success('Flux retiré');
    } catch {
      /* déjà toasté */
    } finally {
      setToDelete(null);
    }
  };

  return (
    <div className="bg-paper-card shadow-card border border-ink-line p-6">
      <div className="flex items-start gap-3 mb-1">
        <Rss className="w-5 h-5 text-accent mt-1 shrink-0" />
        <div>
          <h2 className="font-display text-xl text-ink">Mes flux de veille</h2>
          <p className="text-sm text-ink-soft mt-1">
            Ajoute les flux RSS que tu croises au fil de tes recherches. La veille pioche
            dedans en priorité, en choisissant ceux dont les thèmes collent au sujet.
          </p>
        </div>
      </div>

      {/* Ajout */}
      <div className="mt-5 pt-5 border-t border-ink-line">
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            type="url"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setPreview(null);
            }}
            onKeyDown={(e) => e.key === 'Enter' && handlePreview()}
            placeholder="https://exemple.org/feed/"
            className="flex-1 px-3 py-2 bg-paper border border-ink-line text-ink placeholder:text-ink-faint focus:outline-none focus:border-accent font-mono text-sm"
          />
          <button
            onClick={handlePreview}
            disabled={!url.trim() || checking}
            className="px-4 py-2 border border-ink-line text-ink hover:border-accent hover:text-accent disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-sm font-medium whitespace-nowrap"
          >
            {checking ? 'Vérification…' : 'Vérifier'}
          </button>
        </div>

        {preview && (
          <div
            className={`mt-3 p-3 border flex items-start gap-3 ${
              preview.ok ? 'bg-success/5 border-success/30' : 'bg-danger/5 border-danger/30'
            }`}
          >
            {preview.ok ? (
              <CheckCircle className="w-5 h-5 text-success mt-0.5 shrink-0" />
            ) : (
              <XCircle className="w-5 h-5 text-danger mt-0.5 shrink-0" />
            )}
            <div className="min-w-0 flex-1">
              {preview.ok ? (
                <>
                  <p className="font-medium text-ink">{preview.title}</p>
                  <p className="text-sm text-ink-soft mt-0.5">
                    {preview.entry_count} entrées · dernière : « {preview.sample[0]} »
                  </p>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {preview.tags.slice(0, 10).map((t) => (
                      <Tag key={t} label={t} />
                    ))}
                  </div>
                  <button
                    onClick={handleAdd}
                    disabled={adding}
                    className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 bg-accent text-paper hover:opacity-90 disabled:opacity-40 transition-opacity text-sm font-medium"
                  >
                    <Plus className="w-4 h-4" />
                    {adding ? 'Ajout…' : 'Ajouter à ma bibliothèque'}
                  </button>
                </>
              ) : (
                <p className="text-sm text-danger">{preview.status}</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Liste */}
      <div className="mt-5 pt-5 border-t border-ink-line">
        {loading ? (
          <div className="flex justify-center py-6">
            <Loader size="lg" />
          </div>
        ) : feeds.length === 0 ? (
          <div className="text-center py-8">
            <Rss className="w-10 h-10 mx-auto mb-3 text-ink-faint" />
            <p className="text-ink-soft">Aucun flux pour l'instant</p>
            <p className="text-sm text-ink-faint mt-1">
              Sans flux, la veille s'appuie sur le moteur de recherche et un petit catalogue par défaut.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-ink-line">
            {feeds.map((feed) => {
              const healthy = feed.last_status === 'ok' && feed.last_entry_count > 0;
              return (
                <li key={feed.id} className={`py-3 ${feed.enabled ? '' : 'opacity-50'}`}>
                  <div className="flex items-start gap-3">
                    {healthy ? (
                      <CheckCircle className="w-4 h-4 text-success mt-1 shrink-0" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-warning mt-1 shrink-0" />
                    )}

                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-ink truncate">{feed.title || feed.url}</p>
                      <a
                        href={feed.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs font-mono text-ink-faint hover:text-accent break-all"
                      >
                        {feed.url}
                      </a>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {feed.tags.slice(0, 8).map((t) => (
                          <Tag key={t} label={t} />
                        ))}
                      </div>
                      <p className="text-xs text-ink-faint mt-2">
                        {healthy
                          ? `${feed.last_entry_count} entrées · vérifié le ${formatDate(feed.last_checked)}`
                          : `${feed.last_status ?? 'jamais vérifié'} · ${formatDate(feed.last_checked)}`}
                      </p>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => handleCheck(feed)}
                        disabled={busyId === feed.id}
                        title="Re-vérifier ce flux"
                        className="p-2 text-ink-soft hover:text-accent disabled:opacity-40 transition-colors"
                      >
                        <RefreshCw className={`w-4 h-4 ${busyId === feed.id ? 'animate-spin' : ''}`} />
                      </button>
                      <button
                        onClick={() => handleToggle(feed)}
                        disabled={busyId === feed.id}
                        title={feed.enabled ? 'Désactiver' : 'Activer'}
                        className="px-2 py-1 text-xs border border-ink-line text-ink-soft hover:border-accent hover:text-accent disabled:opacity-40 transition-colors"
                      >
                        {feed.enabled ? 'Actif' : 'Inactif'}
                      </button>
                      <button
                        onClick={() => setToDelete(feed)}
                        title="Retirer de la bibliothèque"
                        className="p-2 text-ink-soft hover:text-danger transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <ConfirmDialog
        open={!!toDelete}
        title="Retirer ce flux ?"
        message={`« ${toDelete?.title ?? ''} » ne sera plus interrogé par la veille.`}
        confirmLabel="Retirer"
        onCancel={() => setToDelete(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
};

export default FeedLibrary;
