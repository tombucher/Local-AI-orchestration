/**
 * Composant d'affichage des indicateurs de maturité détaillés
 */

import { useState, useEffect } from 'react';
import { BarChart2, FileText, Calendar, GitBranch, Lightbulb } from 'lucide-react';
import { StatsCard } from '../StatsCard';
import api from '../../services/api';
import Loader from '../ui/Loader';

interface MaturityIndicatorsProps {
  projectId: number;
  maturityScore: number;
}

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

export const MaturityIndicators = ({ projectId, maturityScore }: MaturityIndicatorsProps) => {
  const [analysis, setAnalysis] = useState<MaturityAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);

  useEffect(() => {
    const fetchMaturityAnalysis = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await api.get<MaturityAnalysis>(`/projects/${projectId}/maturity-analysis`);
        setAnalysis(response.data);

      } catch (err) {
        console.error('Error fetching maturity analysis:', err);
        setError('Erreur lors du chargement de l\'analyse de maturité');
      } finally {
        setLoading(false);
      }
    };

    fetchMaturityAnalysis();
  }, [projectId]);

  const getCriteriaColor = (score: number) => {
    if (score >= 80) return 'green';
    if (score >= 60) return 'yellow';
    if (score >= 40) return 'orange';
    return 'red';
  };

  const getCriteriaIcon = (criteria: string) => {
    switch (criteria) {
      case 'dependencies': return GitBranch;
      case 'descriptions': return FileText;
      case 'deadlines': return Calendar;
      case 'critical_path': return BarChart2;
      default: return Lightbulb;
    }
  };

  if (loading) {
    return (
      <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-6">
        <h2 className="text-lg font-semibold text-ink mb-4">Indicateurs de Maturité</h2>
        <div className="text-center py-8">
          <Loader size="lg" />
          <p className="text-sm text-ink-faint mt-2">Analyse des indicateurs en cours...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-6">
        <h2 className="text-lg font-semibold text-ink mb-4">Indicateurs de Maturité</h2>
        <div className="text-center py-8 text-danger">
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-6">
        <h2 className="text-lg font-semibold text-ink mb-4">Indicateurs de Maturité</h2>
        <div className="text-center py-8 text-ink-faint">
          <p>Aucune analyse de maturité disponible</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-paper-card rounded-none shadow-card border border-ink-line p-6">
      <h2 className="text-lg font-semibold text-ink mb-4">Indicateurs de Maturité</h2>

      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <StatsCard
          title="Score Global"
          value={`${maturityScore}/100`}
          icon={BarChart2}
          color={getCriteriaColor(maturityScore)}
        />
        {analysis.criteria_analysis && (
          <>
            <StatsCard
              title="Dépendances"
              value={`${analysis.criteria_analysis.dependencies.score.toFixed(1)}%`}
              icon={GitBranch}
              color={getCriteriaColor(analysis.criteria_analysis.dependencies.score)}
            />
            <StatsCard
              title="Descriptions"
              value={`${analysis.criteria_analysis.descriptions.score.toFixed(1)}%`}
              icon={FileText}
              color={getCriteriaColor(analysis.criteria_analysis.descriptions.score)}
            />
            <StatsCard
              title="Durées"
              value={`${analysis.criteria_analysis.deadlines.score.toFixed(1)}%`}
              icon={Calendar}
              color={getCriteriaColor(analysis.criteria_analysis.deadlines.score)}
            />
          </>
        )}
      </div>

      {/* Detailed criteria analysis */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {analysis.criteria_analysis && Object.entries(analysis.criteria_analysis).map(([criteria, data]) => {
          const Icon = getCriteriaIcon(criteria);
          const color = getCriteriaColor(data.score);

          return (
            <div key={criteria} className="p-4 border border-ink-line rounded-none">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className={`p-2 rounded-none ${color === 'green' ? 'bg-success/10' : color === 'yellow' ? 'bg-warning/10' : color === 'orange' ? 'bg-warning/10' : 'bg-danger/10'}`}>
                    <Icon className={`w-5 h-5 ${color === 'green' ? 'text-success' : color === 'yellow' ? 'text-warning' : color === 'orange' ? 'text-warning' : 'text-danger'}`} />
                  </div>
                  <div>
                    <h3 className="font-medium text-ink capitalize">{criteria.replace('_', ' ')}</h3>
                    <p className="text-sm text-ink-faint">Poids: {criteria === 'dependencies' || criteria === 'critical_path' ? '30%' : '20%'}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`text-2xl font-bold ${color === 'green' ? 'text-success' : color === 'yellow' ? 'text-warning' : color === 'orange' ? 'text-warning' : 'text-danger'}`}>
                    {data.score.toFixed(1)}%
                  </p>
                </div>
              </div>

              <div className="mb-3">
                <p className="text-sm text-ink-soft mb-1">Détails:</p>
                <p className="text-sm text-ink">{data.details}</p>
              </div>

              <div className="w-full bg-paper-warm rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${color === 'green' ? 'bg-success' : color === 'yellow' ? 'bg-warning' : color === 'orange' ? 'bg-warning' : 'bg-danger'}`}
                  style={{ width: `${data.score}%` }}
                ></div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Improvement suggestions */}
      {analysis.improvement_suggestions && analysis.improvement_suggestions.length > 0 && (
        <div className="border-t border-ink-line pt-6">
          <button
            onClick={() => setShowSuggestions(!showSuggestions)}
            className="flex items-center gap-2 text-primary hover:text-primary/80 transition-colors"
          >
            <Lightbulb className="w-5 h-5" />
            <span className="font-medium">
              {showSuggestions ? 'Masquer les conseils' : 'Afficher les conseils d\'amélioration'}
            </span>
          </button>

          {showSuggestions && (
            <div className="mt-4 space-y-3">
              {analysis.improvement_suggestions.map((suggestion, index) => (
                <div key={index} className="p-3 bg-info/5 border border-info/20 rounded-none">
                  <p className="text-sm text-ink">{suggestion}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};