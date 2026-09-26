/**
 * Page Settings
 * - Affiche et permet de modifier les paramètres utilisateur
 * - Sélection granulaire des modèles Ollama par type de tâche
 */

import { useEffect, useState } from 'react';
import { Settings as SettingsIcon, CheckCircle, AlertCircle, Code, Lightbulb, FileSearch, ListTodo, FileText } from 'lucide-react';
import { Navbar } from '../components/Layout/Navbar';
import { Sidebar } from '../components/Layout/Sidebar';
import { settingsApi } from '../services/settingsApi';
import { OllamaModel, UserSettings } from '../types/settings';
import Loader from '../components/ui/Loader';
import FeedLibrary from '../components/settings/FeedLibrary';
import BriefingSettings from '../components/settings/BriefingSettings';
import ProjectsFolderSettings from '../components/settings/ProjectsFolderSettings';

type ModelType = 'code' | 'text' | 'ideation' | 'analysis' | 'task_generation';

interface ModelSection {
  key: ModelType;
  field: keyof UserSettings;
  icon: any;
  title: string;
  description: string;
  color: string;
}

const MODEL_SECTIONS: ModelSection[] = [
  {
    key: 'code',
    field: 'ollama_model_code',
    icon: Code,
    title: 'Génération de Code',
    description: 'Modèle utilisé pour générer du code à partir des tâches',
    color: 'blue',
  },
  {
    key: 'text',
    field: 'ollama_model_text',
    icon: FileText,
    title: 'Génération de Texte',
    description: 'Modèle pour les tâches texte : recherche, admin, rédaction de documents. Les modèles thinking (qwen3) utilisent une double passe automatique.',
    color: 'orange',
  },
  {
    key: 'ideation',
    field: 'ollama_model_ideation',
    icon: Lightbulb,
    title: 'Idéation / Brainstorming',
    description: 'Modèle utilisé pour les sessions de chat d\'idéation',
    color: 'yellow',
  },
  {
    key: 'analysis',
    field: 'ollama_model_analysis',
    icon: FileSearch,
    title: 'Analyse de Projet',
    description: 'Modèle utilisé pour analyser et comprendre les projets',
    color: 'purple',
  },
  {
    key: 'task_generation',
    field: 'ollama_model_task_generation',
    icon: ListTodo,
    title: 'Génération de Tâches',
    description: 'Modèle utilisé pour suggérer et créer des tâches',
    color: 'green',
  },
];

