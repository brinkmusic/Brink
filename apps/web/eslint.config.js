import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";

// Minimal baseline: ESLint + typescript-eslint recommended. Tighten as needed.
export default tseslint.config(
  { ignores: ["dist"] },
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  }
);
