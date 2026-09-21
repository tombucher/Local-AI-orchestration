/**
 * Vignettes de résultats de veille — style « journal d'atelier ».
 * Favicon du domaine, score en badge, résumé IA en exergue,
 * actions épingler / écarter (statuts SAVED / DISMISSED).
 */

import { useState } from 'react';
import {
  ExternalLink, Star, ChevronDown, ChevronUp, Globe, Tag, Calendar,
  Bookmark, X, RotateCcw, ImagePlus,
} from 'lucide-react';
import toast from 'react-hot-toast';
import type { VeilleResult } from '../../types/task.types';
import { VeilleResultType, VeilleResultStatus } from '../../types/task.types';
import { tasksService } from '../../services/tasks';
import { api } from '../../services/api';

interface VeilleResultsViewerProps {
  results: VeilleResult[];
  total: number;
  /** Permet d'envoyer une illustration au moodboard du projet */
  projectId?: number;
}

/** Labels par type de résultat (filets colorés, pas de pastilles) */
const RESULT_TYPE_CONFIG: Record<VeilleResultType, { label: string; emoji: string }> = {
  [VeilleResultType.FUNDING_OPPORTUNITY]: { label: 'Financement', emoji: '💰' },
  [VeilleResultType.TECH_ARTICLE]: { label: 'Article tech', emoji: '📄' },
  [VeilleResultType.TECH_TOOL]: { label: 'Outil', emoji: '🛠' },
  [VeilleResultType.EVENT]: { label: 'Événement', emoji: '🎪' },
  [VeilleResultType.COLLABORATION]: { label: 'Collaboration', emoji: '🤝' },
  [VeilleResultType.ACADEMIC_PAPER]: { label: 'Publication', emoji: '📚' },
  [VeilleResultType.NEWS_ARTICLE]: { label: 'Actualité', emoji: '📰' },
  [VeilleResultType.ARTIST_WORK]: { label: 'Œuvre', emoji: '🎨' },
  [VeilleResultType.CALL_FOR_PROPOSALS]: { label: 'Appel à projets', emoji: '📢' },
};

