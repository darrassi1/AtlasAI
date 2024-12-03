/** @type {import('tailwindcss').Config} */
const config = {
    mode: 'jit', // Enabling JIT mode
    darkMode: ["class"], // Enabling dark mode with class strategy
    content: ["./src/**/*.{html,js,svelte,ts}"], // Paths to all templates
    safelist: ["dark"], // Safelist classes

    theme: {
        container: {
            center: true,
            padding: "0.7rem",
            screens: {
                "2xl": "1400px"
            }
        },
        extend: {
            colors: {
                'primary': 'var(--primary)',
                'background': 'var(--background)',
                'secondary': 'var(--secondary)',
                'tertiary': 'var(--tertiary)',
                'foreground': 'var(--foreground)',
                'foreground-invert': 'var(--foreground-invert)',
                'foreground-light': 'var(--foreground-light)',
                'foreground-secondary': 'var(--foreground-secondary)',
                'border': 'var(--border)',
                'btn-active': 'var(--btn-active)',
                'seperator': 'var(--seperator)',
                'window-outline': 'var(--window-outline)',
                'browser-window-dots': 'var(--browser-window-dots)',
                'browser-window-search': 'var(--browser-window-search)',
                'browser-window-ribbon': 'var(--browser-window-ribbon)',
                'browser-window-foreground': 'var(--browser-window-foreground)',
                'browser-window-background': 'var(--browser-window-background)',
                'terminal-window-dots': 'var(--terminal-window-dots)',
                'terminal-window-ribbon': 'var(--terminal-window-ribbon)',
                'terminal-window-background': 'var(--terminal-window-background)',
                'terminal-window-foreground': 'var(--terminal-window-foreground)',
                'slider-empty': 'var(--slider-empty)',
                'slider-filled': 'var(--slider-filled)',
                'slider-thumb': 'var(--slider-thumb)',
                'monologue-background': 'var(--monologue-background)',
                'monologue-outline': 'var(--monologue-outline)',
            },
            fontFamily: {
                sans: ["Helvetica"]
            }
        }
    },
    variants: {
        extend: {
            backgroundColor: ['dark'], // Support for dark mode
            textColor: ['dark'],
            borderColor: ['dark'],
            ringColor: ['dark'],
        }
    },
    plugins: [
        require('@tailwindcss/forms'), // Including Tailwind CSS forms plugin
        require('@tailwindcss/typography'), // Including Tailwind CSS typography plugin
    ],
};

export default config;
