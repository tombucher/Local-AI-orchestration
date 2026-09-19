/**
 * RadarViewer — Composant d'affichage du Rapport Radar de veille
 *
 * Affiche les pépites (liens commentés), stats, et section d'affinage interactif.
 */

import { useState } from 'react';
import toast from 'react-hot-toast';
import { tasksService } from '../../services/tasks';
import type { RadarReport, VeilleRefinePayload } from '../../types/task.types';

interface RadarViewerProps {
  report: RadarReport;
  taskId: number;
  onRefine?: (refinement: VeilleRefinePayload) => Promise<void>;
}

// --- Composants internes ---

const ScoreBar = ({ score }: { score: number }) => {
  const pct = Math.min(100, Math.max(0, score));
  const color =
    pct >= 80 ? 'bg-success' :
    pct >= 60 ? 'bg-warning' :
    pct >= 40 ? 'bg-warning' : 'bg-danger';

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-paper-warm rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-medium text-ink-soft w-10 text-right">{pct.toFixed(0)}%</span>
    </div>
  );
};

const PepiteCard = ({ pepite }: { pepite: RadarReport['pepites'][0] }) => (
  <div className="bg-paper-card border border-ink-line rounded-none p-4 hover:shadow-md transition-shadow">
    <div className="flex justify-between items-start gap-3 mb-2">
      <h4 className="font-medium text-ink text-sm leading-tight flex-1">
        {pepite.name}
      </h4>
      <span className="text-xs font-bold text-accent whitespace-nowrap">
        {pepite.relevance_score.toFixed(0)}%
      </span>
    </div>
    <p className="text-sm text-ink-soft mb-3 line-clamp-2">{pepite.synthesis}</p>
    <div className="flex items-center justify-between">
      <ScoreBar score={pepite.relevance_score} />
      {pepite.link && (
        <a
          href={pepite.link}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-3 text-xs text-accent hover:text-accent-deep flex items-center gap-1 whitespace-nowrap"
        >
          🔗 Voir
        </a>
      )}
    </div>
  </div>
);

