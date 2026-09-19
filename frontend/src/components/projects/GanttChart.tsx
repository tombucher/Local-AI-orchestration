/**
 * Frise Gantt SVG du chemin critique — style « journal d'atelier », interactive.
 * - Une ligne par tâche, barres early_start → early_finish
 * - Chemin critique en vermillon, marge (slack) hachurée, dépendances en traits
 * - Poignée à droite d'une barre : étirer pour changer l'estimation (onResize)
 * - Tirer une barre sur une autre ligne : créer une dépendance (onLink —
 *   la tâche cible dépendra de la tâche tirée)
 * Unités CPM = secondes estimées ; libellés en dates projetées.
 */

import { useMemo, useRef, useState } from 'react';
import { CriticalPathData } from '../../types/critical-path.types';

interface GanttChartProps {
  data: CriticalPathData;
  /** Nouvelle estimation (secondes) après étirement d'une barre */
  onResize?: (taskId: number, seconds: number) => void;
  /** `taskId` dépendra désormais de `dependsOnId` */
  onLink?: (taskId: number, dependsOnId: number) => void;
}

type Drag =
  | { kind: 'resize'; taskId: number; row: number; startX: number; origUnits: number; deltaUnits: number }
  | { kind: 'link'; fromId: number; fromRow: number; x: number; y: number; overRow: number | null };

const ROW_H = 34;
const BAR_H = 16;
const LABEL_W = 200;
const CHART_W = 560;
const TOP_PAD = 28;
const HANDLE_W = 8;
const MIN_UNITS = 30 * 60; // 30 min minimum

const formatDay = (iso: string) =>
  new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });

const formatHours = (units: number) => `${Math.max(1, Math.round(units / 3600))} h`;

