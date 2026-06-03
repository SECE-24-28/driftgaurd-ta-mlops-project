/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        obsidian: {
          50: "#f8fafc",
          100: "#f1f5f9",
          900: "#090d16",
          950: "#04060c",
        },
      },
    },
  },
  plugins: [],
};
