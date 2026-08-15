import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";

export default defineConfig([
  ...nextVitals,
  {
    // Next.js 16 enables React Compiler-oriented hook rules that were not part
    // of the previous lint contract. Migrate the existing effects/refs in a
    // dedicated behavior-preserving refactor instead of coupling it to the
    // security dependency upgrade.
    rules: {
      "@next/next/no-location-assign-relative-destination": "off",
      "react-hooks/immutability": "off",
      "react-hooks/refs": "off",
      "react-hooks/set-state-in-effect": "off",
    },
  },
  globalIgnores([".next/**", ".open-next/**", "coverage/**", "test-results/**"]),
]);
