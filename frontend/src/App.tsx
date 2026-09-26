/**
 * App.tsx : Routing principal
 * - Routes publiques : /login, /register
 * - Routes protégées : /dashboard, /projects
 * - Redirect / selon état auth
 */

import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { ProjectsList } from './pages/Projects/ProjectsList';
import { ProjectDetail } from './pages/Projects/ProjectDetail';
import { ProjectForm } from './pages/Projects/ProjectForm';
import { ProjectAnalysisPage } from './pages/Projects/ProjectAnalysis';
import { ProjectMoodboard } from './pages/Projects/ProjectMoodboard';
import UnifiedProjectChat from './components/UnifiedProjectChat';
import { TasksList } from './pages/Tasks/TasksList';
import { TaskDetail } from './pages/Tasks/TaskDetail';
import { TaskForm } from './pages/Tasks/TaskForm';
import { Settings } from './pages/Settings';
import { BriefingNotifier } from './components/Layout/BriefingNotifier';

function App() {
  const { isAuthenticated, checkAuth } = useAuthStore();

  // Vérifier auth au chargement de l'app
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <BrowserRouter>
      <BriefingNotifier />
      <Routes>
        {/* Route racine : redirect selon auth */}
        <Route
          path="/"
          element={
            isAuthenticated ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />

        {/* Routes publiques */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Routes protégées */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />

        {/* Routes Projets */}
        <Route
          path="/projects"
          element={
            <ProtectedRoute>
              <ProjectsList />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/new"
          element={
            <ProtectedRoute>
              <UnifiedProjectChat />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/new/form"
          element={
            <ProtectedRoute>
              <ProjectForm />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/:id"
          element={
            <ProtectedRoute>
              <ProjectDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/:id/edit"
          element={
            <ProtectedRoute>
              <ProjectForm />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/:id/analyze"
          element={
            <ProtectedRoute>
              <ProjectAnalysisPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/projects/:id/moodboard"
          element={
            <ProtectedRoute>
              <ProjectMoodboard />
            </ProtectedRoute>
          }
        />

        {/* Routes Tâches */}
        <Route
          path="/tasks"
          element={
            <ProtectedRoute>
              <TasksList />
            </ProtectedRoute>
          }
        />
        <Route
          path="/tasks/new"
          element={
            <ProtectedRoute>
              <TaskForm />
            </ProtectedRoute>
          }
        />
        <Route
          path="/tasks/:id"
          element={
            <ProtectedRoute>
              <TaskDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/tasks/:id/edit"
          element={
            <ProtectedRoute>
              <TaskForm />
            </ProtectedRoute>
          }
        />

        {/* Route Settings */}
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <Settings />
            </ProtectedRoute>
          }
        />

        {/* 404 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
