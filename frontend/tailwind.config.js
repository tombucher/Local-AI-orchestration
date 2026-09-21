import typography from '@tailwindcss/typography'

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // Design system « journal d'atelier » : papier chaud, encre dense,
      // un seul accent vermillon. Voir index.css pour les styles de base.
      colors: {
        paper: {
          DEFAULT: '#FAF7F2',   // fond principal
          warm: '#F4EFE6',      // fonds secondaires / hover
          card: '#FFFEFB',      // surfaces de cartes
        },
        ink: {
          DEFAULT: '#1C1917',   // texte principal
          soft: '#44403C',      // texte secondaire
          faint: '#78716C',     // texte tertiaire / méta
          line: '#E0D9CD',      // filets, bordures
        },
        accent: {
          DEFAULT: '#E2492F',   // vermillon — actions, liens, accents
          deep: '#B83A24',      // hover
          wash: '#FBEAE5',      // fonds teintés accent
        },
        highlight: '#F5D547',   // jaune surligneur
        // Statuts désaturés pour rester dans l'ambiance papier
        success: '#4D7C5F',
        danger: '#C0392B',
        warning: '#C28A2D',
        info: '#4A6FA5',
        // Compat : ancien primary → vermillon (le temps de la migration)
        primary: '#E2492F',
        secondary: '#4A6FA5',
      },
      fontFamily: {
        display: ['"Fraunces Variable"', 'Georgia', 'serif'],
        sans: ['"Archivo Variable"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(28, 25, 23, 0.06), 0 2px 8px rgba(28, 25, 23, 0.04)',
        lifted: '0 2px 4px rgba(28, 25, 23, 0.08), 0 8px 24px rgba(28, 25, 23, 0.08)',
      },
      keyframes: {
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'pop': {
          '0%': { transform: 'scale(1)' },
          '40%': { transform: 'scale(1.18)' },
          '100%': { transform: 'scale(1)' },
        },
        // Barre de progression sans pourcentage connu : un va-et-vient qui dit
        // « ça travaille » sans mentir sur l'avancement réel.
        'indeterminate': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(300%)' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.45s ease-out both',
        'pop': 'pop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)',
        'indeterminate': 'indeterminate 1.6s ease-in-out infinite',
      },
    },
  },
  plugins: [typography],
}
