/**
 * Composant IdeationChat
 * Interface de dialogue socratique pour la phase d'idéation d'un projet
 * Design épuré type carnet de notes avec streaming en temps réel
 */

import { useState, useEffect, useRef } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { ideationService } from '../services/ideation';
import type { IdeationMessage } from '../types/ideation.types';
import toast from 'react-hot-toast';

interface IdeationChatProps {
  projectId: number;
  onComplete?: () => void;
  onMessageComplete?: () => void;
}

export const IdeationChat = ({ projectId, onMessageComplete }: IdeationChatProps) => {
  const [messages, setMessages] = useState<IdeationMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Charger l'historique de conversation au montage
  useEffect(() => {
    loadConversation();
  }, [projectId]);

  // Auto-scroll vers le bas quand de nouveaux messages arrivent
  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadConversation = async () => {
    try {
      setIsLoading(true);
      const conversation = await ideationService.getConversation(projectId);

      // Si l'historique est vide ou contient seulement le message système, démarrer l'idéation
      if (conversation.messages.length === 0 ||
          (conversation.messages.length === 1 && conversation.messages[0].role === 'SYSTEM')) {
        const startResponse = await ideationService.startIdeation(projectId);
        // Afficher le message de bienvenue ET la première réponse de l'IA
        setMessages([startResponse.welcome_message, startResponse.initial_response]);
      } else {
        // Sinon, afficher l'historique existant
        setMessages(conversation.messages);
      }
    } catch (error) {
      console.error('Error loading conversation:', error);
      // Si la conversation n'existe pas encore, démarrer l'idéation
      try {
        const startResponse = await ideationService.startIdeation(projectId);
        // Afficher le message de bienvenue ET la première réponse de l'IA
        setMessages([startResponse.welcome_message, startResponse.initial_response]);
      } catch (startError) {
        console.error('Error starting ideation:', startError);
        toast.error('Erreur lors du démarrage de l\'idéation');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isStreaming) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setIsStreaming(true);
    setStreamingContent('');

    // Ajouter le message utilisateur immédiatement à l'UI
    const tempUserMessage: IdeationMessage = {
      id: Date.now(), // Temporary ID
      project_id: projectId,
      role: 'USER',
      content: userMessage,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMessage]);

    try {
      // Stream la réponse de l'assistant
      await ideationService.sendMessageStream(
        projectId,
        userMessage,
        // onChunk: Accumuler les chunks
        (chunk: string) => {
          setStreamingContent((prev) => prev + chunk);
        },
        // onComplete: Finaliser et recharger la conversation
        async () => {
          setIsStreaming(false);
          setStreamingContent('');
          // Recharger la conversation pour avoir les messages avec leurs vrais IDs
          await loadConversation();
          // Notifier le parent qu'un message a été reçu (pour détecter GENERATE_TASKS)
          onMessageComplete?.();
        },
        // onError
        (error: Error) => {
          console.error('Streaming error:', error);
          setIsStreaming(false);
          setStreamingContent('');
          toast.error('Erreur lors de l\'envoi du message');
        }
      );
    } catch (error) {
      console.error('Error sending message:', error);
      setIsStreaming(false);
      setStreamingContent('');
      toast.error('Erreur lors de l\'envoi du message');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Envoyer avec Cmd/Ctrl + Enter
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  };

  if (isLoading && messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] bg-paper-card rounded-none shadow-card border border-ink-line">
      {/* Header */}
      <div className="px-6 py-4 border-b-2 border-ink bg-paper">
        <p className="kicker mb-0.5">Correspondance d'atelier</p>
        <h2 className="font-display text-xl text-ink">Dialogue d'idéation</h2>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {messages.map((message, index) => (
          <div
            key={message.id || index}
            className={`flex flex-col ${
              message.role === 'USER' ? 'items-end' : 'items-start'
            }`}
          >
            {/* Rôle et heure, en étiquette éditoriale */}
            <div className="flex items-center gap-2 mb-1.5">
              <span className="kicker">
                {message.role === 'USER' ? 'Vous' : message.role === 'SYSTEM' ? 'Note' : "L'assistant"}
              </span>
              <span className="text-[10px] text-ink-faint figures">{formatTimestamp(message.created_at)}</span>
            </div>

            {/* Bloc de message : encre pour vous, filet vermillon pour l'assistant */}
            <div
              className={`max-w-[85%] text-sm leading-relaxed whitespace-pre-wrap break-words ${
                message.role === 'USER'
                  ? 'bg-ink text-paper px-4 py-3'
                  : message.role === 'SYSTEM'
                  ? 'text-ink-faint italic border border-dashed border-ink-line px-4 py-2'
                  : 'text-ink border-l-2 border-accent pl-4 py-1'
              }`}
            >
              {message.content}
            </div>
          </div>
        ))}

        {/* Message en cours de streaming */}
        {isStreaming && streamingContent && (
          <div className="flex flex-col items-start">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="kicker">L'assistant</span>
              <span className="flex items-center gap-1">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="w-1 h-1 bg-ink-faint inline-block animate-pulse"
                    style={{ animationDelay: `${i * 180}ms` }}
                  />
                ))}
              </span>
            </div>
            <div className="max-w-[85%] text-sm leading-relaxed text-ink border-l-2 border-accent pl-4 py-1 whitespace-pre-wrap break-words">
              {streamingContent}
              <span className="inline-block w-[2px] h-4 ml-0.5 align-middle bg-accent animate-pulse" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-ink-line bg-paper">
        <div className="flex items-end gap-3">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Décrivez votre idée ou répondez aux questions..."
              disabled={isStreaming}
              rows={3}
              className="w-full px-4 py-3 bg-paper-card border border-ink-line focus:outline-none focus:border-ink focus:ring-1 focus:ring-ink resize-none disabled:bg-paper-warm disabled:cursor-not-allowed text-sm transition-colors"
            />
            <div className="absolute bottom-2 right-2 text-xs text-ink-faint">
              Cmd/Ctrl + Enter pour envoyer
            </div>
          </div>
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isStreaming}
            className="flex items-center justify-center w-12 h-12 bg-accent text-white rounded-none hover:bg-accent-deep disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isStreaming ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
