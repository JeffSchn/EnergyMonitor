/**
 * Reusable Chart.js rendering helpers for the Energy Monitor app.
 *
 * CHART_THEME controls every colour / dash-pattern used by the average-line
 * overlays.  Themed branches only need to swap this object.
 */

const CHART_THEME = {
    daily: {
        borderColor: '#A0522D',
        backgroundColor: 'rgba(160, 82, 45, 0.1)',
    },
    monthly: {
        backgroundColor: 'rgba(107, 142, 35, 0.55)',
        borderColor: '#6B8E23',
    },
    avgOverall: {
        borderColor: '#8B4513',
        borderDash: [4, 4],
        borderWidth: 2.5,
    },
    avgSummer: {
        borderColor: '#DAA520',
        borderDash: [6, 6],
        borderWidth: 2,
    },
    avgWinter: {
        borderColor: '#2E8B57',
        borderDash: [6, 6],
        borderWidth: 2,
    },
};

function _buildAvgDatasets(labels, averages, mixedType) {
    const ds = [];
    if (!averages) return ds;

    const specs = [
        { key: 'overall', label: 'Overall Avg',          theme: CHART_THEME.avgOverall },
        { key: 'summer',  label: 'Summer Avg Apr\u2013Sep', theme: CHART_THEME.avgSummer },
        { key: 'winter',  label: 'Winter Avg Oct\u2013Mar', theme: CHART_THEME.avgWinter },
    ];

    for (const s of specs) {
        const val = averages[s.key];
        if (val === null || val === undefined) continue;
        const entry = {
            label: `${s.label} (${val.toFixed(1)} kWh)`,
            data: Array(labels.length).fill(val),
            borderColor: s.theme.borderColor,
            borderDash: s.theme.borderDash,
            borderWidth: s.theme.borderWidth,
            pointRadius: 0,
            fill: false,
            tension: 0,
            order: 1,
        };
        if (mixedType) entry.type = 'line';
        ds.push(entry);
    }
    return ds;
}

function renderDailyChart(canvasId, data, averages) {
    if (!data || data.length === 0) return null;
    const ctx = document.getElementById(canvasId).getContext('2d');
    const labels = data.map(d => d.date);

    const datasets = [{
        label: 'Daily kWh',
        data: data.map(d => d.kwh),
        borderColor: CHART_THEME.daily.borderColor,
        backgroundColor: CHART_THEME.daily.backgroundColor,
        fill: true,
        tension: 0.3,
        pointRadius: 1,
        order: 2,
    }, ..._buildAvgDatasets(labels, averages, false)];

    return new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            scales: {
                x: {
                    title: { display: true, text: 'Date' },
                    ticks: { maxTicksLimit: 20 },
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'kWh' },
                },
            },
        },
    });
}

function renderMonthlyChart(canvasId, data, averages) {
    if (!data || data.length === 0) return null;
    const ctx = document.getElementById(canvasId).getContext('2d');
    const labels = data.map(d => d.label);

    const datasets = [{
        type: 'bar',
        label: 'Monthly kWh',
        data: data.map(d => d.kwh),
        backgroundColor: CHART_THEME.monthly.backgroundColor,
        borderColor: CHART_THEME.monthly.borderColor,
        borderWidth: 1,
        order: 2,
    }, ..._buildAvgDatasets(labels, averages, true)];

    return new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'kWh' },
                },
            },
        },
    });
}
