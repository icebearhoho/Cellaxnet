import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";

export default defineConfig([
  ...nextVitals,
  {
    // This React 19 compiler-oriented rule rejects the established async-load
    // effects throughout this React 18 app. Keep the existing behavior until
    // the React 19 migration can refactor them deliberately.
    rules: {
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/static-components": "off",
      "@next/next/no-location-assign-relative-destination": "off",
      "import/no-anonymous-default-export": "off",
    },
  },
  globalIgnores([".next/**", "node_modules/**", "next-env.d.ts"]),
]);
