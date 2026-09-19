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
