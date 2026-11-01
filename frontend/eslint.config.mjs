// ESLint setup. eslint-config-next 16 supports the new flat config, so its rules are
// imported directly. (The old FlatCompat wrapper crashes on ESLint 9.)
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const config = [
  ...nextCoreWebVitals,
  ...nextTypescript,
  { ignores: [".next/**", "node_modules/**", "lib/api/**"] },
];

export default config;
