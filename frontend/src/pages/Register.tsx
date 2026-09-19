/**
 * Page Register
 * - Formulaire email + password + full_name
 * - Validation avec React Hook Form + Zod
 * - Auto-login après succès → redirect /dashboard
 */

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Link, useNavigate } from 'react-router-dom';
import { UserPlus } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import { APP_NAME } from '../utils/constants';

// Schéma de validation Zod
const registerSchema = z.object({
  email: z.string().email('Email invalide'),
  password: z.string().min(6, 'Minimum 6 caractères'),
  full_name: z.string().min(2, 'Nom requis (minimum 2 caractères)'),
});

type RegisterFormData = z.infer<typeof registerSchema>;

export const Register = () => {
  const navigate = useNavigate();
  const { register: registerUser, isAuthenticated, isLoading, error, clearError } = useAuthStore();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  // Redirect si authentifié (auto-login après inscription)
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  // Clear error au montage
  useEffect(() => {
    clearError();
  }, [clearError]);

  const onSubmit = async (data: RegisterFormData) => {
    try {
      await registerUser(data);
      // Navigation gérée par useEffect (auto-login)
    } catch (err) {
      // Erreur gérée par le store
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <div className="mx-auto h-12 w-12 bg-secondary rounded-none flex items-center justify-center">
            <UserPlus className="h-6 w-6 text-white" />
          </div>
          <h2 className="mt-6 text-3xl font-bold text-ink">{APP_NAME}</h2>
          <p className="mt-2 text-sm text-ink-soft">
            Créez votre compte gratuitement
          </p>
        </div>

        {/* Formulaire */}
        <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-6">
          {/* Erreur API */}
          {error && (
            <div className="bg-danger/10 border border-danger/20 text-danger px-4 py-3 rounded-none text-sm">
              {error}
            </div>
          )}

          <div className="space-y-4">
            {/* Nom complet */}
            <div>
              <label
                htmlFor="full_name"
                className="block text-sm font-medium text-ink-soft mb-1"
              >
                Nom complet
              </label>
              <input
                {...register('full_name')}
                id="full_name"
                type="text"
                autoComplete="name"
                className="appearance-none relative block w-full px-3 py-2 border border-ink-line rounded-none placeholder-gray-400 text-ink focus:outline-none focus:ring-2 focus:ring-secondary focus:border-transparent sm:text-sm"
                placeholder="Jean Dupont"
              />
              {errors.full_name && (
                <p className="mt-1 text-sm text-danger">
                  {errors.full_name.message}
                </p>
              )}
            </div>

            {/* Email */}
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-ink-soft mb-1"
              >
                Email
              </label>
              <input
                {...register('email')}
                id="email"
                type="email"
                autoComplete="email"
                className="appearance-none relative block w-full px-3 py-2 border border-ink-line rounded-none placeholder-gray-400 text-ink focus:outline-none focus:ring-2 focus:ring-secondary focus:border-transparent sm:text-sm"
                placeholder="votre@email.com"
              />
              {errors.email && (
                <p className="mt-1 text-sm text-danger">{errors.email.message}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-ink-soft mb-1"
              >
                Mot de passe
              </label>
              <input
                {...register('password')}
                id="password"
                type="password"
                autoComplete="new-password"
                className="appearance-none relative block w-full px-3 py-2 border border-ink-line rounded-none placeholder-gray-400 text-ink focus:outline-none focus:ring-2 focus:ring-secondary focus:border-transparent sm:text-sm"
                placeholder="••••••••"
              />
              {errors.password && (
                <p className="mt-1 text-sm text-danger">
                  {errors.password.message}
                </p>
              )}
            </div>
          </div>

          {/* Bouton Submit */}
          <button
            type="submit"
            disabled={isLoading}
            className="group relative w-full flex justify-center py-2.5 px-4 border border-transparent text-sm font-medium rounded-none text-white bg-secondary hover:bg-secondary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Inscription...' : 'Créer mon compte'}
          </button>

          {/* Lien Login */}
          <div className="text-center">
            <p className="text-sm text-ink-soft">
              Déjà un compte ?{' '}
              <Link
                to="/login"
                className="font-medium text-secondary hover:text-secondary/80"
              >
                Se connecter
              </Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
};
