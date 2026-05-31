import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    rules: {
      "no-restricted-syntax": [
        "error",
        {
          selector:
            "TSAsExpression:not([typeAnnotation.typeName.name='const'])",
          message:
            "Type casting with `as` is not allowed. Use explicit types instead.",
        },
        {
          selector: "TSSatisfiesExpression",
          message: "`satisfies` is not allowed. Use explicit types instead.",
        },
      ],
    },
  },
]);

export default eslintConfig;
