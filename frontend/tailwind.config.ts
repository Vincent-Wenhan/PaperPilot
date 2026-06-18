import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: "#ffffff",
        "surface-muted": "#f7f8fa",
        border: "#d9dee6",
        "border-strong": "#bdc6d1",
        muted: "#657080",
        soft: "#8a94a3",
        accent: "#176b5d",
        "accent-strong": "#0f564a",
        green: "#1f7a4d",
        amber: "#a56412",
        red: "#b42318",
        violet: "#6d4cc2",
        blue: "#2867b2",
      },
    },
  },
  plugins: [],
};

export default config;
