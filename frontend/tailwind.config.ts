import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0e131e",
        surface: "#0e131e",
        "surface-container-lowest": "#090e19",
        "surface-container-low": "#171b27",
        "surface-container": "#1b202b",
        "surface-container-high": "#252a36",
        "surface-container-highest": "#303541",
        primary: "#d0bcff",
        "on-primary": "#3c0091",
        secondary: "#00dce6",
        "secondary-light": "#dcfdff",
        "on-secondary": "#00373a",
        tertiary: "#4edea3",
        error: "#ffb4ab",
        "error-container": "#93000a",
        outline: "#958ea0",
        "outline-variant": "#494454",
        "on-surface": "#dee2f2",
        "on-surface-variant": "#cbc3d7",
      },
      fontFamily: {
        heading: ["'Space Grotesk'", "sans-serif"],
        body: ["'Space Mono'", "monospace"],
      },
      fontSize: {
        "label-sm": ["9px", { lineHeight: "1.2", letterSpacing: "0.05em" }],
        "label-md": ["10px", { lineHeight: "1.2", letterSpacing: "0.05em" }],
        "label-lg": ["12px", { lineHeight: "1.2", letterSpacing: "0.05em" }],
        "body-sm": ["11px", { lineHeight: "1.5", letterSpacing: "0" }],
        "body-md": ["13px", { lineHeight: "1.5", letterSpacing: "0" }],
        "body-lg": ["14px", { lineHeight: "1.5", letterSpacing: "0" }],
        "headline-sm": ["15px", { lineHeight: "1.3", letterSpacing: "0" }],
        "headline-md": ["18px", { lineHeight: "1.3", letterSpacing: "0" }],
        "headline-lg": ["22px", { lineHeight: "1.3", letterSpacing: "0" }],
        "headline-xl": ["32px", { lineHeight: "1.2", letterSpacing: "0" }],
      },
      spacing: {
        "space-xs": "0.25rem",
        "space-sm": "0.5rem",
        "space-md": "0.75rem",
        "space-lg": "1.25rem",
        "space-xl": "2rem",
        gutter: "1rem",
        "gutter-sm": "0.5rem",
        "gutter-lg": "1.5rem",
      },
      borderRadius: {
        DEFAULT: "0.25rem",
      },
    },
  },
  plugins: [],
};
export default config;
