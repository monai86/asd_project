import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "var(--color-text-strong)",
        panel: "var(--color-surface)",
        clinical: "var(--color-accent)",
        safety: "var(--color-warning-text)",
        line: "var(--color-border)",
        field: "var(--color-surface-strong)",
        moss: "var(--color-success-text)",
        river: "var(--color-info-text)",
        blossom: "#cb5f9e",
        aqua: "var(--color-accent)"
      },
      boxShadow: {
        soft: "var(--shadow-soft)",
        lift: "var(--shadow-lift)"
      }
    }
  },
  plugins: []
};

export default config;
