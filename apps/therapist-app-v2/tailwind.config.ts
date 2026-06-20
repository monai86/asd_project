import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#121a44",
        panel: "#f4f1ff",
        clinical: "#6f54f6",
        safety: "#a25117",
        line: "#e2dcf7",
        field: "#ffffff",
        moss: "#1f9d70",
        river: "#2f8ad7",
        blossom: "#ef5fc2",
        aqua: "#35c7bf"
      },
      boxShadow: {
        soft: "0 18px 55px rgba(83, 65, 158, 0.12)",
        lift: "0 24px 80px rgba(83, 65, 158, 0.18)"
      }
    }
  },
  plugins: []
};

export default config;
