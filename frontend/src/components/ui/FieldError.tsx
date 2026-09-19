/**
 * Affiche l'erreur de validation d'un champ de formulaire (react-hook-form + zod).
 * Utilisation : <FieldError error={errors.name} />
 */

import type { FieldError as RHFFieldError } from 'react-hook-form';

interface FieldErrorProps {
  error?: RHFFieldError | { message?: string };
}

export default function FieldError({ error }: FieldErrorProps) {
  if (!error?.message) return null;
  return (
    <p className="mt-1 text-sm text-danger" role="alert">
      {error.message}
    </p>
  );
}