const KeywordChip = ({
  label,
  variant,
  onAction,
  actionLabel,
}: {
  label: string;
  variant: 'current' | 'add' | 'remove' | 'exclude';
  onAction?: () => void;
  actionLabel?: string;
}) => {
  const colors = {
    current: 'bg-paper-warm text-ink-soft',
    add: 'bg-success/5 text-success border border-success/30',
    remove: 'bg-danger/5 text-danger border border-danger/30',
    exclude: 'bg-warning/5 text-warning border border-warning/30',
  };

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${colors[variant]}`}>
      {label}
      {onAction && (
        <button
          onClick={onAction}
          className="ml-1 hover:opacity-70 transition-opacity"
          title={actionLabel}
        >
          {variant === 'add' ? '＋' : variant === 'remove' ? '−' : variant === 'exclude' ? '🚫' : ''}
        </button>
      )}
    </span>
  );
};

// --- Composant principal ---

export const RadarViewer = ({ report, taskId, onRefine }: RadarViewerProps) => {
  const [pendingAdds, setPendingAdds] = useState<string[]>([]);
  const [pendingExcludes, setPendingExcludes] = useState<string[]>([]);
  const [pendingRemoves, setPendingRemoves] = useState<string[]>([]);
  const [userNotes, setUserNotes] = useState('');
  const [isRefining, setIsRefining] = useState(false);
  const [showAffinage, setShowAffinage] = useState(false);

  const { pepites, stats, affinage } = report;

  const handleAddKeyword = (kw: string) => {
    if (!pendingAdds.includes(kw)) setPendingAdds([...pendingAdds, kw]);
  };

  const handleExcludeKeyword = (kw: string) => {
    if (!pendingExcludes.includes(kw)) setPendingExcludes([...pendingExcludes, kw]);
  };

  const handleRemoveKeyword = (kw: string) => {
    if (!pendingRemoves.includes(kw)) setPendingRemoves([...pendingRemoves, kw]);
  };

  const handleApplyRefinement = async () => {
    if (!onRefine) return;
    setIsRefining(true);
    try {
      await onRefine({
        add_keywords: pendingAdds,
        remove_keywords: pendingRemoves,
        add_excluded: pendingExcludes,
        remove_excluded: [],
        user_notes: userNotes || undefined,
      });
      // Reset
      setPendingAdds([]);
      setPendingExcludes([]);
      setPendingRemoves([]);
      setUserNotes('');
    } finally {
      setIsRefining(false);
    }
  };

  const hasChanges = pendingAdds.length > 0 || pendingExcludes.length > 0 || pendingRemoves.length > 0 || userNotes.trim().length > 0;

  return (
    <div className="space-y-6">
      {/* Stats bar */}
      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-none p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-ink">🔍 Rapport Radar</h3>
          <span className="text-xs text-ink-faint">{stats.scan_date}</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="text-center">
            <div className="text-2xl font-bold text-accent">{stats.total_scanned}</div>
            <div className="text-xs text-ink-faint">Scannés</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-success">{stats.total_relevant}</div>
            <div className="text-xs text-ink-faint">Pertinents</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-accent">{stats.avg_score.toFixed(0)}%</div>
            <div className="text-xs text-ink-faint">Score moyen</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-warning">{stats.top_sources.length}</div>
            <div className="text-xs text-ink-faint">Sources</div>
          </div>
        </div>
        {stats.top_sources.length > 0 && (
          <div className="mt-2 flex gap-1 flex-wrap">
            {stats.top_sources.map((src, i) => (
              <span key={i} className="text-xs bg-paper-card/60 px-2 py-0.5 rounded-full text-ink-soft">
                {src}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Pépites */}
      {pepites.length > 0 ? (
        <div>
          <h3 className="text-md font-semibold text-ink mb-3">
            💎 Pépites ({pepites.length})
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {pepites.map((pepite, i) => (
              <PepiteCard key={i} pepite={pepite} />
            ))}
          </div>
        </div>
      ) : (
        <div className="text-center py-8 text-ink-faint">
          <span className="text-4xl mb-2 block">🔍</span>
          <p>Aucune pépite trouvée pour cette occurrence.</p>
          <p className="text-sm mt-1">Essayez d'affiner vos mots-clés ci-dessous.</p>
        </div>
      )}

      {/* Section Affinage */}
      <div className="border border-ink-line rounded-none overflow-hidden">
        <button
          onClick={() => setShowAffinage(!showAffinage)}
          className="w-full flex items-center justify-between px-4 py-3 bg-paper hover:bg-paper-warm transition-colors"
        >
          <span className="font-medium text-ink-soft">🎯 Affinage pour la prochaine occurrence</span>
          <span className="text-ink-faint">{showAffinage ? '▲' : '▼'}</span>
        </button>

        {showAffinage && (
          <div className="p-4 space-y-4">
            {/* Raisonnement IA */}
            {affinage.reasoning && (
              <p className="text-sm text-ink-soft italic bg-accent-wash p-3 rounded-none">
                💡 {affinage.reasoning}
              </p>
            )}

            {/* Keywords actuels */}
            <div>
              <label className="text-xs font-medium text-ink-faint uppercase tracking-wide">Mots-clés actuels</label>
              <div className="flex gap-1 flex-wrap mt-1">
                {affinage.current_keywords.map((kw, i) => (
                  <KeywordChip
                    key={i}
                    label={kw}
                    variant={pendingRemoves.includes(kw) ? 'remove' : 'current'}
                    onAction={() => handleRemoveKeyword(kw)}
                    actionLabel="Retirer ce mot-clé"
                  />
                ))}
              </div>
            </div>

            {/* Suggestions d'ajout */}
            {affinage.suggested_additions.length > 0 && (
              <div>
                <label className="text-xs font-medium text-ink-faint uppercase tracking-wide">Suggestions d'ajout</label>
                <div className="flex gap-1 flex-wrap mt-1">
                  {affinage.suggested_additions.map((kw, i) => (
                    <KeywordChip
                      key={i}
                      label={kw}
                      variant="add"
                      onAction={() => handleAddKeyword(kw)}
                      actionLabel="Ajouter ce mot-clé"
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Suggestions d'exclusion */}
            {affinage.suggested_exclusions.length > 0 && (
              <div>
                <label className="text-xs font-medium text-ink-faint uppercase tracking-wide">Suggestions d'exclusion</label>
                <div className="flex gap-1 flex-wrap mt-1">
                  {affinage.suggested_exclusions.map((kw, i) => (
                    <KeywordChip
                      key={i}
                      label={kw}
                      variant="exclude"
                      onAction={() => handleExcludeKeyword(kw)}
                      actionLabel="Exclure ce mot-clé"
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Modifications en attente */}
            {hasChanges && (
              <div className="bg-info/5 border border-info/30 rounded-none p-3 space-y-2">
                <p className="text-sm font-medium text-info">Modifications en attente :</p>
                {pendingAdds.length > 0 && (
                  <p className="text-xs text-accent">+ Ajouter : {pendingAdds.join(', ')}</p>
                )}
                {pendingRemoves.length > 0 && (
                  <p className="text-xs text-danger">− Retirer : {pendingRemoves.join(', ')}</p>
                )}
                {pendingExcludes.length > 0 && (
                  <p className="text-xs text-warning">🚫 Exclure : {pendingExcludes.join(', ')}</p>
                )}
              </div>
            )}

            {/* Notes utilisateur */}
            <div>
              <label className="text-xs font-medium text-ink-faint uppercase tracking-wide">Notes d'affinage</label>
              <textarea
                value={userNotes}
                onChange={(e) => setUserNotes(e.target.value)}
                className="mt-1 w-full border border-ink-line rounded-none px-3 py-2 text-sm resize-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                rows={2}
                placeholder="Ex: Chercher plus d'artistes européens, ignorer les articles purement académiques..."
              />
            </div>

            {/* Bouton appliquer */}
            {onRefine && (
              <button
                onClick={handleApplyRefinement}
                disabled={!hasChanges || isRefining}
                className={`w-full py-2 px-4 rounded-none font-medium text-sm transition-colors ${
                  hasChanges && !isRefining
                    ? 'bg-accent text-white hover:bg-accent-deep'
                    : 'bg-paper-warm text-ink-faint cursor-not-allowed'
                }`}
              >
                {isRefining ? '⏳ Application...' : '✨ Appliquer l\'affinage'}
              </button>
            )}

            <button
              onClick={async () => {
                setIsRefining(true);
                try {
                  const res = await tasksService.rescanVeille(taskId);
                  toast.success(
                    res.status === 'already_running'
                      ? 'Une veille est déjà en cours pour ce sujet'
                      : 'Veille relancée — résultats dans quelques minutes'
                  );
                } catch {
                  // Erreur déjà toastée par l'intercepteur API
                } finally {
                  setIsRefining(false);
                }
              }}
              disabled={isRefining}
              className="w-full mt-2 py-2 px-4 rounded-none font-medium text-sm border border-accent text-accent hover:bg-accent hover:text-white transition-colors disabled:opacity-40"
            >
              🔄 Relancer la veille maintenant
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