export const Settings = () => {
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<ModelType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<ModelType | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [modelsData, settingsData] = await Promise.all([
        settingsApi.getOllamaModels(),
        settingsApi.getUserSettings(),
      ]);

      setModels(modelsData);
      setSettings(settingsData);
    } catch (err: any) {
      console.error('Failed to load settings:', err);
      setError(
        err.response?.data?.detail ||
        'Impossible de charger les paramètres. Vérifiez que le backend est accessible.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleModelChange = async (modelType: ModelType, modelName: string) => {
    try {
      setSaving(modelType);
      setError(null);
      setSuccess(null);

      const section = MODEL_SECTIONS.find(s => s.key === modelType);
      if (!section) return;

      const updatedSettings = await settingsApi.updateUserSettings({
        [section.field]: modelName,
      });

      setSettings(updatedSettings);
      setSuccess(modelType);

      // Masquer le message de succès après 3 secondes
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      console.error('Failed to update model:', err);
      setError(
        err.response?.data?.detail ||
        'Erreur lors de la mise à jour du modèle'
      );
    } finally {
      setSaving(null);
    }
  };

  const formatSize = (bytes: number): string => {
    return `${(bytes / 1e9).toFixed(2)} GB`;
  };

  const getColorClasses = (color: string) => {
    const colors: Record<string, { border: string; bg: string; text: string }> = {
      blue: { border: 'border-info', bg: 'bg-info/5', text: 'text-info' },
      orange: { border: 'border-warning', bg: 'bg-warning/5', text: 'text-warning' },
      yellow: { border: 'border-warning', bg: 'bg-warning/5', text: 'text-warning' },
      purple: { border: 'border-accent', bg: 'bg-accent-wash', text: 'text-accent-deep' },
      green: { border: 'border-success', bg: 'bg-success/5', text: 'text-success' },
    };
    return colors[color] || colors.blue;
  };

  return (
    <div className="min-h-screen bg-paper">
      <Navbar />

      <div className="flex">
        <Sidebar />

        {/* Main Content */}
        <main className="flex-1 min-w-0 p-6 lg:p-8">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <SettingsIcon className="w-8 h-8 text-ink-soft" />
              <h1 className="text-3xl font-bold text-ink">Paramètres</h1>
            </div>
            <p className="text-ink-soft">
              Configurez les modèles IA pour chaque type de tâche
            </p>
          </div>

          {/* Messages d'erreur globaux */}
          {error && (
            <div className="mb-6 p-4 bg-danger/5 border border-danger/30 rounded-none flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-danger" />
              <p className="text-danger">{error}</p>
            </div>
          )}

          {/* Loading state */}
          {loading ? (
            <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-12 text-center">
              <Loader size="lg" />
              <p className="text-ink-soft">Chargement des paramètres...</p>
            </div>
          ) : (
            <>
              {/* Model Sections */}
              <div className="space-y-6">
                {MODEL_SECTIONS.map((section) => {
                  const Icon = section.icon;
                  const colors = getColorClasses(section.color);
                  const currentModel = settings?.[section.field] as string;
                  const isSaving = saving === section.key;
                  const isSuccess = success === section.key;

                  return (
                    <div
                      key={section.key}
                      className={`bg-paper-card rounded-none shadow-card border-2 ${colors.border} overflow-hidden`}
                    >
                      {/* Section Header */}
                      <div className={`${colors.bg} px-6 py-4 border-b-2 ${colors.border}`}>
                        <div className="flex items-center gap-3 mb-1">
                          <Icon className={`w-6 h-6 ${colors.text}`} />
                          <h2 className="text-xl font-semibold text-ink">
                            {section.title}
                          </h2>
                        </div>
                        <p className="text-sm text-ink-soft ml-9">
                          {section.description}
                        </p>
                      </div>

                      {/* Success Message */}
                      {isSuccess && (
                        <div className="mx-6 mt-4 p-3 bg-success/5 border border-success/30 rounded-none flex items-center gap-2">
                          <CheckCircle className="w-4 h-4 text-success" />
                          <p className="text-sm text-success font-medium">
                            Modèle mis à jour avec succès !
                          </p>
                        </div>
                      )}

                      {/* Model Selector */}
                      <div className="p-6">
                        {models.length > 0 ? (
                          <div className="space-y-2">
                            {models.map((model) => {
                              const isSelected = currentModel === model.name;

                              return (
                                <label
                                  key={model.name}
                                  className={`
                                    flex items-center gap-3 p-3 border-2 rounded-none cursor-pointer transition-all
                                    ${
                                      isSelected
                                        ? `${colors.border} ${colors.bg}`
                                        : 'border-ink-line hover:border-ink-line hover:bg-paper-warm'
                                    }
                                    ${isSaving ? 'opacity-50 cursor-not-allowed' : ''}
                                  `}
                                >
                                  <input
                                    type="radio"
                                    name={`model-${section.key}`}
                                    value={model.name}
                                    checked={isSelected}
                                    onChange={() => handleModelChange(section.key, model.name)}
                                    disabled={isSaving}
                                    className={`w-4 h-4 ${colors.text} focus:ring-2 focus:ring-offset-0`}
                                  />
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                      <span className="font-medium text-ink truncate">
                                        {model.name}
                                      </span>
                                      {isSelected && (
                                        <span className={`px-2 py-0.5 text-xs font-medium ${colors.bg} ${colors.text} rounded border ${colors.border}`}>
                                          Actif
                                        </span>
                                      )}
                                    </div>
                                    <div className="text-xs text-ink-faint">
                                      {formatSize(model.size)}
                                    </div>
                                  </div>
                                </label>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="text-center py-8">
                            <AlertCircle className="w-12 h-12 mx-auto mb-3 text-ink-faint" />
                            <p className="text-ink-soft mb-2">Aucun modèle Ollama disponible</p>
                            <p className="text-sm text-ink-faint">
                              Assurez-vous qu'Ollama est installé et qu'au moins un modèle est téléchargé
                            </p>
                          </div>
                        )}

                        {isSaving && (
                          <div className="mt-3 flex items-center justify-center gap-2 text-ink-soft">
                            <Loader size="lg" />
                            <span className="text-sm font-medium">Enregistrement...</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Bibliothèque de flux RSS pour la veille */}
              <div className="mt-6">
                <ProjectsFolderSettings />
                <BriefingSettings />
                <FeedLibrary />
              </div>

              {/* Info supplémentaire */}
              <div className="mt-6 bg-info/5 border border-info/30 rounded-none p-4">
                <h3 className="font-semibold text-info mb-2">
                  Conseils pour choisir les modèles
                </h3>
                <ul className="text-sm text-info space-y-1">
                  <li>• <strong>Génération de Code</strong>: Utilisez codestral, deepseek-coder ou codellama pour de meilleurs résultats</li>
                  <li>• <strong>Génération de Texte</strong>: Les modèles thinking (qwen3) utilisent une double passe automatique — plus lent mais bien meilleure qualité. Mistral est plus rapide.</li>
                  <li>• <strong>Idéation</strong>: Les modèles génériques (mistral, llama) sont excellents pour la créativité</li>
                  <li>• <strong>Analyse</strong>: Les modèles plus grands (13B+) offrent une meilleure compréhension</li>
                  <li>• <strong>Génération de Tâches</strong>: Les modèles 7B sont suffisants et plus rapides</li>
                </ul>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
};
