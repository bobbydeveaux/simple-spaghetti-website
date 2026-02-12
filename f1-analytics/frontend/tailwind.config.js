/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'f1-red': '#E10600',
        'f1-dark': '#15151E',
        'f1-gray': '#38383F',
        'f1-light-gray': '#A9A9A9',
        'redbull': '#0600EF',
        'ferrari': '#DC143C',
        'mercedes': '#00D2BE',
        'mclaren': '#FF8700',
        'alpine': '#0090FF',
        'alphatauri': '#2B4562',
        'astonmartin': '#006F62',
        'williams': '#005AFF',
        'alfaromeo': '#900000',
        'haas': '#FFFFFF',
      },
      fontFamily: {
        'f1': ['F1 Regular', 'Arial', 'sans-serif'],
        'f1-bold': ['F1 Bold', 'Arial Black', 'sans-serif'],
      },
      animation: {
        'spin-slow': 'spin 3s linear infinite',
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-in': 'bounceIn 0.6s ease-out',
      },
      keyframes: {
        bounceIn: {
          '0%': {
            opacity: '0',
            transform: 'scale(0.3)',
          },
          '50%': {
            opacity: '0.9',
            transform: 'scale(1.05)',
          },
          '80%': {
            opacity: '1',
            transform: 'scale(0.9)',
          },
          '100%': {
            opacity: '1',
            transform: 'scale(1)',
          },
        },
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
      screens: {
        '3xl': '1600px',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}