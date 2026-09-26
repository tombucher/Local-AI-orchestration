/**
 * Dossier de projets : un sous-dossier par projet, avec sa fiche .md.
 *
 * Tom écrit ses projets dans son éditeur ; l'outil les lit, coche les tâches
 * terminées et range ce qu'il produit dans Production/.
 */

import { useEffect, useState } from 'react';
import { ChevronLeft, Folder, FolderCheck, FolderOpen, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import {
  BrowseResult,
  ProjectsFolderState,
  SyncReport,
  projectFoldersApi,
} from '../../services/projectFoldersApi';

const MODELE = `# Tickets de veille

Une imprimante thermique qui imprime l'actu écologique
en ASCII. Je vise un appel à projets avant décembre.

## Veille visuelle
mots-clés: ticket de caisse, ASCII art

## Note d'intention
type: document · échéance: 15/10 · après: Veille visuelle
Ton personnel, à la première personne.
- [ ] Origine du projet
- [ ] Dispositif technique

## Page web de présentation
type: code · après: Note d'intention · fichier: index.html`;

const resumer = (r: SyncReport) =>
  [
    r.created.length && `${r.created.length} projet(s) créé(s)`,
    r.updated.length && `${r.updated.length} mis à jour`,
    r.checked.length && `${r.checked.length} tâche(s) cochée(s)`,
    r.exported.length && `${r.exported.length} fichier(s) rangé(s) dans Production`,
  ]
    .filter(Boolean)
    .join(' · ') || 'Tout est déjà à jour';

export const ProjectsFolderSettings = () => {
  const [etat, setEtat] = useState<ProjectsFolderState | null>(null);
  const [parcours, setParcours] = useState<BrowseResult | null>(null);
  const [rapport, setRapport] = useState<SyncReport | null>(null);
  const [occupe, setOccupe] = useState(false);

  useEffect(() => {
    projectFoldersApi.get().then(setEtat).catch(() => {});
  }, []);

  const ouvrir = async (path: string) => {
    try {
      setParcours(await projectFoldersApi.browse(path));
    } catch {
      // erreur affichée par l'intercepteur
    }
  };

  const choisir = async (path: string | null) => {
    setOccupe(true);
    try {
      const nouveau = await projectFoldersApi.set(path);
      setEtat(nouveau);
      setParcours(null);
      setRapport(nouveau.report ?? null);
      if (path) toast.success('Dossier de projets enregistré');
    } catch {
      // erreur affichée par l'intercepteur
    } finally {
      setOccupe(false);
    }
  };

  const synchroniser = async () => {
    setOccupe(true);
    try {
      const r = await projectFoldersApi.sync();
      setRapport(r);
      setEtat(await projectFoldersApi.get());
    } catch {
      // erreur affichée par l'intercepteur
    } finally {
      setOccupe(false);
    }
  };

  if (!etat) return null;

  return (
    <div className="bg-paper-card shadow-card border border-ink-line p-6 mb-6">
      <div className="flex items-start gap-3">
        <FolderOpen className="w-5 h-5 text-accent mt-1 shrink-0" />
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-xl text-ink">Dossier de projets</h2>
          <p className="text-sm text-ink-soft mt-1 max-w-2xl">
            Un sous-dossier par projet, avec sa fiche <code className="font-mono text-xs">.md</code>{' '}
            écrite dans ton éditeur habituel. L'outil suit chaque enregistrement, coche les
            tâches terminées dans la fiche et range ce qu'il produit dans un dossier{' '}
            <code className="font-mono text-xs">Production</code> à côté.
          </p>

          {!etat.available ? (
            <p className="mt-4 text-sm text-warning">
              Aucun dossier du Mac n'est partagé avec l'outil (voir PROJECTS_HOST_DIR dans .env).
            </p>
          ) : (
            <>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <span className="font-mono text-sm text-ink break-all">
                  {etat.display ?? 'Aucun dossier choisi'}
                </span>
                <button
                  onClick={() => ouvrir(etat.path ?? '')}
                  disabled={occupe}
                  className="px-3 py-1.5 border border-ink-line text-sm text-ink hover:border-accent hover:text-accent disabled:opacity-40"
                >
                  {etat.path ? 'Changer' : 'Choisir un dossier'}
                </button>
                {etat.path && (
                  <>
                    <button
                      onClick={synchroniser}
                      disabled={occupe}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-ink-line text-sm text-ink hover:border-accent hover:text-accent disabled:opacity-40"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${occupe ? 'animate-spin' : ''}`} />
                      Synchroniser
                    </button>
                    <button
                      onClick={() => choisir(null)}
                      disabled={occupe}
                      className="px-3 py-1.5 text-sm text-ink-faint hover:text-accent disabled:opacity-40"
                    >
                      Arrêter
                    </button>
                  </>
                )}
              </div>

              {parcours && (
                <div className="mt-4 border border-ink-line">
                  <div className="flex items-center gap-2 px-3 py-2 border-b border-ink-line bg-paper-warm">
                    {parcours.parent !== null && (
                      <button
                        onClick={() => ouvrir(parcours.parent ?? '')}
                        className="p-1 hover:text-accent"
                        title="Dossier parent"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                    )}
                    <span className="font-mono text-xs text-ink-soft truncate min-w-0 flex-1">
                      {parcours.display}
                    </span>
                    <button
                      onClick={() => choisir(parcours.path)}
                      disabled={occupe}
                      className="shrink-0 px-3 py-1 bg-accent text-white text-sm hover:opacity-90 disabled:opacity-40"
                    >
                      Choisir ce dossier
                    </button>
                  </div>
                  <ul className="max-h-72 overflow-auto divide-y divide-ink-line">
                    {parcours.dirs.length === 0 && (
                      <li className="px-3 py-2 text-sm text-ink-faint">Aucun sous-dossier</li>
                    )}
                    {parcours.dirs.map((d) => (
                      <li key={d.path}>
                        <button
                          onClick={() => ouvrir(d.path)}
                          className="w-full flex items-center gap-2 px-3 py-2 text-left text-sm hover:text-accent"
                        >
                          {d.is_project ? (
                            <FolderCheck className="w-4 h-4 text-success shrink-0" />
                          ) : (
                            <Folder className="w-4 h-4 text-ink-faint shrink-0" />
                          )}
                          <span className="truncate">{d.name}</span>
                          {d.is_project && (
                            <span className="ml-auto text-xs text-ink-faint shrink-0">contient une fiche .md</span>
                          )}
                        </button>
                      </li>
                    ))}
                  </ul>
                  <p className="px-3 py-2 border-t border-ink-line text-xs text-ink-faint">
                    Choisis le dossier qui <em>contient</em> tes dossiers-projets, pas un projet lui-même.
                  </p>
                </div>
              )}

              {etat.path && (
                <div className="mt-4">
                  <p className="text-xs uppercase tracking-wider text-ink-faint mb-1">
                    {etat.projects.length} projet(s) trouvé(s)
                  </p>
                  {etat.projects.length > 0 && (
                    <ul className="text-sm text-ink-soft space-y-0.5">
                      {etat.projects.map((p) => (
                        <li key={p.path} className="truncate">
                          <span className="text-ink">{p.folder}</span>
                          <span className="text-ink-faint"> / {p.file}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {rapport && (
                <div className="mt-4 text-sm">
                  <p className="text-ink">{resumer(rapport)}</p>
                  {rapport.kept.length > 0 && (
                    <p className="text-ink-soft mt-1">
                      Non écrasés car retouchés à la main : {rapport.kept.join(', ')}
                    </p>
                  )}
                  {rapport.warnings.length > 0 && (
                    <ul className="mt-2 text-warning list-disc pl-5 space-y-0.5">
                      {rapport.warnings.map((w) => (
                        <li key={w}>{w}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </>
          )}

          <details className="mt-5">
            <summary className="text-sm text-accent cursor-pointer">Le format d'une fiche</summary>
            <div className="mt-3 grid gap-4 md:grid-cols-2">
              <pre className="text-xs font-mono bg-paper-warm border border-ink-line p-3 overflow-auto whitespace-pre-wrap">
                {MODELE}
              </pre>
              <ul className="text-sm text-ink-soft space-y-2">
                <li><strong className="text-ink"># Titre</strong> : le nom du projet (sinon, celui du dossier).</li>
                <li><strong className="text-ink">Texte libre</strong> : la description. Sans aucune tâche, lance
                  « Analyser avec l'IA » depuis le projet pour qu'elle t'en propose.</li>
                <li><strong className="text-ink">## Titre</strong> : une tâche, créée en attente — c'est toi qui
                  l'actives. <code className="font-mono text-xs">## [x]</code> = terminée.</li>
                <li><strong className="text-ink">Ligne sous le titre</strong> (facultative) :{' '}
                  <code className="font-mono text-xs">type</code> (document, code, veille, veille visuelle,
                  recherche, financement, administratif — sinon deviné),{' '}
                  <code className="font-mono text-xs">échéance</code>,{' '}
                  <code className="font-mono text-xs">après</code>,{' '}
                  <code className="font-mono text-xs">priorité</code>,{' '}
                  <code className="font-mono text-xs">fichier</code>,{' '}
                  <code className="font-mono text-xs">mots-clés</code>.</li>
                <li><strong className="text-ink">- [ ] cases</strong> : les étapes de la tâche (les sections
                  d'un document).</li>
                <li>Une tâche retirée de la fiche est annulée si elle n'a encore rien produit.</li>
              </ul>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
};

export default ProjectsFolderSettings;
