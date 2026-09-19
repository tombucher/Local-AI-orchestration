/**
 * Types pour le module d'idéation socratique
 */

export type MessageRole = 'USER' | 'ASSISTANT' | 'SYSTEM';

export interface IdeationMessage {
  id: number;
  project_id: number;
  role: MessageRole;
  content: string;
  meta?: Record<string, any>;
  created_at: string;
}

export interface IdeationConversation {
  project_id: number;
  messages: IdeationMessage[];
  total_messages: number;
  ideation_completed: boolean;
  ideation_completed_at?: string;
}

export interface IdeationStartRequest {
  project_id: number;
}

export interface IdeationStartResponse {
  project_id: number;
  status: string;
  welcome_message: IdeationMessage;
  initial_response: IdeationMessage;
}

export interface IdeationSendMessageRequest {
  message: string;
}

export interface IdeationSendMessageResponse {
  user_message: IdeationMessage;
  assistant_message: IdeationMessage;
}

export interface IdeationCompleteResponse {
  project_id: number;
  status: string;
  ideation_completed_at: string;
  messages_count: number;
  next_step: string;
}
