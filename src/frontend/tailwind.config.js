/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        academic: {
          primary: '#1E3A8A',    // Deep Academic Blue
          secondary: '#2563EB',  // Royal Blue
          success: '#10B981',    // Emerald Green
          warning: '#F59E0B',    // Amber Orange
          danger: '#EF4444',     // Crimson Red
          canvas: '#F8FAFC',     // Slate 50
          border: '#E2E8F0',     // Slate 200
          text: '#0F172A',       // Slate 900
          muted: '#64748B'       // Slate 500
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
