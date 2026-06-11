/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./pages/**/*.{js,jsx}', './components/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dg: {
          bg: '#0d1117',
          sidebar: '#161b22',
          card: '#1c2128',
          border: '#30363d',
          text: '#e6edf3',
          muted: '#7d8590',
          blue: '#58a6ff',
          green: '#3fb950',
          amber: '#d29922',
          red: '#f85149',
          purple: '#a371f7',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif']
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    }
  },
  plugins: []
};
