/**
 * Paramètres : quel modèle pour quel usage, le dossier de projets, le
 * briefing, les flux de veille.
 *
 * Avant : cinq grands cadres colorés listant chacun tous les modèles en
 * boutons radio, suivis de conseils qui citaient des modèles disparus
 * (codestral, mistral, llama). Avec deux modèles installés, c'était dix
 * boutons pour un choix. Un tableau usage → modèle suffit.
 */

import { useEffect, useState } from 'react';
import { AlertCircle, Check, Loader2 } from 'lucide-react';
import { Navbar } from '../components/Layout/Navbar';
import { Sidebar } from '../components/Layout/Sidebar';
import { settingsApi } from '../services/settingsApi';
import { OllamaModel, UserSettings } from '../types/settings';
import Loader from '../components/ui/Loader';
import FeedLibrary from '../components/settings/FeedLibrary';
import BriefingSettings from '../components/settings/BriefingSettings';
import ProjectsFolderSettings from '../components/settings/ProjectsFolderSettings';

type ChampModele = 'ollama_model_code' | 'ollama_model_text' | 'ollama_model_ideation'
  | 'ollama_model_analysis' | 'ollama_model_task_generation';

const USAGES: { champ: ChampModele; titre: string; detail: string }[] = [
  { champ: 'ollama_model_code', titre: 'Code', detail: 'Fichiers générés depuis les tâches de code' },
  { champ: 'ollama_model_text', titre: 'Textes', detail: 'Documents, recherches, tâches administratives' },
  { champ: 'ollama_model_ideation', titre: 'Discussion', detail: 'Idéation et discussion sur un projet' },
  { champ: 'ollama_model_analysis', titre: 'Analyse', detail: 'Lecture d\'un projet pour en proposer des tâches' },
  { champ: 'ollama_model_task_generation', titre: 'Tâches', detail: 'Rédaction des tâches proposées' },
];

const taille = (octets: number) => `${(octets / 1e9).toFixed(1)} Go`;

export const Settings = () => {
  const [modeles, setModeles] = useState<OllamaModel[]>([]);
  const [reglages, setReglages] = useState<UserSettings | null>(null);
  const [chargement, setChargement] = useState(true);
  const [enregistrement, setEnregistrement] = useState<ChampModele | null>(null);
  const [enregistre, setEnregistre] = useState<ChampModele | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([settingsApi.getOllamaModels(), settingsApi.getUserSettings()])
      .then(([m, r]) => {
        setModeles(m);
        setReglages(r);
      })
      .catch((err: any) => setErreur(err.response?.data?.detail || 'Impossible de charger les paramètres. Le backend est-il lancé ?'))
      .finally(() => setChargement(false));
  }, []);

  const choisir = async (champ: ChampModele, nom: string) => {
    setEnregistrement(champ);
    setErreur(null);
    try {
      setReglages(await settingsApi.updateUserSettings({ [champ]: nom }));
      setEnregistre(champ);
      setTimeout(() => setEnregistre((c) => (c === champ ? null : c)), 2500);
    } catch (err: any) {
      setErreur(err.response?.data?.detail || 'Le modèle n\'a pas pu être enregistré');
    } finally {
      setEnregistrement(null);
    }
  };

  return (
    <div className="min-h-screen bg-paper">
      <Navbar />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 min-w-0 p-6 lg:p-10 max-w-4xl">
          <header className="mb-8">
            <p className="kicker">Réglages</p>
            <h1 className="font-display text-4xl text-ink mt-1">Paramètres</h1>
            <div className="rule-strong mt-4" />
          </header>

          {erreur && (
            <div className="mb-6 p-4 bg-danger/5 border border-danger/30 flex items-center gap-3 text-danger">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <p>{erreur}</p>
            </div>
          )}

          {chargement ? (
            <div className="py-12 flex justify-center"><Loader size="lg" label="Lecture des réglages…" /></div>
          ) : (
            <section className="bg-paper-card border border-ink-line shadow-card p-5 mb-6">
              <div className="flex items-baseline justify-between gap-4 mb-1 pb-2 rule">
                <h2 className="font-display text-2xl text-ink">Modèles</h2>
                <p className="text-xs text-ink-faint">
                  {modeles.length > 0 ? `${modeles.length} installé${modeles.length > 1 ? 's' : ''} dans Ollama` : 'Ollama injoignable'}
                </p>
              </div>
              <p className="text-sm text-ink-soft mb-4">
                Tout tourne sur ta machine. Un gros modèle pour ce qui demande de la finesse,
                un petit pour ce qui doit répondre vite. La veille et le briefing utilisent le modèle
                rapide défini dans <code className="font-mono text-xs">.env</code> (<code className="font-mono text-xs">OLLAMA_MODEL_PROMPT</code>).
              </p>

              {modeles.length === 0 ? (
                <p className="text-sm text-ink-faint">
                  Aucun modèle trouvé : lance Ollama, puis <code className="font-mono text-xs">ollama pull qwen3.8:27b-mlx</code>.
                </p>
              ) : (
                <ul className="divide-y divide-ink-line/60">
                  {USAGES.map(({ champ, titre, detail }) => {
                    const actuel = (reglages?.[champ] as string | null) ?? '';
                    const inconnu = actuel && !modeles.some((m) => m.name === actuel);
                    return (
                      <li key={champ} className="py-3 flex flex-wrap items-center gap-x-6 gap-y-2">
                        <div className="w-40 shrink-0">
                          <p className="font-medium text-ink">{titre}</p>
                          <p className="text-xs text-ink-faint leading-snug">{detail}</p>
                        </div>
                        <select
                          aria-label={`Modèle pour ${titre.toLowerCase()}`}
                          value={actuel}
                          disabled={enregistrement === champ}
                          onChange={(e) => choisir(champ, e.target.value)}
                          className="flex-1 min-w-[14rem] px-3 py-2 border border-ink-line bg-paper text-sm text-ink focus:border-accent focus:outline-none disabled:opacity-50"
                        >
                          {!actuel && <option value="">— choisir —</option>}
                          {inconnu && <option value={actuel}>{actuel} (plus installé : repli automatique)</option>}
                          {modeles.map((m) => (
                            <option key={m.name} value={m.name}>{m.name} · {taille(m.size)}</option>
                          ))}
                        </select>
                        <span className="w-5 text-success">
                          {enregistrement === champ && <Loader2 className="w-4 h-4 animate-spin text-ink-faint" />}
                          {enregistre === champ && <Check className="w-4 h-4" />}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          )}

          <ProjectsFolderSettings />
          <BriefingSettings />
          <FeedLibrary />
        </main>
      </div>
    </div>
  );
};
