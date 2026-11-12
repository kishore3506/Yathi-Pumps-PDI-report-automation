/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        havells: {
          red: '#C8102E',
          darkred: '#9C0006',
          gray: '#333333',
          lightgray: '#F5F5F7',
          border: '#E2E8F0',
          accent: '#0284C7'
        }
      }
    },
  },
  plugins: [],
}
