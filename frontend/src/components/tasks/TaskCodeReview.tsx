/**
 * Le code d'une tâche à l'écran de validation : l'aperçu qui tourne, puis
 * chaque fichier dans son onglet.
 *
 * Avant, la validation ne montrait que le texte brut d'une page de 30 000
 * caractères : impossible de juger un visuel génératif sans le copier
 * ailleurs. Ici la page (HTML + CSS + JS de la tâche, et ceux des autres
 * tâches du projet qu'elle utilise) est assemblée dans un cadre isolé.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { Eye, Maximize2, Minimize2, RefreshCw } from 'lucide-react';
import type { Task } from '../../types/task.types';
import api from '../../services/api';
import { assemblerApercu, MARQUE_SONDE, preparerApercu, type MessageConsole } from '../../utils/apercu';
import { CodeViewer } from './CodeViewer';

interface FichierTache {
  path: string;
  content: string;
  language: string | null;
  task_id: number;
  task_title: string;
  mine: boolean;
}

interface ApercuTache {
  entry: string | null;
  files: FichierTache[];
}

/** Langage Prism déduit du nom de fichier (défaut : texte brut). */
const LANGUAGE_BY_EXTENSION: Record<string, string> = {
  html: 'markup', htm: 'markup', svg: 'markup', vue: 'markup',
  css: 'css', scss: 'scss', sass: 'sass',
  js: 'javascript', mjs: 'javascript', cjs: 'javascript', jsx: 'jsx',
  ts: 'typescript', tsx: 'tsx',
  py: 'python', json: 'json', yml: 'yaml', yaml: 'yaml', md: 'markdown',
  sh: 'bash', sql: 'sql', toml: 'toml', rs: 'rust', go: 'go', php: 'php', rb: 'ruby',
};

const languageFromPath = (path?: string): string => {
  const extension = path?.split('.').pop()?.toLowerCase();
  return (extension && LANGUAGE_BY_EXTENSION[extension]) || 'python';
};

const ROLE: Record<string, string> = { html: 'HTML', htm: 'HTML', css: 'CSS', js: 'JS' };
const roleDe = (chemin: string) => ROLE[chemin.split('.').pop()?.toLowerCase() ?? ''];

