/**
 * Petite célébration quand une tâche passe à « terminée ».
 * Toast personnalisé avec animation pop (cf. tailwind animate-pop).
 */

import toast from 'react-hot-toast';

const MESSAGES = [
  'Et une de moins !',
  'Belle avancée.',
  'Ça progresse à l\'atelier.',
  'Encore une de pliée.',
  'Le projet avance, bravo.',
];

export function celebrateCompletion(taskTitle?: string) {
  const message = MESSAGES[Math.floor(Math.random() * MESSAGES.length)];
  toast.success(taskTitle ? `${message} — « ${taskTitle} »` : message, {
    icon: '🖋',
    duration: 3500,
    className: 'animate-pop',
    style: {
      background: '#1C1917',
      color: '#FAF7F2',
      borderRadius: '0',
      border: '1px solid #1C1917',
    },
  });
}
