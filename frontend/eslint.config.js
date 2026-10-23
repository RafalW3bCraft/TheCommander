import tseslint from "typescript-eslint";
import hooks from "eslint-plugin-react-hooks";
export default tseslint.config(...tseslint.configs.recommended, {
  files: ["src/**/*.{ts,tsx}", "e2e/**/*.ts"],
  plugins: { "react-hooks": hooks },
  rules: {
    "@typescript-eslint/no-explicit-any": "error",
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "error",
  },
});
