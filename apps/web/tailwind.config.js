/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Brink palette — locked in Week 1, do not relitigate
        brink: {
          ink: "#0B0B12",       // page bg
          panel: "#15151F",     // card bg
          line: "#26263A",      // borders
          mute: "#8A8AA3",      // secondary text
          text: "#EDEDF5",      // primary text
          accent: "#9D8DF1",    // primary action (lavender)
          hot: "#F472B6",       // reactions / streaks
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
