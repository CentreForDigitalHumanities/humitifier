let charts = [];

window.chartColors = [
    '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316', '#14b8a6', '#6366f1',
    '#0ea5e9', '#84cc16', '#eab308', '#f43f5e', '#a855f7', '#d946ef', '#4f46e5', '#0891b2', '#0d9488', '#7c3aed'
];

function getChartColors() {
    const isDark = document.documentElement.classList.contains('dark');
    return {
        text: isDark ? '#e5e7eb' : '#1f2937',
        grid: isDark ? '#374151' : '#e5e7eb',
    };
}

function updateChartTheme() {
    const colors = getChartColors();

    Chart.defaults.color = colors.text;
    Chart.defaults.borderColor = colors.grid;
    Chart.defaults.plugins.legend.labels.color = colors.text;
    Chart.defaults.plugins.title.color = colors.text;

    charts.forEach(chart => {
        chart.options.plugins.legend.labels.color = colors.text;
        chart.options.plugins.title.color = colors.text;

        if (chart.options.scales) {
            Object.values(chart.options.scales).forEach(scale => {
                if (scale.ticks) scale.ticks.color = colors.text;
                if (scale.grid) scale.grid.color = colors.grid;
                if (scale.title) scale.title.color = colors.text;
            });
        }
        chart.update();
    });
}

document.addEventListener('themeChanged', updateChartTheme);

/**
 * Initialize a chart with standard dashboard styling
 */
function initDashboardChart(canvasId, type, title, labels, datasets, extraOptions = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const colors = getChartColors();
    Chart.defaults.color = colors.text;
    Chart.defaults.borderColor = colors.grid;
    Chart.defaults.plugins.legend.labels.color = colors.text;
    Chart.defaults.plugins.title.color = colors.text;

    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: type === 'pie' ? 'right' : 'bottom',
            },
            title: {
                display: true,
                text: title,
            },
        },
    };

    // Deep merge for plugins.legend and plugins.title if they exist in extraOptions
    const options = {
        ...defaultOptions,
        ...extraOptions,
        onClick: (event, elements, chart) => {
            if (elements.length > 0) {
                const element = elements[0];
                const datasetIndex = element.datasetIndex;
                const index = element.index;
                const dataset = chart.data.datasets[datasetIndex];

                if (dataset.links && dataset.links[index]) {
                    window.location.href = dataset.links[index];
                }
            }
        },
        onHover: (event, elements, chart) => {
            if (elements.length > 0) {
                const element = elements[0];
                const datasetIndex = element.datasetIndex;
                const index = element.index;
                const dataset = chart.data.datasets[datasetIndex];
                if (dataset.links && dataset.links[index]) {
                    event.native.target.style.cursor = 'pointer';
                    return;
                }
            }
            event.native.target.style.cursor = 'default';
        },
        plugins: {
            ...defaultOptions.plugins,
            ...(extraOptions.plugins || {}),
            legend: {
                ...defaultOptions.plugins.legend,
                ...(extraOptions.plugins?.legend || {}),
            },
            title: {
                ...defaultOptions.plugins.title,
                ...(extraOptions.plugins?.title || {}),
            }
        }
    };

    const chart = new Chart(canvas, {
        type: type,
        data: {
            labels: labels,
            datasets: datasets
        },
        options: options,
    });
    charts.push(chart);
    return chart;
}
