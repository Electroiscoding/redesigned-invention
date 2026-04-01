import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'element-h': '#FF4444',
        'element-he': '#CCFF00',
        'element-ne': '#FF6600',
        'element-o': '#00CCCC',
        'glass-bg': 'rgba(255, 255, 255, 0.12)',
      },
    },
  },
  plugins: [],
}

export default config