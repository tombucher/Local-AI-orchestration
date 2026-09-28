/**
 * Ce que le projet a produit, rassemblé au même endroit.
 *
 * Le résultat d'un projet restait éparpillé dans ses tâches : il fallait copier
 * chaque fichier à la main pour voir le site exister. Ici : la liste des fichiers,
 * un aperçu du site en direct, l'archive .zip, et les liens cassés entre fichiers.
 *
 * Le mode Diagnostic montre ce que contient vraiment chaque fichier et la console
 * de l'aperçu : les erreurs JavaScript du site généré restaient invisibles.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, Bug, ClipboardCopy, Download, Eye, EyeOff, FileCode2, FileText, Package, RefreshCw, Rss } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

interface CodeFile {
  path: string;
  task_id: number;
  task_title: string;
  size: number;
  content: string;
  language: string | null; // ce que contient vraiment le fichier (py, html, css…)
}

interface DocumentFile {
  path: string;
  task_id: number;
  task_title: string;
  kind: 'document' | 'veille';
  size: number;
}

interface ProjectFilesResponse {
  entry: string | null;
  code: CodeFile[];
  documents: DocumentFile[];
  coherence: string[];
}

const formatTaille = (o: number) => (o < 1024 ? `${o} o` : `${Math.round(o / 1024)} Ko`);

/** Les alertes du serveur marquent les noms entre `backticks` */
const Alerte = ({ texte }: { texte: string }) => (
  <>
    {texte.split(/`([^`]+)`/).map((morceau, i) =>
      i % 2 ? (
        <code key={i} className="font-mono text-xs bg-paper-warm px-1">{morceau}</code>
      ) : (
        morceau
      ),
    )}
  </>
);

/** Famille d'une extension, pour comparer au contenu détecté par le serveur */
const FAMILLES: Record<string, string> = {
  html: 'html', htm: 'html', css: 'css', scss: 'css', js: 'js', mjs: 'js', jsx: 'js',
  ts: 'js', tsx: 'js', py: 'py', md: 'md', json: 'json', php: 'php', sh: 'sh', svg: 'svg',
};
const familleDe = (chemin: string) => FAMILLES[chemin.split('.').pop()?.toLowerCase() ?? ''] ?? null;

interface MessageConsole {
  niveau: 'error' | 'warn' | 'log';
  message: string;
}

const MARQUE_SONDE = 'apercu-orchestrateur';

/**
 * Sonde placée en tête de l'aperçu : elle relaie console et erreurs du site vers
 * l'orchestrateur (postMessage — le cadre reste isolé, sans accès à la page).
 */
const SONDE = `<script>(function(){
function envoyer(n,a){try{parent.postMessage({source:'${MARQUE_SONDE}',niveau:n,message:Array.prototype.map.call(a,function(x){try{return typeof x==='string'?x:JSON.stringify(x)}catch(e){return String(x)}}).join(' ')},'*')}catch(e){}}
['error','warn','log'].forEach(function(n){var o=console[n];console[n]=function(){envoyer(n,arguments);o.apply(console,arguments)}});
window.addEventListener('error',function(e){envoyer('error',[e.message+(e.lineno?' (ligne '+e.lineno+')':'')])});
window.addEventListener('unhandledrejection',function(e){envoyer('error',['Promesse rejetée : '+(e.reason&&e.reason.message||e.reason)])});
})();</script>`;

const echapperRegex = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/**
 * Assemble la page d'entrée avec ses feuilles de styles et scripts en ligne : un
 * cadre isolé (srcdoc) ne peut pas aller chercher styles.css ou app.js ailleurs.
 */
export const assemblerApercu = (entry: string, files: CodeFile[]): string => {
  const parChemin = new Map(files.map((f) => [f.path.replace(/^\.\//, ''), f.content]));
  let html = parChemin.get(entry) ?? '';
  const scriptsDiffere: string[] = [];

  for (const [chemin, contenu] of parChemin) {
    const ref = `(?:\\./)?${echapperRegex(chemin)}`;
    if (chemin.endsWith('.css')) {
      html = html.replace(
        new RegExp(`<link\\b[^>]*href=["']${ref}["'][^>]*>`, 'gi'),
        () => `<style>/* ${chemin} */\n${contenu}</style>`,
      );
    } else if (/\.(m?js)$/.test(chemin)) {
      const sur = contenu.replace(/<\/script/gi, '<\\/script');
      html = html.replace(
        new RegExp(`<script\\b([^>]*)src=["']${ref}["']([^>]*)>\\s*</script>`, 'gi'),
        (_m, avant: string, apres: string) => {
          // Un script différé attend le DOM : en ligne, il doit passer en fin de page
          if (/\b(defer|type=["']module["'])/i.test(avant + apres)) {
            scriptsDiffere.push(`<script>/* ${chemin} */\n${sur}</script>`);
            return '';
          }
          return `<script>/* ${chemin} */\n${sur}</script>`;
        },
      );
    }
  }
  if (scriptsDiffere.length) {
    html = /<\/body>/i.test(html)
      ? html.replace(/<\/body>/i, `${scriptsDiffere.join('\n')}\n</body>`)
      : `${html}\n${scriptsDiffere.join('\n')}`;
  }
  // La sonde passe avant tout script du site, pour capter ses premières erreurs
  return /<head[^>]*>/i.test(html) ? html.replace(/<head[^>]*>/i, (m) => `${m}\n${SONDE}`) : `${SONDE}\n${html}`;
};

