/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './src/**/*.{js,jsx}',
    './src/popup/index.html',
    './src/options/index.html',
    './src/sidepanel/index.html',
  ],
  theme: {
    extend: {
      colors: {
        violet: {
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6d28d9',
        },
      },
    },
  },
  plugins: [],
};
