/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#0a0f1c",
          900: "#0f1729",
          800: "#151f38",
          700: "#1e2d52",
        },
        accent: {
          purple: "#7c6cf0",
          violet: "#5b4bc4",
        },
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "system-ui", "sans-serif"],
        display: ["IBM Plex Sans", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