export const TaskCodeReview = ({ task }: { task: Task }) => {
  const [data, setData] = useState<ApercuTache | null>(null);
  const [onglet, setOnglet] = useState('apercu');
  const [pleinEcran, setPleinEcran] = useState(false);
  const [rechargement, setRechargement] = useState(0);
  const [consoleApercu, setConsoleApercu] = useState<MessageConsole[]>([]);
  const cadre = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    let actif = true;
    api.get<ApercuTache>(`/tasks/${task.id}/apercu`, { silentError: true })
      .then((r) => {
        if (!actif) return;
        setData(r.data);
        setOnglet('apercu');
      })
      .catch(() => actif && setData({ entry: null, files: [] }));
    return () => { actif = false; };
  }, [task.id, task.generated_code]);

  // Page de la tâche, du projet, ou page minimale si le projet n'en a pas.
  // La page du projet peut être celle d'une autre tâche, cassée : on peut
  // alors voir le code de cette tâche sur une page minimale
  const [pageMinimale, setPageMinimale] = useState(false);
  const apercu = useMemo(() => {
    if (!data) return null;
    if (pageMinimale) {
      return preparerApercu(null, data.files.filter((f) => !/\.html?$/i.test(f.path)));
    }
    return preparerApercu(data.entry, data.files);
  }, [data, pageMinimale]);
  const srcDoc = useMemo(() => (apercu ? assemblerApercu(apercu.entry, apercu.files) : ''), [apercu]);

  useEffect(() => { setConsoleApercu([]); }, [srcDoc, rechargement]);

  useEffect(() => {
    const recevoir = (e: MessageEvent) => {
      if (e.source !== cadre.current?.contentWindow || e.data?.source !== MARQUE_SONDE) return;
      const { niveau, message } = e.data as MessageConsole;
      setConsoleApercu((liste) => [...liste, { niveau, message: String(message).slice(0, 400) }].slice(-50));
    };
    window.addEventListener('message', recevoir);
    return () => window.removeEventListener('message', recevoir);
  }, []);

  // Échap ferme le plein écran
  useEffect(() => {
    if (!pleinEcran) return;
    const touche = (e: KeyboardEvent) => e.key === 'Escape' && setPleinEcran(false);
    window.addEventListener('keydown', touche);
    return () => window.removeEventListener('keydown', touche);
  }, [pleinEcran]);

  if (data === null) {
    return <p className="text-sm text-ink-faint py-6">Préparation de l'aperçu…</p>;
  }

  const miens = data.files.filter((f) => f.mine);
  // L'API ne sait rien en tirer (ancienne tâche, sortie illisible) : le texte brut
  if (miens.length === 0) {
    return <CodeViewer code={task.generated_code || ''} language={languageFromPath(task.metadata?.artifact_path)} />;
  }

  const fichier = miens.find((f) => f.path === onglet);
  const pageDuProjet = apercu && !apercu.secours && !miens.some((f) => f.path === apercu.entry);
  const choixDePage = pageMinimale || pageDuProjet;
  const erreurs = consoleApercu.filter((m) => m.niveau === 'error');

  const ongletClasse = (actif: boolean) =>
    `px-3 py-1.5 text-sm border-b-2 transition-colors ${actif ? 'border-accent text-ink' : 'border-transparent text-ink-soft hover:text-ink'}`;

  const tronques: string[] = task.metadata?.fichiers_tronques ?? [];

  return (
    <div>
      {tronques.length > 0 && (
        <p className="mb-3 px-3 py-2 border border-warning/40 bg-warning/5 text-sm text-warning">
          {tronques.join(', ')} : coupé par la limite de longueur du modèle, donc incomplet. Demande un
          ajustement de ce fichier seulement pour le terminer.
        </p>
      )}
      <div className="flex flex-wrap items-end gap-1 border-b border-ink-line mb-3">
        {apercu && (
          <button onClick={() => setOnglet('apercu')} className={`${ongletClasse(onglet === 'apercu')} inline-flex items-center gap-1.5`}>
            <Eye className="w-3.5 h-3.5" /> Aperçu
          </button>
        )}
        {/* Une page en trois fichiers : HTML, CSS, JS (le nom complet en survol) */}
        {miens.map((f) => (
          <button key={f.path} title={f.path} onClick={() => setOnglet(f.path)} className={ongletClasse(onglet === f.path)}>
            <span className="font-mono text-xs">{miens.length > 1 && roleDe(f.path) ? roleDe(f.path) : f.path}</span>
          </button>
        ))}
      </div>

      {onglet === 'apercu' && apercu ? (
        <div className={pleinEcran ? 'fixed inset-0 z-50 bg-paper p-4 flex flex-col' : 'border border-ink-line'}>
          <div className="flex items-center justify-between gap-2 px-3 py-1.5 border-b border-ink-line bg-paper-warm text-xs text-ink-faint">
            <span className="truncate">
              {apercu.secours
                ? 'Le projet n\'a pas de page HTML : page minimale qui charge ses styles et scripts'
                : pageDuProjet
                  ? `${apercu.entry}, la page du projet, avec le code de cette tâche`
                  : `${apercu.entry} — aperçu isolé : le code n'a accès ni à l'orchestrateur ni à tes données`}
            </span>
            <span className="flex shrink-0 items-center gap-3">
              {choixDePage && (
                <button onClick={() => setPageMinimale((v) => !v)} className="hover:text-accent">
                  {pageMinimale ? 'Page du projet' : 'Page minimale'}
                </button>
              )}
              <button onClick={() => setRechargement((n) => n + 1)} className="inline-flex items-center gap-1 hover:text-accent">
                <RefreshCw className="w-3.5 h-3.5" /> Relancer
              </button>
              <button onClick={() => setPleinEcran((v) => !v)} className="inline-flex items-center gap-1 hover:text-accent">
                {pleinEcran ? <><Minimize2 className="w-3.5 h-3.5" /> Réduire</> : <><Maximize2 className="w-3.5 h-3.5" /> Plein écran</>}
              </button>
            </span>
          </div>
          {/* allow-scripts sans allow-same-origin : le code généré reste dans sa boîte */}
          <iframe
            key={rechargement}
            ref={cadre}
            title={`Aperçu de ${apercu.entry}`}
            sandbox="allow-scripts allow-forms allow-modals allow-downloads"
            srcDoc={srcDoc}
            className={pleinEcran ? 'w-full flex-1 bg-white border border-ink-line' : 'w-full h-[60vh] bg-white'}
          />
          {erreurs.length > 0 && (
            <div className="px-3 py-2 border-t border-ink-line bg-danger/5 text-xs text-danger space-y-0.5">
              <p className="font-medium">{erreurs.length} erreur(s) JavaScript : à signaler dans « Demander un ajustement »</p>
              {erreurs.slice(0, 5).map((m, i) => <p key={i} className="font-mono break-words">{m.message}</p>)}
            </div>
          )}
        </div>
      ) : fichier ? (
        <>
          <p className="mb-2 font-mono text-xs text-ink-faint">{fichier.path}</p>
          <CodeViewer code={fichier.content} language={languageFromPath(fichier.path)} />
        </>
      ) : null}

      {!apercu && (
        <p className="mt-2 text-xs text-ink-faint">Pas d'aperçu : ce code n'est pas une page web.</p>
      )}
    </div>
  );
};
