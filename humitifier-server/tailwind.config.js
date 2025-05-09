const colors = require('tailwindcss/colors')

/** @type {import('tailwindcss').Config} */
module.exports = {
    content: ["./src/*/templates/**/*.html", './src/**/*.py'],
    safelist: [
        'sm:table-cell',
        'md:table-cell',
        'lg:table-cell',
        'xl:table-cell',
        '2xl:table-cell',
        'ultrawide:table-cell',
        'btn-danger',
        'btn-primary',
        '!flex',
        '!block',
    ],
    darkMode: ['selector'],
    theme: {
        container: {
            center: true,
        },
        colors: {
            transparent: 'transparent',
            current: 'currentColor',
            black: colors.black,
            white: colors.white,
            gray: colors.zinc,
            blue: colors.blue,
            red: colors.red,
            green: colors.green,
            yellow: colors.yellow,
            orange: colors.orange,
            neutral: colors.neutral,
            primary: '#FFCD00'
        },
        extend: {
            screens: {
                'ultrawide': '2000px',
            }
        }
        // extend: {
        //   colors: {
        //     'primary': '#FFCD00',
        //   }
        // },
    },
    plugins: [
        function ({addVariant}) {
            addVariant('light', 'html:not(.dark) &')
        },
    ],
}
