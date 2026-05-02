/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        azure: {
          50: "#F3FAFF",
          100: "#D7EBFF",
          200: "#B8DAFF",
          300: "#8EC8FF",
          400: "#50A7F5",
          500: "#0078D4",
          600: "#106EBE",
          700: "#005A9E",
          800: "#004578",
          900: "#00335B",
          950: "#001B33",
        },
        fluent: {
          blue: "#0078D4",
          cyan: "#50E6FF",
          success: "#107C10",
          warning: "#FFB900",
          danger: "#D13438",
        },
      },
      boxShadow: {
        glow: "0 0 40px rgba(0, 120, 212, 0.22)",
      },
    },
  },
  plugins: [],
};
