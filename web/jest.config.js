const nextJest = require("next/jest");

const createJestConfig = nextJest({
  dir: "./",
});

const customJestConfig = {
  reporters: [
    "default",
    ["jest-junit", { outputDirectory: "coverage", outputName: "junit.xml" }],
  ],
  setupFilesAfterEnv: ["<rootDir>/jest.setup.js"],
  testEnvironment: "jest-environment-jsdom",
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
    "^mapbox-gl$": "<rootDir>/src/__mocks__/mapbox-gl.js",
    "^react-map-gl$": "<rootDir>/src/__mocks__/react-map-gl.js",
    "^react-map-gl/mapbox$": "<rootDir>/src/__mocks__/react-map-gl.js",
    "^react-map-gl/maplibre$": "<rootDir>/src/__mocks__/react-map-gl.js",
    "^maplibre-gl$": "<rootDir>/src/__mocks__/mapbox-gl.js",
    "^supercluster$": "<rootDir>/src/__mocks__/supercluster.js",
  },
  collectCoverageFrom: [
    "src/**/*.{js,jsx}",
    "!src/**/*.test.{js,jsx}",
    "!src/__mocks__/**",
    "!src/app/layout.js",
    "!src/app/**/page.js",
  ],
  coverageThreshold: {
    global: {
      lines: 80,
      functions: 80,
    },
  },
  testMatch: ["**/__tests__/**/*.{js,jsx}", "**/*.test.{js,jsx}"],
};

module.exports = createJestConfig(customJestConfig);
