/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "ui-monospace", "monospace"],
      },
      colors: {
        accent: { DEFAULT: "#7c3aed", hover: "#6d28d9" },
        success: "#10b981",
        warning: "#f59e0b",
        danger:  "#ef4444",
      },
      keyframes: {
        "pipeline-pulse": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(124,58,237,0.5)" },
          "50%":       { boxShadow: "0 0 0 6px rgba(124,58,237,0)" },
        },
        "slide-up": {
          from: { transform: "translateY(6px)", opacity: "0" },
          to:   { transform: "translateY(0)",   opacity: "1" },
        },
        "step-in": {
          from: { transform: "scale(0.7)", opacity: "0" },
          to:   { transform: "scale(1)",   opacity: "1" },
        },
        "error-in": {
          from: { transform: "translateY(4px)", opacity: "0" },
          to:   { transform: "translateY(0)",   opacity: "1" },
        },
      },
      animation: {
        "pipeline-pulse": "pipeline-pulse 2s ease-in-out infinite",
        "slide-up":       "slide-up 200ms ease-out",
        "step-in":        "step-in  200ms ease-out both",
        "error-in":       "error-in 200ms ease-out",
      },
    },
  },
  plugins: [],
};
