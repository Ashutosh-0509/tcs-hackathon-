import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        certain: "#15803d",
        uncertain: "#b45309",
        needsVerification: "#b91c1c",
      },
    },
  },
  plugins: [],
};

export default config;