export const GanttChart = ({ data, onResize, onLink }: GanttChartProps) => {
  const tasks = data.ordered_tasks;
  const svgRef = useRef<SVGSVGElement>(null);
  const [drag, setDrag] = useState<Drag | null>(null);
  const interactive = Boolean(onResize || onLink);

  const scale = useMemo(() => CHART_W / Math.max(data.total_duration, 1), [data.total_duration]);

  if (tasks.length === 0) {
    return (
      <p className="text-sm text-ink-faint py-4">
        Aucune tâche à afficher — ajoutez des tâches avec des estimations de durée.
      </p>
    );
  }

  const height = TOP_PAD + tasks.length * ROW_H + 8;
  const rowIndex = new Map(tasks.map((t, i) => [t.task_id, i]));
  const rowY = (row: number) => TOP_PAD + row * ROW_H + ROW_H / 2;

  /** Coordonnées du pointeur dans le repère du SVG (viewBox) */
  const toSvg = (e: React.PointerEvent): { x: number; y: number } => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return { x: 0, y: 0 };
    const p = pt.matrixTransform(ctm.inverse());
    return { x: p.x, y: p.y };
  };

  const rowFromY = (y: number): number | null => {
    const row = Math.floor((y - TOP_PAD) / ROW_H);
    return row >= 0 && row < tasks.length ? row : null;
  };

  const startResize = (e: React.PointerEvent, taskId: number, row: number, origUnits: number) => {
    if (!onResize) return;
    e.stopPropagation();
    (e.currentTarget as Element).setPointerCapture?.(e.pointerId);
    setDrag({ kind: 'resize', taskId, row, startX: toSvg(e).x, origUnits, deltaUnits: 0 });
  };

  const startLink = (e: React.PointerEvent, fromId: number, fromRow: number) => {
    if (!onLink) return;
    e.stopPropagation();
    const { x, y } = toSvg(e);
    setDrag({ kind: 'link', fromId, fromRow, x, y, overRow: null });
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (!drag) return;
    const { x, y } = toSvg(e);
    if (drag.kind === 'resize') {
      setDrag({ ...drag, deltaUnits: (x - drag.startX) / scale });
    } else {
      setDrag({ ...drag, x, y, overRow: rowFromY(y) });
    }
  };

  const onPointerUp = () => {
    if (!drag) return;
    if (drag.kind === 'resize' && onResize) {
      const next = Math.max(MIN_UNITS, Math.round(drag.origUnits + drag.deltaUnits));
      if (Math.abs(next - drag.origUnits) >= 60) onResize(drag.taskId, next);
    } else if (drag.kind === 'link' && onLink && drag.overRow !== null && drag.overRow !== drag.fromRow) {
      onLink(tasks[drag.overRow].task_id, drag.fromId);
    }
    setDrag(null);
  };

  // Graduations : 5 repères temporels projetés
  const t0 = tasks[0] ? new Date(tasks[0].projected_start).getTime() : Date.now();
  const tEnd = data.projected_end_date ? new Date(data.projected_end_date).getTime() : t0;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => ({
    x: LABEL_W + f * CHART_W,
    label: formatDay(new Date(t0 + f * (tEnd - t0)).toISOString()),
  }));

  return (
    <div className="overflow-x-auto">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${LABEL_W + CHART_W + 16} ${height}`}
        className={`w-full min-w-[640px] select-none ${drag ? (drag.kind === 'resize' ? 'cursor-ew-resize' : 'cursor-grabbing') : ''}`}
        role="img"
        aria-label="Frise du chemin critique"
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={() => drag && setDrag(null)}
      >
        <defs>
          <pattern id="slack-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="6" height="6" fill="transparent" />
            <line x1="0" y1="0" x2="0" y2="6" stroke="#78716C" strokeWidth="1.5" opacity="0.45" />
          </pattern>
        </defs>

        {/* Graduations */}
        {ticks.map((tick, i) => (
          <g key={i}>
            <line x1={tick.x} y1={TOP_PAD - 6} x2={tick.x} y2={height - 8} stroke="#E0D9CD" strokeWidth="1" />
            <text x={tick.x} y={TOP_PAD - 12} textAnchor="middle" fontSize="9" fill="#78716C" fontFamily="JetBrains Mono, monospace">
              {tick.label}
            </text>
          </g>
        ))}

        {/* Ligne cible pendant un glisser de dépendance */}
        {drag?.kind === 'link' && drag.overRow !== null && drag.overRow !== drag.fromRow && (
          <rect x={LABEL_W} y={TOP_PAD + drag.overRow * ROW_H} width={CHART_W} height={ROW_H} fill="#F5D547" opacity="0.25" />
        )}

        {/* Dépendances existantes */}
        {tasks.map((task) =>
          task.depends_on.map((depId) => {
            const fromRow = rowIndex.get(depId);
            const toRow = rowIndex.get(task.task_id);
            if (fromRow === undefined || toRow === undefined) return null;
            const fromTask = tasks[fromRow];
            const x1 = LABEL_W + fromTask.early_finish * scale;
            const x2 = LABEL_W + task.early_start * scale;
            return (
              <path
                key={`${depId}-${task.task_id}`}
                d={`M ${x1} ${rowY(fromRow)} L ${x1 + 6} ${rowY(fromRow)} L ${x1 + 6} ${rowY(toRow)} L ${x2} ${rowY(toRow)}`}
                fill="none" stroke="#78716C" strokeWidth="1" opacity="0.5"
              />
            );
          })
        )}

        {/* Lignes de tâches */}
        {tasks.map((task, i) => {
          const y = TOP_PAD + i * ROW_H;
          const barY = y + (ROW_H - BAR_H) / 2;
          const units = task.early_finish - task.early_start;
          const previewUnits = drag?.kind === 'resize' && drag.taskId === task.task_id
            ? Math.max(MIN_UNITS, units + drag.deltaUnits) : units;
          const barX = LABEL_W + task.early_start * scale;
          const barW = Math.max(previewUnits * scale, 3);
          const slackW = task.slack * scale;
          const isDone = task.status === 'completed';
          const isSource = drag?.kind === 'link' && drag.fromId === task.task_id;

          return (
            <g key={task.task_id}>
              <text x={LABEL_W - 10} y={y + ROW_H / 2 + 3} textAnchor="end" fontSize="11"
                fill={task.is_critical ? '#1C1917' : '#44403C'} fontWeight={task.is_critical ? '600' : '400'}>
                {task.title.length > 28 ? task.title.slice(0, 27) + '…' : task.title}
              </text>

              {/* Barre principale — tirer sur une autre ligne = dépendance */}
              <rect
                x={barX} y={barY} width={barW} height={BAR_H}
                fill={isDone ? '#4D7C5F' : task.is_critical ? '#E2492F' : '#1C1917'}
                opacity={isSource ? 0.5 : isDone ? 0.55 : task.is_critical ? 1 : 0.75}
                className={onLink ? 'cursor-grab' : ''}
                onPointerDown={(e) => startLink(e, task.task_id, i)}
              >
                <title>
                  {task.title} — {formatDay(task.projected_start)} → {formatDay(task.projected_end)} · {formatHours(units)}
                  {task.is_critical ? ' (critique)' : ''}
                  {onLink ? '\nTirer sur une autre tâche pour en faire une dépendance' : ''}
                </title>
              </rect>

              {/* Poignée d'étirement (estimation) */}
              {onResize && (
                <rect
                  x={barX + barW - HANDLE_W / 2} y={barY - 2} width={HANDLE_W} height={BAR_H + 4}
                  fill="#FAF7F2" stroke="#1C1917" strokeWidth="1"
                  className="cursor-ew-resize"
                  onPointerDown={(e) => startResize(e, task.task_id, i, units)}
                >
                  <title>Étirer pour modifier l'estimation ({formatHours(units)})</title>
                </rect>
              )}

              {/* Aperçu de la nouvelle durée pendant l'étirement */}
              {drag?.kind === 'resize' && drag.taskId === task.task_id && (
                <text x={barX + barW + 8} y={y + ROW_H / 2 + 3} fontSize="10" fill="#E2492F" fontFamily="JetBrains Mono, monospace">
                  {formatHours(previewUnits)}
                </text>
              )}

              {/* Marge hachurée */}
              {slackW > 1 && !(drag?.kind === 'resize' && drag.taskId === task.task_id) && (
                <rect x={barX + barW} y={barY} width={slackW} height={BAR_H} fill="url(#slack-hatch)" stroke="#E0D9CD" strokeWidth="0.5" pointerEvents="none" />
              )}

              {/* Échéance : losange */}
              {task.due_date && tEnd > t0 && (
                <path
                  d={`M ${LABEL_W + ((new Date(task.due_date).getTime() - t0) / (tEnd - t0)) * CHART_W} ${y + ROW_H / 2 - 6} l 5 6 l -5 6 l -5 -6 z`}
                  fill="#F5D547" stroke="#1C1917" strokeWidth="1" pointerEvents="none"
                >
                  <title>Échéance : {formatDay(task.due_date)}</title>
                </path>
              )}
            </g>
          );
        })}

        {/* Trait de liaison pendant le glisser */}
        {drag?.kind === 'link' && (
          <line
            x1={LABEL_W + (tasks[drag.fromRow].early_finish) * scale} y1={rowY(drag.fromRow)}
            x2={drag.x} y2={drag.y}
            stroke="#E2492F" strokeWidth="1.5" strokeDasharray="4 3" pointerEvents="none"
          />
        )}
      </svg>

      {/* Légende */}
      <div className="flex flex-wrap items-center gap-4 mt-2 text-[11px] text-ink-faint">
        <span className="flex items-center gap-1.5"><span className="inline-block w-4 h-2.5 bg-accent" /> Chemin critique</span>
        <span className="flex items-center gap-1.5"><span className="inline-block w-4 h-2.5 bg-ink opacity-75" /> Tâche</span>
        <span className="flex items-center gap-1.5"><span className="inline-block w-4 h-2.5 bg-success opacity-55" /> Terminée</span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-4 h-2.5 border border-ink-line" style={{
            backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 2px, #78716C77 2px, #78716C77 3px)',
          }} /> Marge
        </span>
        {interactive && (
          <span className="italic">Poignée : étirer l'estimation · Tirer une barre sur une autre : créer une dépendance</span>
        )}
        {data.projected_end_date && (
          <span className="ml-auto figures">Fin projetée : <strong className="text-ink-soft">{formatDay(data.projected_end_date)}</strong></span>
        )}
      </div>
    </div>
  );
};

export default GanttChart;