interface Props {
  projectId: number;
}

export const ProjectOutputs = ({ projectId }: Props) => {
  const [data, setData] = useState<ProjectFilesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [apercu, setApercu] = useState(false);
  const [ouvert, setOuvert] = useState<string | null>(null);
  const [telechargement, setTelechargement] = useState(false);
  const [diagnostic, setDiagnostic] = useState(false);
  const [consoleApercu, setConsoleApercu] = useState<MessageConsole[]>([]);
  const cadre = useRef<HTMLIFrameElement>(null);

  const charger = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get<ProjectFilesResponse>(`/projects/${projectId}/files`);
      setData(response.data);
    } catch {
      // l'intercepteur de l'API affiche déjà l'erreur
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    charger();
  }, [charger]);

  const srcDoc = useMemo(
    () => (data?.entry && apercu ? assemblerApercu(data.entry, data.code) : ''),
    [data, apercu],
  );

  // Console de l'aperçu : remise à zéro à chaque nouvel aperçu
  useEffect(() => {
    setConsoleApercu([]);
  }, [srcDoc]);

  useEffect(() => {
    const recevoir = (e: MessageEvent) => {
      if (e.source !== cadre.current?.contentWindow || e.data?.source !== MARQUE_SONDE) return;
      const { niveau, message } = e.data as MessageConsole;
      setConsoleApercu((liste) => [...liste, { niveau, message: String(message).slice(0, 500) }].slice(-100));
    };
    window.addEventListener('message', recevoir);
    return () => window.removeEventListener('message', recevoir);
  }, []);

  const erreurs = consoleApercu.filter((m) => m.niveau === 'error');

  // Rapport texte à coller dans une conversation pour signaler un problème
  const copierRapport = async () => {
    if (!data) return;
    const lignes = [
      `Diagnostic — projet ${projectId}`,
      `Page d'entrée : ${data.entry ?? 'aucune (pas de page HTML)'}`,
      '',
      'Fichiers :',
      ...data.code.map(
        (f) => `- ${f.path} (${f.size} o) — contenu détecté : ${f.language ?? 'incertain'} — ${f.task_title}`,
      ),
      '',
      'Alertes :',
      ...(data.coherence.length ? data.coherence.map((a) => `- ${a}`) : ['- aucune']),
      '',
      'Console de l\'aperçu :',
      ...(consoleApercu.length
        ? consoleApercu.map((m) => `- [${m.niveau}] ${m.message}`)
        : [apercu ? '- rien' : "- (aperçu non ouvert)"]),
    ];
    try {
      await navigator.clipboard.writeText(lignes.join('\n'));
      toast.success('Rapport copié');
    } catch {
      toast.error('Copie impossible : sélectionne le texte à la main');
    }
  };

  const telecharger = async () => {
    setTelechargement(true);
    try {
      const response = await api.get<Blob>(`/projects/${projectId}/export`, { responseType: 'blob' });
      const nom = /filename="([^"]+)"/.exec(response.headers['content-disposition'] ?? '')?.[1]
        ?? `projet-${projectId}.zip`;
      const url = URL.createObjectURL(response.data);
      const lien = document.createElement('a');
      lien.href = url;
      lien.download = nom;
      lien.click();
      URL.revokeObjectURL(url);
    } catch {
      // l'intercepteur de l'API affiche déjà l'erreur
    } finally {
      setTelechargement(false);
    }
  };

  if (loading && !data) return null;
  if (!data || (data.code.length === 0 && data.documents.length === 0)) return null;

  const fichierOuvert = data.code.find((f) => f.path === ouvert);

  return (
    <div className="bg-paper-card shadow-card border border-ink-line p-6 mb-6">
      <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
        <div className="flex items-start gap-3 min-w-0">
          <Package className="w-5 h-5 text-accent mt-1 shrink-0" />
          <div className="min-w-0">
            <h2 className="font-display text-xl text-ink">Ce que le projet a produit</h2>
            <p className="text-sm text-ink-soft mt-1">
              Les fichiers de code assemblés selon le plan, les documents et les veilles —
              à voir ici, ou à télécharger d'un bloc.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={charger}
            disabled={loading}
            title="Actualiser"
            className="inline-flex items-center gap-2 px-3 py-2 border border-ink-line text-ink hover:border-accent hover:text-accent disabled:opacity-40 transition-colors text-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          {data.entry && (
            <button
              onClick={() => setApercu((v) => !v)}
              className="inline-flex items-center gap-2 px-4 py-2 border border-ink-line text-ink hover:border-accent hover:text-accent transition-colors text-sm font-medium"
            >
              {apercu ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              {apercu ? "Fermer l'aperçu" : 'Aperçu du site'}
            </button>
          )}
          <button
            onClick={() => setDiagnostic((v) => !v)}
            aria-pressed={diagnostic}
            title="Ce que contient vraiment chaque fichier, et les erreurs de l'aperçu"
            className={`inline-flex items-center gap-2 px-3 py-2 border text-sm transition-colors ${
              diagnostic ? 'border-accent text-accent' : 'border-ink-line text-ink hover:border-accent hover:text-accent'
            }`}
          >
            <Bug className="w-4 h-4" />
            Diagnostic
            {erreurs.length > 0 && (
              <span className="px-1.5 bg-danger text-white text-xs figures">{erreurs.length}</span>
            )}
          </button>
          <button
            onClick={telecharger}
            disabled={telechargement}
            className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-white hover:opacity-90 disabled:opacity-40 transition-opacity text-sm font-medium"
          >
            <Download className="w-4 h-4" />
            {telechargement ? 'Préparation…' : 'Tout télécharger (.zip)'}
          </button>
        </div>
      </div>

      {data.coherence.length > 0 && (
        <div className="border border-warning bg-warning/10 p-4 mb-4">
          <p className="flex items-center gap-2 text-sm font-medium text-ink mb-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-warning" />
            Liens à vérifier entre les fichiers
          </p>
          <ul className="space-y-1 text-sm text-ink-soft list-disc pl-5">
            {data.coherence.map((alerte) => (
              <li key={alerte} className="break-words"><Alerte texte={alerte} /></li>
            ))}
          </ul>
        </div>
      )}

      {apercu && data.entry && (
        <div className="border border-ink-line mb-4">
          <div className="px-3 py-1.5 border-b border-ink-line bg-paper-warm text-xs text-ink-faint">
            {data.entry} — aperçu isolé : le site n'a accès ni à l'orchestrateur ni à tes données
          </div>
          {/* allow-scripts sans allow-same-origin : le code généré reste dans sa boîte */}
          <iframe
            ref={cadre}
            title="Aperçu du site"
            sandbox="allow-scripts allow-forms allow-modals"
            srcDoc={srcDoc}
            className="w-full h-[70vh] bg-white"
          />
          {erreurs.length > 0 && !diagnostic && (
            <button
              onClick={() => setDiagnostic(true)}
              className="w-full px-3 py-1.5 border-t border-ink-line text-left text-xs text-danger hover:underline"
            >
              {erreurs.length} erreur(s) JavaScript dans le site — ouvrir le diagnostic
            </button>
          )}
        </div>
      )}

      {diagnostic && (
        <div className="border border-ink-line bg-paper-warm/50 p-4 mb-4 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-medium text-ink flex items-center gap-2">
              <Bug className="w-4 h-4 text-accent" /> Diagnostic
            </p>
            <button
              onClick={copierRapport}
              className="inline-flex items-center gap-1.5 px-3 py-1 border border-ink-line text-xs text-ink hover:border-accent hover:text-accent"
            >
              <ClipboardCopy className="w-3.5 h-3.5" />
              Copier le rapport
            </button>
          </div>

          <div>
            <p className="text-xs uppercase tracking-wider text-ink-faint mb-1">Fichiers de code</p>
            {data.code.length === 0 ? (
              <p className="text-sm text-ink-faint">Aucun fichier de code.</p>
            ) : (
              <ul className="text-sm divide-y divide-ink-line">
                {data.code.map((f) => {
                  const attendu = familleDe(f.path);
                  const discordant = f.language && attendu && f.language !== attendu;
                  return (
                    <li key={f.path} className="flex flex-wrap items-baseline gap-x-3 py-1.5">
                      <span className="font-mono">{f.path}</span>
                      <span className={discordant ? 'text-danger' : 'text-ink-faint'}>
                        contenu : {f.language ?? 'incertain'}
                        {discordant && ` (extension .${f.path.split('.').pop()})`}
                      </span>
                      <span className="text-xs text-ink-faint truncate min-w-0">{f.task_title}</span>
                    </li>
                  );
                })}
              </ul>
            )}
            <p className="mt-1 text-xs text-ink-faint">
              Page d'entrée de l'aperçu : {data.entry ?? 'aucune — ce projet ne contient pas de page HTML'}
            </p>
          </div>

          <div>
            <p className="text-xs uppercase tracking-wider text-ink-faint mb-1">Console de l'aperçu</p>
            {!apercu ? (
              <p className="text-sm text-ink-faint">
                {data.entry ? "Ouvre l'aperçu du site pour capter ses messages et ses erreurs." : "Pas d'aperçu pour ce projet."}
              </p>
            ) : consoleApercu.length === 0 ? (
              <p className="text-sm text-ink-faint">Aucun message : le site n'a signalé aucune erreur.</p>
            ) : (
              <ul className="font-mono text-xs space-y-1 max-h-60 overflow-auto">
                {consoleApercu.map((m, i) => (
                  <li
                    key={i}
                    className={m.niveau === 'error' ? 'text-danger' : m.niveau === 'warn' ? 'text-warning' : 'text-ink-soft'}
                  >
                    [{m.niveau}] {m.message}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {data.code.length > 0 && (
          <div className="min-w-0">
            <h3 className="text-xs uppercase tracking-wider text-ink-faint mb-2">Code</h3>
            <ul className="divide-y divide-ink-line border-y border-ink-line">
              {data.code.map((f) => (
                <li key={f.path}>
                  <button
                    onClick={() => setOuvert((p) => (p === f.path ? null : f.path))}
                    className="w-full flex items-center gap-3 py-2 text-left hover:text-accent"
                  >
                    <FileCode2 className="w-4 h-4 shrink-0 text-ink-faint" />
                    <span className="font-mono text-sm shrink-0 max-w-[60%] truncate">{f.path}</span>
                    <span className="text-xs text-ink-faint truncate min-w-0 hidden sm:inline">{f.task_title}</span>
                    <span className="ml-auto text-xs text-ink-faint shrink-0">{formatTaille(f.size)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        {data.documents.length > 0 && (
          <div className="min-w-0">
            <h3 className="text-xs uppercase tracking-wider text-ink-faint mb-2">Documents et veilles</h3>
            <ul className="divide-y divide-ink-line border-y border-ink-line">
              {data.documents.map((f) => {
                const Icone = f.kind === 'veille' ? Rss : FileText;
                return (
                  <li key={f.path} className="flex items-center gap-3 py-2 min-w-0">
                    <Icone className="w-4 h-4 shrink-0 text-ink-faint" />
                    <span className="text-sm truncate">{f.task_title}</span>
                    <span className="ml-auto text-xs text-ink-faint shrink-0">{formatTaille(f.size)}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </div>

      {fichierOuvert && (
        <pre className="mt-4 max-h-96 overflow-auto border border-ink-line bg-paper-warm p-4 text-xs font-mono whitespace-pre">
          {fichierOuvert.content}
        </pre>
      )}
    </div>
  );
};

export default ProjectOutputs;
