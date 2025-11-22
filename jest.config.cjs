module.exports = {
  testEnvironment: "jsdom",
  roots: ["<rootDir>/tests/frontend"],
  collectCoverage: true,
  collectCoverageFrom: ["src/interfaces/web/static/js/**/*.js"],
  coverageDirectory: "artifacts/js-coverage",
  coverageReporters: ["text-summary", "lcov", "html"],
  transform: {},
};
