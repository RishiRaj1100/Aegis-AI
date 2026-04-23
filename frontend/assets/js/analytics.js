/**
 * AegisAI — Analytics Module (Chart.js)
 */
const Analytics = (() => {
  'use strict';

  const chartInstances = {};
  const COLORS = {
    indigo: '#6366F1', violet: '#7C3AED', cyan: '#22D3EE',
    emerald: '#10B981', amber: '#F59E0B', rose: '#F43F5E',
    indigoAlpha: 'rgba(99,102,241,0.15)', grid: 'rgba(255,255,255,0.04)',
    text: '#8B92A9',
  };

  const defaultOptions = {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: COLORS.text, font: { family: "'Inter', sans-serif", size: 12 } } },
      tooltip: {
        backgroundColor: '#0F1520', borderColor: 'rgba(255,255,255,0.065)', borderWidth: 1,
        titleFont: { family: "'Inter', sans-serif" }, bodyFont: { family: "'JetBrains Mono', monospace", size: 12 },
        cornerRadius: 8, padding: 12,
      },
    },
    scales: {
      x: { grid: { color: COLORS.grid }, ticks: { color: COLORS.text, font: { family: "'JetBrains Mono', monospace", size: 11 } } },
      y: { grid: { color: COLORS.grid }, ticks: { color: COLORS.text, font: { family: "'JetBrains Mono', monospace", size: 11 } } },
    },
    animation: { duration: 800, easing: 'easeOutQuart' },
  };

  function renderTrustOverTime(canvasId) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || typeof Chart === 'undefined') return;
    if (chartInstances[canvasId]) chartInstances[canvasId].destroy();

    const labels = Array.from({ length: 30 }, (_, i) => `Day ${i + 1}`);
    const data = Array.from({ length: 30 }, () => 55 + Math.random() * 35);

    chartInstances[canvasId] = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Trust Score', data, borderColor: COLORS.indigo, backgroundColor: COLORS.indigoAlpha,
          fill: true, tension: 0.4, pointRadius: 0, pointHoverRadius: 6,
          pointHoverBackgroundColor: COLORS.indigo, borderWidth: 2,
        }],
      },
      options: { ...defaultOptions, plugins: { ...defaultOptions.plugins, legend: { display: false } } },
    });
  }

  function renderDomainDoughnut(canvasId) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || typeof Chart === 'undefined') return;
    if (chartInstances[canvasId]) chartInstances[canvasId].destroy();

    chartInstances[canvasId] = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Business', 'Technology', 'Finance', 'Marketing', 'Operations'],
        datasets: [{
          data: [35, 28, 15, 12, 10],
          backgroundColor: [COLORS.indigo, COLORS.cyan, COLORS.emerald, COLORS.amber, COLORS.violet],
          borderColor: '#05070F', borderWidth: 3,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '65%',
        plugins: {
          legend: { position: 'bottom', labels: { color: COLORS.text, padding: 16, font: { family: "'Inter', sans-serif", size: 12 } } },
          tooltip: defaultOptions.plugins.tooltip,
        },
        animation: { duration: 800, easing: 'easeOutQuart' },
      },
    });
  }

  function renderEthicsBar(canvasId) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || typeof Chart === 'undefined') return;
    if (chartInstances[canvasId]) chartInstances[canvasId].destroy();

    chartInstances[canvasId] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Privacy', 'Bias', 'Legal'],
        datasets: [{
          label: 'Flags', data: [8, 5, 3],
          backgroundColor: [COLORS.indigo, COLORS.amber, COLORS.rose],
          borderRadius: 6, barThickness: 24,
        }],
      },
      options: {
        ...defaultOptions, indexAxis: 'y',
        plugins: { ...defaultOptions.plugins, legend: { display: false } },
        scales: {
          x: { ...defaultOptions.scales.x, beginAtZero: true },
          y: defaultOptions.scales.y,
        },
      },
    });
  }

  function renderScatter(canvasId) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || typeof Chart === 'undefined') return;
    if (chartInstances[canvasId]) chartInstances[canvasId].destroy();

    const data = Array.from({ length: 25 }, () => ({
      x: 40 + Math.random() * 55,
      y: 30 + Math.random() * 65,
    }));

    chartInstances[canvasId] = new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: [{
          label: 'Goals', data,
          backgroundColor: data.map(d => d.x >= 65 && d.y >= 70 ? COLORS.emerald : d.x >= 65 ? COLORS.amber : COLORS.rose),
          pointRadius: 6, pointHoverRadius: 10,
        }],
      },
      options: {
        ...defaultOptions,
        plugins: { ...defaultOptions.plugins, legend: { display: false } },
        scales: {
          x: { ...defaultOptions.scales.x, title: { display: true, text: 'Trust Score', color: COLORS.text } },
          y: { ...defaultOptions.scales.y, title: { display: true, text: 'Success Rate %', color: COLORS.text } },
        },
      },
    });
  }

  function renderAll() {
    renderTrustOverTime('chart-trust');
    renderDomainDoughnut('chart-domain');
    renderEthicsBar('chart-ethics');
    renderScatter('chart-scatter');
  }

  return { renderAll, renderTrustOverTime, renderDomainDoughnut, renderEthicsBar, renderScatter };
})();
