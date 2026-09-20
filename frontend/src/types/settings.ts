/**
 * Types pour les paramètres utilisateur
 */

export interface OllamaModel {
  name: string;
  size: number;
  modified_at: string;
}

export interface UserSettings {
  id: number;
  user_id: number;
  ollama_model_code: string;
  ollama_model_ideation: string;
  ollama_model_analysis: string;
  ollama_model_task_generation: string;
  ollama_model_text: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserSettingsUpdate {
  ollama_model_code?: string;
  ollama_model_ideation?: string;
  ollama_model_analysis?: string;
  ollama_model_task_generation?: string;
  ollama_model_text?: string | null;
}

/** Flux RSS de la bibliothèque personnelle */
export interface RssFeed {
  id: number;
  url: string;
  title: string;
  tags: string[];
  enabled: boolean;
  last_checked: string | null;
  last_status: string | null;
  last_entry_count: number;
  created_at: string;
}

export interface RssFeedCreate {
  url: string;
  title?: string;
  tags?: string[];
}

export interface RssFeedUpdate {
  title?: string;
  tags?: string[];
  enabled?: boolean;
}

/** Vérification d'un flux avant enregistrement */
export interface FeedCheckResult {
  ok: boolean;
  status: string;
  title: string;
  tags: string[];
  entry_count: number;
  sample: string[];
}