/** Favicon du domaine via DuckDuckGo (gratuit, pas de clé) */
const Favicon = ({ url }: { url: string }) => {
  const [failed, setFailed] = useState(false);
  let host = '';
  try {
    host = new URL(url).hostname;
  } catch {
    return <Globe className="w-4 h-4 text-ink-faint" />;
  }
  if (failed) return <Globe className="w-4 h-4 text-ink-faint" />;
  return (
    <img
      src={`https://icons.duckduckgo.com/ip3/${host}.ico`}
      alt=""
      className="w-4 h-4"
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
};

const scoreColor = (score: number) =>
  score >= 80 ? 'text-success border-success' :
  score >= 60 ? 'text-warning border-warning' :
  'text-ink-faint border-ink-line';

/** Carte pour un résultat de veille */
const VeilleResultCard = ({ result: initial, projectId }: { result: VeilleResult; projectId?: number }) => {
  const [result, setResult] = useState(initial);
  const [expanded, setExpanded] = useState(false);
  const [pending, setPending] = useState(false);
  const [versMoodboard, setVersMoodboard] = useState(false);
  const typeConfig = RESULT_TYPE_CONFIG[result.result_type] || { label: result.result_type, emoji: '📋' };

  const isSaved = result.status === VeilleResultStatus.SAVED;
  const isDismissed = result.status === VeilleResultStatus.DISMISSED;

  const setStatus = async (status: VeilleResultStatus) => {
    setPending(true);
    try {
      const updated = await tasksService.updateVeilleResult(result.id, { status });
      setResult(updated);
      if (status === VeilleResultStatus.SAVED) toast.success('Épinglé');
      if (status === VeilleResultStatus.DISMISSED) toast('Écarté', { icon: '🗞' });
    } catch {
      // Erreur déjà toastée par l'intercepteur API
    } finally {
      setPending(false);
    }
  };

  /** Envoie l'illustration de l'article vers le moodboard du projet */
  const envoyerAuMoodboard = async () => {
    if (!projectId || !result.image_url) return;
    setVersMoodboard(true);
    try {
      await api.post(`/projects/${projectId}/visual-references`, {
        url: result.image_url,
        title: result.title,
        source_url: result.url || undefined,
      });
      toast.success('Ajoutée au moodboard');
    } catch {
      // Motif déjà affiché par l'intercepteur API
    } finally {
      setVersMoodboard(false);
    }
  };

  return (
    <div
      className={`bg-paper-card border border-ink-line p-4 transition-all
        ${isDismissed ? 'opacity-45' : 'hover:shadow-card'}
        ${isSaved ? 'border-l-2 border-l-highlight' : ''}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-2">
        {/* Illustration de l'article, fournie par le moteur ou le flux */}
        {result.image_url && (
          <img
            src={result.image_url}
            alt=""
            loading="lazy"
            referrerPolicy="no-referrer"
            className="w-20 h-20 object-cover border border-ink-line shrink-0"
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            {result.url && <Favicon url={result.url} />}
            <span className="kicker">{typeConfig.emoji} {typeConfig.label}</span>
            <span className={`border px-1.5 py-0.5 text-[10px] font-mono font-semibold figures ${scoreColor(result.relevance_score)}`}>
              {Math.round(result.relevance_score)}
            </span>
          </div>
          <h3 className={`font-display text-base text-ink leading-snug ${isDismissed ? 'line-through' : ''}`}>
            {result.url ? (
              <a href={result.url} target="_blank" rel="noopener noreferrer" className="hover:text-accent transition-colors">
                {result.title}
              </a>
            ) : result.title}
          </h3>
        </div>

        {/* Actions épingler / écarter */}
        <div className="flex items-center gap-1 shrink-0">
          {!isDismissed && projectId && result.image_url && (
            <button
              onClick={envoyerAuMoodboard}
              disabled={versMoodboard}
              title="Envoyer l'image au moodboard"
              className="p-1.5 text-ink-faint hover:text-accent hover:bg-paper-warm transition-colors disabled:opacity-40"
            >
              <ImagePlus className="w-4 h-4" />
            </button>
          )}
          {!isDismissed && (
            <button
              onClick={() => setStatus(isSaved ? VeilleResultStatus.READ : VeilleResultStatus.SAVED)}
              disabled={pending}
              title={isSaved ? 'Désépingler' : 'Épingler'}
              className={`p-1.5 transition-colors ${isSaved ? 'text-ink bg-highlight/50' : 'text-ink-faint hover:text-ink hover:bg-paper-warm'}`}
            >
              <Bookmark className={`w-4 h-4 ${isSaved ? 'fill-current' : ''}`} />
            </button>
          )}
          {isDismissed ? (
            <button
              onClick={() => setStatus(VeilleResultStatus.READ)}
              disabled={pending}
              title="Restaurer"
              className="p-1.5 text-ink-faint hover:text-ink hover:bg-paper-warm transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={() => setStatus(VeilleResultStatus.DISMISSED)}
              disabled={pending}
              title="Écarter"
              className="p-1.5 text-ink-faint hover:text-danger hover:bg-paper-warm transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Résumé IA en exergue, sinon description */}
      {(result.ai_summary || result.description) && !isDismissed && (
        <p className="text-sm text-ink-soft mb-2 line-clamp-2 italic">
          {result.ai_summary || result.description}
        </p>
      )}

      {/* Métadonnées inline */}
      <div className="flex flex-wrap gap-3 text-[11px] text-ink-faint mb-2 figures">
        {result.source_platform && (
          <span className="flex items-center gap-1">
            <Globe className="w-3 h-3" />
            {result.source_platform}
          </span>
        )}
        {result.found_at && (
          <span className="flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            {new Date(result.found_at).toLocaleDateString('fr-FR')}
          </span>
        )}
        {result.key_points && result.key_points.length > 0 && (
          <span className="flex items-center gap-1">
            <Tag className="w-3 h-3" />
            {result.key_points.length} points clés
          </span>
        )}
      </div>

      {/* Bouton expand/collapse */}
      {!isDismissed && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-xs text-accent hover:text-accent-deep transition-colors"
        >
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? 'Moins de détails' : 'Plus de détails'}
        </button>
      )}

      {/* Section expandable */}
      {expanded && !isDismissed && (
        <div className="mt-3 pt-3 border-t border-ink-line space-y-3">
          {result.relevance_reason && (
            <div>
              <p className="kicker mb-1">Pourquoi c'est pertinent</p>
              <p className="text-sm text-ink-soft">{result.relevance_reason}</p>
            </div>
          )}

          {result.key_points && result.key_points.length > 0 && (
            <div>
              <p className="kicker mb-1">Points clés</p>
              <ul className="list-disc list-inside text-sm text-ink-soft space-y-1">
                {result.key_points.map((point, idx) => (
                  <li key={idx}>{point}</li>
                ))}
              </ul>
            </div>
          )}

          {result.metadata && Object.keys(result.metadata).length > 0 && (
            <div>
              <p className="kicker mb-1">Métadonnées</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(result.metadata).map(([key, value]) => (
                  <span key={key} className="inline-flex items-center px-2 py-0.5 bg-paper-warm text-xs text-ink-soft">
                    <strong className="mr-1">{key} :</strong> {String(value)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {result.url && (
            <a
              href={result.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-sm text-accent hover:text-accent-deep hover:underline"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Voir la source complète
            </a>
          )}
        </div>
      )}
    </div>
  );
};

export const VeilleResultsViewer = ({ results, total, projectId }: VeilleResultsViewerProps) => {
  if (!results || results.length === 0) {
    return (
      <div className="bg-paper border border-dashed border-ink-line p-6 text-center">
        <p className="text-ink-faint">Aucun résultat de veille trouvé pour cette tâche.</p>
      </div>
    );
  }

  const avgScore = Math.round(results.reduce((sum, r) => sum + r.relevance_score, 0) / results.length);
  const typeCount = new Set(results.map(r => r.result_type)).size;

  return (
    <div className="space-y-4">
      {/* Manchette */}
      <div className="flex items-center gap-4 text-sm text-ink-soft figures pb-2 rule">
        <span className="flex items-center gap-1">
          <Star className="w-4 h-4 text-highlight fill-current" />
          <strong>{total}</strong> résultat{total > 1 ? 's' : ''}
        </span>
        <span>Score moyen : <strong>{avgScore}</strong></span>
        <span>{typeCount} type{typeCount > 1 ? 's' : ''}</span>
      </div>

      {/* Vignettes */}
      <div className="space-y-3">
        {results.map((result) => (
          <VeilleResultCard key={result.id} result={result} projectId={projectId} />
        ))}
      </div>
    </div>
  );
};
