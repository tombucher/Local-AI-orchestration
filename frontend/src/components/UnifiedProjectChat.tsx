/**
 * Composant de dialogue unifié pour création de projet
 *
 * Remplace le formulaire traditionnel par un dialogue direct avec l'IA
 */
import React, { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { unifiedProjectService } from '../services/unifiedProject';
import { ideationService } from '../services/ideation';
import { IdeationChat } from './IdeationChat';
import { FinalizationValidationModal } from './FinalizationValidationModal';
import { Navbar } from './Layout/Navbar';
import { Sidebar } from './Layout/Sidebar';
import toast from 'react-hot-toast';
import { Sparkles, CheckCircle, Loader2, Play } from 'lucide-react';
import type { FinalizeProjectResponse, TaskGenerated } from '../services/unifiedProject';
import type { ProjectFinalizationPreview } from '../types/project.types';
import Loader from './ui/Loader';

const UnifiedProjectChat: React.FC = () => {
  const navigate = useNavigate();
  const [projectId, setProjectId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [shouldCheckForSignal, setShouldCheckForSignal] = useState(true);
  const isProcessingSignal = useRef(false);
  const [showFinalization, setShowFinalization] = useState(false);
  const [isFinalizing, setIsFinalizing] = useState(false);
  const [finalizationResult] = useState<FinalizeProjectResponse | null>(null);
  const [isChatStarted, setIsChatStarted] = useState(false);

  // Nouveaux états pour le modal de validation
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [finalizationPreview, setFinalizationPreview] = useState<ProjectFinalizationPreview | null>(null);

  const handleStartChat = async () => {
    // Vérifier si un projet est déjà en cours pour éviter les doublons
    if (projectId !== null) {
      console.log('Projet déjà chargé, pas de nouveau démarrage nécessaire');
      setIsChatStarted(true);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await unifiedProjectService.startProjectChat();
      setProjectId(response.project_id);
      setIsChatStarted(true);
      console.log('Nouveau projet démarré avec ID:', response.project_id);
    } catch (err) {
      console.error('Error starting project chat:', err);
      setError('Impossible de démarrer le dialogue. Réessayez.');
    } finally {
      setIsLoading(false);
    }
  };

  // Suppression de l'appel automatique au montage
  // Le chat ne démarre plus que sur action utilisateur explicite

  // Vérifier si le signal GENERATE_TASKS est présent dans la conversation
  // Appelée uniquement après l'envoi de messages, pas en boucle
  const checkForSignal = useCallback(async () => {
    if (!projectId || !shouldCheckForSignal || isProcessingSignal.current) return;

    try {
      // Empêcher les exécutions multiples simultanées
      if (isProcessingSignal.current) return;
      isProcessingSignal.current = true;

      const conversation = await ideationService.getConversation(projectId);

      // Chercher le signal GENERATE_TASKS dans les derniers messages de l'assistant
      const lastAssistantMessages = conversation.messages
        .filter(msg => msg.role === 'ASSISTANT')
        .slice(-5); // Les 5 derniers messages assistant

      console.log('🔍 Vérification du signal GENERATE_TASKS...', {
        totalMessages: conversation.messages.length,
        lastAssistantMessages: lastAssistantMessages.length,
        lastContents: lastAssistantMessages.map(m => m.content.substring(0, 100))
      });

      const hasSignal = lastAssistantMessages.some(msg => {
        const content = msg.content;
        const hasExactSignal = content.includes('GENERATE_TASKS');
        const hasGenerationMention = content.toLowerCase().includes('génération des tâches');
        const hasGeneratePlan = content.toLowerCase().includes('générer le plan');
        const hasTuVeuxQue = content.toLowerCase().includes('tu veux que je génère');

        if (hasExactSignal || hasGenerationMention || hasGeneratePlan || hasTuVeuxQue) {
          console.log('✅ Signal détecté dans le message:', content.substring(0, 200));
          return true;
        }
        return false;
      });

      if (hasSignal) {
        console.log('🎉 Signal GENERATE_TASKS détecté ! Affichage du bouton de finalisation.');
        setShouldCheckForSignal(false); // Arrêter de vérifier
        setShowFinalization(true); // Afficher l'interface de finalisation
      }
    } catch (err) {
      console.error('Error checking for signal:', err);
    } finally {
      // Réinitialiser le flag pour permettre les vérifications futures
      isProcessingSignal.current = false;
    }
  }, [projectId, shouldCheckForSignal]);

  // Suppression complète du setInterval - détection événementielle uniquement
  // La vérification du signal se fera uniquement après l'envoi de messages
  // Plus de boucle infinie, plus de saturation de la console

  const handleFinalize = async () => {
    console.log('CLIC DÉTECTÉ SUR LE BOUTON FINALISER');
    console.log('Valeur de projectId au moment du clic:', projectId);

    if (!projectId) {
      console.error('Aucun projectId disponible pour la finalisation');
      toast.error('Aucun projet à finaliser');
      return;
    }

    if (isFinalizing) {
      console.error('Finalisation déjà en cours, ignoré');
      toast.error('Finalisation déjà en cours');
      return;
    }

    console.log('ETAPE 1: Début de handleFinalize avec projectId:', projectId);
    setIsFinalizing(true);
    setShouldCheckForSignal(false); // Arrêter immédiatement la vérification du signal

    try {
      console.log('ETAPE 2: Appel à unifiedProjectService.previewFinalization');
      const preview = await unifiedProjectService.previewFinalization(projectId);
      console.log('ETAPE 3: Preview reçu:', preview);

      if (!preview) {
        throw new Error('Réponse de preview invalide ou vide');
      }

      // Ouvrir le modal de validation
      setFinalizationPreview(preview);
      setShowValidationModal(true);
      setIsFinalizing(false); // Réactiver le bouton
    } catch (err) {
      console.error('ETAPE ERREUR: Erreur lors de la génération du preview:', err);
      toast.error('Erreur lors de la génération du preview: ' + (err instanceof Error ? err.message : String(err)));
      setIsFinalizing(false);
      setShouldCheckForSignal(false); // S'assurer que la vérification est bien arrêtée
    }
  };

  // Nouvelle fonction pour gérer la finalisation complète après validation
  const handleValidationComplete = async () => {
    try {
      setShowValidationModal(false);

      // Attendre un peu et rediriger vers le projet
      setTimeout(() => {
        if (projectId) {
          console.log('Redirection vers /projects/' + projectId);
          navigate(`/projects/${projectId}`);
        }
      }, 1000);
    } catch (error) {
      console.error('Erreur lors de la finalisation:', error);
      toast.error('Erreur lors de la finalisation');
    }
  };

  return (
    <div className="min-h-screen bg-paper">
      <Navbar />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-8">
          {isLoading && (
            <div className="flex items-center justify-center h-96">
              <div className="text-center">
                <Loader size="lg" />
                <p className="text-ink-soft">Démarrage du dialogue...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center justify-center h-96">
              <div className="bg-danger/5 border border-danger/30 rounded-none p-6 max-w-md">
                <h3 className="text-danger font-semibold mb-2">Erreur</h3>
                <p className="text-danger mb-4">{error}</p>
                <button
                  onClick={handleStartChat}
                  className="bg-danger text-white px-4 py-2 rounded hover:opacity-90 hover:bg-danger transition-colors"
                >
                  Réessayer
                </button>
              </div>
            </div>
          )}

          {/* Affichage du résultat de finalisation */}
          {finalizationResult && (
            <div className="max-w-4xl mx-auto">
              <div className="bg-paper-card rounded-2xl shadow-lg p-8">
                <div className="text-center mb-6">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-success/10 rounded-full mb-4">
                    <CheckCircle className="w-10 h-10 text-success" />
                  </div>
                  <h2 className="text-3xl font-bold text-ink mb-2">
                    {finalizationResult.project_name}
                  </h2>
                  <p className="text-ink-soft mb-4">{finalizationResult.project_description}</p>
                  <div className="inline-flex items-center gap-2 px-4 py-2 bg-accent-wash text-accent-deep rounded-full">
                    <Sparkles className="w-4 h-4" />
                    <span className="font-semibold">{finalizationResult.tasks_count} tâches générées</span>
                  </div>
                </div>

                <div className="space-y-3 mb-6 max-h-96 overflow-y-auto">
                  {finalizationResult.tasks.map((task: TaskGenerated) => (
                    <div key={task.id} className="bg-paper rounded-none p-4 border border-ink-line">
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-semibold text-ink">{task.title}</h4>
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          task.priority === 'P1' ? 'bg-danger/10 text-danger' :
                          task.priority === 'P2' ? 'bg-warning/10 text-warning' :
                          'bg-info/10 text-info'
                        }`}>
                          {task.priority}
                        </span>
                      </div>
                      <p className="text-sm text-ink-soft line-clamp-2">{task.description}</p>
                    </div>
                  ))}
                </div>

                <p className="text-center text-sm text-ink-faint">
                  Redirection vers le projet dans quelques secondes...
                </p>
              </div>
            </div>
          )}

          {/* Interface de démarrage si le chat n'a pas encore démarré */}
          {!isLoading && !error && !isChatStarted && !finalizationResult && (
            <div className="max-w-6xl mx-auto">
              <div className="bg-paper-card rounded-none shadow-lg p-12 text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-accent-wash rounded-full mb-6">
                  <Play className="w-8 h-8 text-accent" />
                </div>
                <h2 className="text-2xl font-bold text-ink mb-4">Prêt à démarrer votre projet ?</h2>
                <p className="text-ink-soft mb-8 max-w-md mx-auto">
                  Cliquez sur le bouton ci-dessous pour lancer le dialogue d'idéation et créer votre projet
                </p>
                <button
                  onClick={handleStartChat}
                  disabled={isLoading}
                  className="flex items-center justify-center gap-2 px-6 py-3 bg-accent text-white rounded-none hover:bg-accent-deep transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Sparkles className="w-5 h-5" />
                  Lancer l'idéation
                </button>
              </div>
            </div>
          )}

          {/* Contenu principal avec le chat */}
          {!isLoading && !error && isChatStarted && projectId && !finalizationResult && (
            <div className="max-w-6xl mx-auto">
              {/* Header avec titre */}
              <div className="mb-6">
                <h1 className="text-3xl font-bold text-ink">Nouveau Projet</h1>
                <p className="text-ink-soft mt-2">
                  Dialoguez avec l'IA pour définir votre projet et générer automatiquement les tâches
                </p>
              </div>

              {/* Notification de génération de tâches */}
              {showFinalization && !isFinalizing && (
                <div className="bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-none px-6 py-4 shadow-lg mb-6" style={{ position: 'relative', zIndex: 10 }}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Sparkles className="w-6 h-6" />
                      <div>
                        <p className="font-semibold">Votre vision est claire !</p>
                        <p className="text-sm text-white/80">Prêt à générer automatiquement le plan de tâches ?</p>
                      </div>
                    </div>
                    <button
                      onClick={handleFinalize}
                      className="bg-paper-card text-accent px-6 py-2 rounded-none font-semibold hover:bg-accent-wash transition-colors shadow-md"
                      style={{ zIndex: 20, cursor: 'pointer' }}
                      title="Finaliser le projet"
                    >
                      Générer les tâches
                    </button>
                  </div>
                </div>
              )}

              {/* Loading de finalisation */}
              {isFinalizing && (
                <div className="bg-accent text-white rounded-none px-6 py-4 mb-6">
                  <div className="flex items-center justify-center gap-3">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <p className="font-semibold">Génération des tâches en cours...</p>
                  </div>
                </div>
              )}

              {/* Chat */}
              <div className="bg-paper-card rounded-none shadow-lg">
                <IdeationChat projectId={projectId} onMessageComplete={checkForSignal} />
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Modal de validation */}
      <FinalizationValidationModal
        isOpen={showValidationModal}
        onClose={() => setShowValidationModal(false)}
        preview={finalizationPreview}
        projectId={projectId || 0}
        onFinalize={handleValidationComplete}
      />
    </div>
  );
};

export default UnifiedProjectChat;
