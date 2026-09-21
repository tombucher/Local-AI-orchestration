/**
 * Dashboard — « la une » du journal d'atelier
 * - Masthead : édition du jour, stats en manchette
 * - Lead story : briefing quotidien (résumé + top priorités)
 * - Colonnes : projets en cours, tâches à valider
 */

import { useEffect, useState } from 'react';
import { FolderKanban, CheckSquare, Plus, Eye, AlertTriangle, ArrowRight, Flame, Sparkles, CalendarClock } from 'lucide-react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useProjectsStore } from '../stores/projectsStore';
import { useTasksStore } from '../stores/tasksStore';
import { Navbar } from '../components/Layout/Navbar';
import { Sidebar } from '../components/Layout/Sidebar';
import { ProjectCard } from '../components/ProjectCard';
import { ServiceStatus } from '../components/ServiceStatus';
import { DailyReport, SuggestedTask } from '../types/daily-report.types';
import toast from 'react-hot-toast';
import { TaskStatus } from '../types/task.types';
import type { VeilleResult } from '../types/task.types';
import { api } from '../services/api';

/** Date longue façon presse : « jeudi 12 juin 2026 » */
const editionDate = new Intl.DateTimeFormat('fr-FR', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
}).format(new Date());

export const Dashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { projects, fetchProjects } = useProjectsStore();
  const { tasks, fetchTasks } = useTasksStore();
  const [dailyReport, setDailyReport] = useState<DailyReport | null>(null);
  const [deadlines, setDeadlines] = useState<VeilleResult[]>([]);

  useEffect(() => {
    fetchProjects();
    fetchTasks();

    // Récupérer le rapport quotidien (silencieux : absent = normal le 1er jour)
    api
      .get('/reports/daily/latest', { silentError: true })
      .then((response) => {
        if (response.data) setDailyReport(response.data);
      })
      .catch(() => {});

    // Échéances d'appels à projets à venir
    api
      .get<{ items: VeilleResult[] }>('/tasks/veille-deadlines', { silentError: true })
      .then((r) => setDeadlines(r.data.items))
      .catch(() => {});
  }, [fetchProjects, fetchTasks]);

  const projectsArray = Array.isArray(projects) ? projects : [];
  const tasksArray = Array.isArray(tasks) ? tasks : [];

  const recentProjects = projectsArray.slice(0, 4);
  const tasksToReview = tasksArray.filter((t) => t.status === TaskStatus.MANUAL_REVIEW).slice(0, 5);
  const completedToday = dailyReport?.completed_today ?? 0;
  const criticalProjects = dailyReport?.projects.filter((p) => p.health_status === 'critical') ?? [];

  const firstName = user?.full_name?.split(' ')[0] ?? '';

  // Série : jours consécutifs (en remontant depuis aujourd'hui) avec ≥1 tâche terminée
  const streak = (() => {
    const days = new Set(
      tasksArray
        .filter((t) => t.completed_at)
        .map((t) => new Date(t.completed_at as string).toDateString())
    );
    let count = 0;
    const cursor = new Date();
    while (days.has(cursor.toDateString())) {
      count += 1;
      cursor.setDate(cursor.getDate() - 1);
    }
    return count;
  })();

  // Projets avec une « prochaine action évidente » fournie par le briefing
  const nextActions = (dailyReport?.projects ?? []).filter((p) => p.next_obvious_action);
  // Projets stagnants avec suggestions de relance
  const stagnantProjects = (dailyReport?.projects ?? []).filter(
    (p) => p.is_stagnant && (p.suggested_tasks?.length ?? 0) > 0
  );
  const [creatingSuggestion, setCreatingSuggestion] = useState<string | null>(null);

  const createSuggestedTask = async (projectId: number, suggestion: SuggestedTask) => {
    setCreatingSuggestion(`${projectId}-${suggestion.title}`);
    try {
      await api.post(`/projects/${projectId}/create-suggested-tasks`, {
        tasks: [suggestion],
        veille: [],
      });
      toast.success(`Tâche créée : « ${suggestion.title} »`);
      fetchTasks();
    } catch {
      // Erreur déjà toastée par l'intercepteur API
    } finally {
      setCreatingSuggestion(null);
    }
  };

  return (
    <div className="min-h-screen bg-paper">
      <Navbar />

      <div className="flex">
        <Sidebar />

        <main className="flex-1 min-w-0 p-6 lg:p-10 max-w-6xl">
          {/* ===== Masthead ===== */}
          <header className="mb-8 animate-fade-up">
            <div className="flex items-baseline justify-between gap-4 flex-wrap">
              <p className="kicker">Édition du {editionDate}</p>
              <p className="text-xs text-ink-faint figures">
                {projectsArray.length} projet{projectsArray.length > 1 ? 's' : ''} ·{' '}
                {tasksArray.length} tâche{tasksArray.length > 1 ? 's' : ''}
                {completedToday > 0 && (
                  <span className="text-success font-medium"> · {completedToday} terminée{completedToday > 1 ? 's' : ''} aujourd'hui</span>
                )}
                {streak >= 2 && (
                  <span className="text-accent font-medium"> · 🔥 {streak} jours d'affilée</span>
                )}
              </p>
            </div>
            <h1 className="font-display text-4xl lg:text-5xl text-ink mt-2 tracking-tight">
              {firstName ? `À l'atelier, ${firstName}.` : "À l'atelier."}
            </h1>
            <div className="rule-strong mt-4" />
          </header>

          {/* ===== Lead story : briefing du jour ===== */}
          {dailyReport && (
            <section className="mb-10 animate-fade-up" style={{ animationDelay: '80ms' }}>
              <p className="kicker mb-2">Le briefing du matin</p>
              <p className="standfirst max-w-3xl">{dailyReport.summary}</p>

              {dailyReport.top_priorities.length > 0 && (
                <ol className="mt-5 space-y-2 max-w-2xl">
                  {dailyReport.top_priorities.slice(0, 3).map((priority, i) => (
                    <li key={i} className="flex gap-4 items-baseline">
                      <span className="font-display text-2xl text-accent figures leading-none">
                        {i + 1}.
                      </span>
                      <span className="text-sm text-ink-soft leading-relaxed">{priority}</span>
                    </li>
                  ))}
                </ol>
              )}

              {nextActions.length > 0 && (
                <div className="mt-6 max-w-2xl space-y-2">
                  <p className="kicker">La prochaine action évidente</p>
                  {nextActions.map((p) => (
                    <Link
                      key={p.project_id}
                      to={`/projects/${p.project_id}`}
                      className="group flex items-start gap-3 border border-ink-line bg-paper-card px-4 py-3 hover:border-accent transition-colors"
                    >
                      <ArrowRight className="w-4 h-4 text-accent mt-0.5 shrink-0 group-hover:translate-x-0.5 transition-transform" />
                      <span className="text-sm">
                        <span className="font-semibold text-ink">{p.project_name}</span>
                        <span className="text-ink-soft"> — {p.next_obvious_action}</span>
                      </span>
                    </Link>
                  ))}
                </div>
              )}

              {stagnantProjects.length > 0 && (
                <div className="mt-6 max-w-2xl space-y-3">
                  <p className="kicker flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" /> Pour relancer la machine
                  </p>
                  {stagnantProjects.map((p) => (
                    <div key={p.project_id} className="border border-ink-line bg-paper-card p-4">
                      <p className="text-sm font-semibold text-ink mb-2 flex items-center gap-2">
                        <Flame className="w-4 h-4 text-warning" />
                        {p.project_name} dort depuis un moment — quelques idées :
                      </p>
                      <ul className="space-y-2">
                        {(p.suggested_tasks ?? []).map((sg) => (
                          <li key={sg.title} className="flex items-center justify-between gap-3">
                            <span className="text-sm text-ink-soft">{sg.title}</span>
                            <button
                              onClick={() => createSuggestedTask(p.project_id, sg)}
                              disabled={creatingSuggestion === `${p.project_id}-${sg.title}`}
                              className="shrink-0 text-xs font-semibold uppercase tracking-wide text-accent hover:text-accent-deep disabled:opacity-40 transition-colors"
                            >
                              {creatingSuggestion === `${p.project_id}-${sg.title}` ? 'Création…' : '+ Créer'}
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              )}

              {criticalProjects.length > 0 && (
                <div className="mt-4 inline-flex items-center gap-2 border border-danger/40 bg-danger/5 px-3 py-1.5 text-sm text-danger">
                  <AlertTriangle className="w-4 h-4" />
                  {criticalProjects.length} projet{criticalProjects.length > 1 ? 's' : ''} en état critique
                </div>
              )}
            </section>
          )}

          {/* ===== Grille magazine ===== */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Colonne principale : projets */}
            <section className="lg:col-span-2 animate-fade-up" style={{ animationDelay: '160ms' }}>
              <div className="flex items-end justify-between mb-4 pb-2 rule">
                <h2 className="font-display text-2xl text-ink">Projets en cours</h2>
                <button
                  onClick={() => navigate('/projects/new')}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-accent text-white hover:bg-accent-deep transition-colors text-xs font-semibold uppercase tracking-wide"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Nouveau
                </button>
              </div>

              {recentProjects.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  {recentProjects.map((project) => (
                    <ProjectCard
                      key={project.id}
                      project={project}
                      onView={(id) => navigate(`/projects/${id}`)}
                    />
                  ))}
                </div>
              ) : (
                <div className="border border-dashed border-ink-line p-12 text-center">
                  <FolderKanban className="w-10 h-10 mx-auto mb-3 text-ink-faint" />
                  <p className="text-ink-soft mb-4">Aucun projet pour le moment — et si on lançait quelque chose ?</p>
                  <button
                    onClick={() => navigate('/projects/new')}
                    className="px-4 py-2 bg-accent text-white hover:bg-accent-deep transition-colors font-medium text-sm uppercase tracking-wide"
                  >
                    Créer votre premier projet
                  </button>
                </div>
              )}

              {projectsArray.length > 4 && (
                <Link to="/projects" className="inline-block mt-4 text-sm text-accent hover:text-accent-deep font-medium">
                  Tous les projets ({projectsArray.length}) →
                </Link>
              )}
            </section>

            {/* Colonne latérale : à valider + service */}
            <aside className="space-y-6 animate-fade-up" style={{ animationDelay: '240ms' }}>
              {/* À valider */}
              <div className="bg-paper-card border border-ink-line border-t-2 border-t-highlight shadow-card p-5">
                <div className="flex items-center gap-2 mb-3 pb-2 rule">
                  <Eye className="w-4 h-4 text-ink-soft" />
                  <h2 className="font-display text-lg text-ink">À valider</h2>
                  {tasksToReview.length > 0 && (
                    <span className="ml-auto font-mono text-xs text-ink-faint figures">{tasksToReview.length}</span>
                  )}
                </div>
                {tasksToReview.length > 0 ? (
                  <ul className="space-y-2.5">
                    {tasksToReview.map((task) => (
                      <li key={task.id}>
                        <Link
                          to={`/tasks/${task.id}`}
                          className="block text-sm text-ink-soft hover:text-accent transition-colors leading-snug"
                        >
                          {task.title}
                          <span className="block text-[11px] text-ink-faint mt-0.5">{task.project_name}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-ink-faint flex items-center gap-2">
                    <CheckSquare className="w-4 h-4" /> Rien en attente — la voie est libre.
                  </p>
                )}
              </div>

              {deadlines.length > 0 && (
                <div className="bg-paper-card border border-ink-line border-t-2 border-t-accent shadow-card p-5">
                  <div className="flex items-center gap-2 mb-3 pb-2 rule">
                    <CalendarClock className="w-4 h-4 text-accent" />
                    <h2 className="font-display text-lg text-ink">Échéances à venir</h2>
                  </div>
                  <ul className="space-y-2.5">
                    {deadlines.map((d) => {
                      const days = Math.ceil(
                        (new Date(d.deadline as string).getTime() - Date.now()) / 86400000
                      );
                      return (
                        <li key={d.id}>
                          <a
                            href={d.url || '#'}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block text-sm text-ink-soft hover:text-accent transition-colors leading-snug"
                          >
                            {d.title}
                            <span
                              className={`block text-[11px] mt-0.5 figures font-medium ${
                                days <= 15 ? 'text-danger' : 'text-ink-faint'
                              }`}
                            >
                              {new Date(d.deadline as string).toLocaleDateString('fr-FR')} — dans {days} j
                            </span>
                          </a>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}

              <ServiceStatus />
            </aside>
          </div>
        </main>
      </div>
    </div>
  );
};
