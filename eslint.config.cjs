const js = require("@eslint/js");

module.exports = [
  js.configs.recommended,
  {
    files: ["src/interfaces/web/static/js/**/*.js"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        document: "readonly",
        window: "readonly",
        requestAnimationFrame: "readonly",
        setTimeout: "readonly",
        fetch: "readonly",
        FormData: "readonly",
        URLSearchParams: "readonly",
      },
    },
    rules: {
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_", caughtErrorsIgnorePattern: "^_" }],
      "no-undef": "error",
      "no-irregular-whitespace": "off",
    },
  },
];
