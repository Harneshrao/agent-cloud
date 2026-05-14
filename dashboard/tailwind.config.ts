import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        card: "var(--card)",
        elevated: "var(--elevated)",
        border: "var(--border)",
        primary: "var(--primary)",
        "primary-soft": "var(--primary-soft)",
        secondary: "var(--secondary)",
        "secondary-soft": "var(--secondary-soft)",
        success: "var(--success)",
        warning: "var(--warning)",
        error: "var(--error)",
        foreground: "var(--foreground)",
        "foreground-secondary": "var(--foreground-secondary)",
        muted: "var(--muted)",
        accent: "var(--accent)",
        "accent-muted": "#4f46e5",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "monospace"],
      },
      fontSize: {
        "page-title": ["32px", { lineHeight: "1.2", fontWeight: "700" }],
        "section-title": ["20px", { lineHeight: "1.3", fontWeight: "600" }],
        "card-value": ["28px", { lineHeight: "1.2", fontWeight: "700" }],
        body: ["14px", { lineHeight: "1.5" }],
        label: ["12px", { lineHeight: "1.4", fontWeight: "500" }],
      },
      /* 8px grid: use gap-2 (8px), gap-4 (16px), gap-6 (24px), gap-8 (32px), p-4, p-6, p-8 */
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.25rem",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.06)",
        glow: "0 6px 16px rgba(37, 99, 235, 0.18)",
      },
      animation: {
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-up": "slideUp 0.35s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
