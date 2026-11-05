/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        heading: ['Outfit', '"Plus Jakarta Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        pure: {
          white: '#ffffff',
          black: '#000000',
        },
        noir: {
          950: '#040406',
          900: '#08080b',
          850: '#0e0e12',
          800: '#141419',
          700: '#1f1f26',
        },
        snow: {
          50: '#ffffff',
          100: '#fafafa',
          200: '#f4f4f6',
          300: '#eaeaed',
          400: '#dcdce0',
        },
        dopamine: {
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
        }
      },
      boxShadow: {
        'clean': '0 2px 12px -2px rgba(0, 0, 0, 0.04), 0 0 0 1px rgba(0, 0, 0, 0.05)',
        'clean-hover': '0 12px 28px -4px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(0, 0, 0, 0.08)',
        'dark-card': '0 8px 30px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.08)',
        'dark-hover': '0 16px 36px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(255, 255, 255, 0.15)',
        'dopamine-glow': '0 0 35px rgba(16, 185, 129, 0.35)',
      }
    },
  },
  plugins: [],
}