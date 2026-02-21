/**
 * Reusable Chart.js rendering helpers for the Energy Monitor app.
 */

function renderDailyChart(canvasId, data, averages) {
    if (!data || data.length === 0) return;
    const ctx = document.getElementById(canvasId).getContext('2d');

    const labels = data.map(d => d.date);
    const datasets = [{
        label: 'Daily kWh',
        data: data.map(d => d.kwh),
        borderColor: 'rgba(54, 162, 235, 1)',
        backgroundColor: 'rgba(54, 162, 235, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 1,
        order: 2,
    }];

    if (averages) {
        if (averages.overall !== null) {
            datasets.push({
                label: `Overall Avg (${averages.overall.toFixed(1)} kWh)`,
                data: Array(labels.length).fill(averages.overall),
                borderColor: 'rgba(255, 99, 132, 1)',
                borderDash: [6, 4],
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                tension: 0,
                order: 1,
            });
        }
        if (averages.summer !== null) {
            datasets.push({
                label: `Summer Avg Apr–Sep (${averages.summer.toFixed(1)} kWh)`,
                data: Array(labels.length).fill(averages.summer),
                borderColor: 'rgba(255, 159, 64, 1)',
                borderDash: [8, 4],
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                tension: 0,
                order: 1,
            });
        }
        if (averages.winter !== null) {
            datasets.push({
                label: `Winter Avg Oct–Mar (${averages.winter.toFixed(1)} kWh)`,
                data: Array(labels.length).fill(averages.winter),
                borderColor: 'rgba(75, 192, 192, 1)',
                borderDash: [8, 4],
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                tension: 0,
                order: 1,
            });
        }
    }

    new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            scales: {
                x: {
                    title: { display: true, text: 'Date' },
                    ticks: { maxTicksLimit: 20 }
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'kWh' }
                }
            }
        }
    });
}

function renderMonthlyChart(canvasId, data, averages) {
    if (!data || data.length === 0) return;
    const ctx = document.getElementById(canvasId).getContext('2d');

    const labels = data.map(d => d.label);
    const datasets = [{
        type: 'bar',
        label: 'Monthly kWh',
        data: data.map(d => d.kwh),
        backgroundColor: 'rgba(75, 192, 192, 0.6)',
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1,
        order: 2,
    }];

    if (averages) {
        if (averages.overall !== null) {
            datasets.push({
                type: 'line',
                label: `Overall Avg (${averages.overall.toFixed(1)} kWh)`,
                data: Array(labels.length).fill(averages.overall),
                borderColor: 'rgba(255, 99, 132, 1)',
                borderDash: [6, 4],
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                order: 1,
            });
        }
        if (averages.summer !== null) {
            datasets.push({
                type: 'line',
                label: `Summer Avg Apr–Sep (${averages.summer.toFixed(1)} kWh)`,
                data: Array(labels.length).fill(averages.summer),
                borderColor: 'rgba(255, 159, 64, 1)',
                borderDash: [8, 4],
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                order: 1,
            });
        }
        if (averages.winter !== null) {
            datasets.push({
                type: 'line',
                label: `Winter Avg Oct–Mar (${averages.winter.toFixed(1)} kWh)`,
                data: Array(labels.length).fill(averages.winter),
                borderColor: 'rgba(54, 162, 235, 1)',
                borderDash: [8, 4],
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                order: 1,
            });
        }
    }

    new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'kWh' }
                }
            }
        }
    });
}
