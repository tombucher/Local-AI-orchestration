/**
 * Bouton pour demander une analyse IA des conseils de maturité
 */

import { useState } from 'react';
import { Sparkles, Lightbulb, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

interface MaturityAnalysis {
  maturity_score: number;
  criteria_analysis: {
    dependencies: {
      score: number;
      details: string;
      percentage: number;
    };
    descriptions: {
      score: number;
      details: string;
      percentage: number;
    };
    deadlines: {
      score: number;
      details: string;
      percentage: number;
    };
    critical_path: {
      score: number;
      details: string;
      percentage: number;
    };
  };
  improvement_suggestions: string[];
}

interface AIAnalysisButtonProps {
  projectId: number;
  onAnalysisComplete: (analysis: MaturityAnalysis) => void;
}

export const AIAnalysisButton = ({ projectId, onAnalysisComplete }: AIAnalysisButtonProps) => {
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<MaturityAnalysis | null>(null);

  const handleAIAnalysis = async () => {
    try {
      setLoading(true);
      setShowModal(false);

      const response = await api.get<MaturityAnalysis>(`/projects/${projectId}/maturity-analysis`);
      const data = response.data;

      setAnalysisResult(data);
      onAnalysisComplete(data);
      setShowModal(true);

    } catch (err) {
      console.error('Error fetching AI analysis:', err);
      toast.error('Erreur lors de l\'analyse IA');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        onClick={handleAIAnalysis}
        disabled={loading}
        className="flex items-center gap-2 px-4 py-2 text-white bg-primary rounded-none hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Analyse en cours...
          </>
        ) : (
          <>
            <Sparkles className="w-4 h-4" />
            Conseils de Maturité IA
          </>
        )}
      </button>

      {showModal && analysisResult && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-paper-card rounded-none shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-ink flex items-center gap-2">
                  <Lightbulb className="w-6 h-6 text-primary" />
                  Analyse IA de la Maturité
                </h2>
                <button
                  onClick={() => setShowModal(false)}
                  className="text-ink-faint hover:text-ink-soft transition-colors"
                >
                  <span className="text-2xl">&times;</span>
                </button>
              </div>

              {/* Score global */}
              <div className="bg-paper rounded-none p-4 mb-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-ink-soft mb-1">Score de Maturité Global</p>
                    <p className="text-3xl font-bold text-primary">{analysisResult.maturity_score}/100</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      analysisResult.maturity_score >= 80 ? 'bg-success/10 text-success' :
                      analysisResult.maturity_score >= 60 ? 'bg-warning/10 text-warning' :
                      analysisResult.maturity_score >= 40 ? 'bg-warning/10 text-warning' :
                      'bg-danger/10 text-danger'
                    }`}>
                      {analysisResult.maturity_score >= 80 ? 'Excellent' :
                       analysisResult.maturity_score >= 60 ? 'Bon' :
                       analysisResult.maturity_score >= 40 ? 'Moyen' : 'À améliorer'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Analyse par critère */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-ink mb-3">Analyse détaillée</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Object.entries(analysisResult.criteria_analysis).map(([criteria, data]) => (
                    <div key={criteria} className="p-3 border border-ink-line rounded-none">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-ink-soft capitalize">
                          {criteria.replace('_', ' ')}
                        </span>
                        <span className={`text-sm font-bold ${
                          data.score >= 80 ? 'text-success' :
                          data.score >= 60 ? 'text-warning' :
                          data.score >= 40 ? 'text-warning' : 'text-danger'
                        }`}>
                          {data.score.toFixed(1)}%
                        </span>
                      </div>
                      <p className="text-xs text-ink-faint mb-1">{data.details}</p>
                      <div className="w-full bg-paper-warm rounded-full h-1">
                        <div
                          className={`h-1 rounded-full ${
                            data.score >= 80 ? 'bg-success' :
                            data.score >= 60 ? 'bg-warning' :
                            data.score >= 40 ? 'bg-warning' : 'bg-danger'
                          }`}
                          style={{ width: `${data.score}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Conseils d'amélioration */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-ink mb-3">Conseils d'amélioration</h3>
                <div className="space-y-3">
                  {analysisResult.improvement_suggestions.map((suggestion: string, index: number) => (
                    <div key={index} className="p-3 bg-info/5 border border-info/20 rounded-none flex items-start gap-3">
                      <Lightbulb className="w-5 h-5 text-info mt-0.5 flex-shrink-0" />
                      <p className="text-sm text-ink">{suggestion}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Actions recommandées */}
              <div className="bg-warning/5 rounded-none p-4">
                <h3 className="text-lg font-semibold text-ink mb-3">Actions recommandées</h3>
                <p className="text-sm text-ink-soft">
                  Pour améliorer votre score de maturité, concentrez-vous sur les critères avec les scores les plus bas.
                  Ajoutez des dépendances entre tâches, complétez les descriptions et estimez les durées pour chaque tâche.
                </p>
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-primary text-white rounded-none hover:bg-primary/90 transition-colors"
                >
                  Fermer
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};