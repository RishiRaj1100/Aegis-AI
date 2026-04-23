/**
 * AegisAI — DAG Visualization (D3.js)
 * Renders subtask dependency graph with pan/zoom
 */
const DAG = (() => {
  'use strict';

  function render(containerId, subtasks) {
    if (typeof d3 === 'undefined') return;
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    const width = container.clientWidth || 700;
    const height = Math.max(400, subtasks.length * 80);

    const svg = d3.select(`#${containerId}`)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .style('background', 'var(--bg-surface)');

    const g = svg.append('g');

    // Zoom
    const zoom = d3.zoom()
      .scaleExtent([0.5, 2])
      .on('zoom', (event) => g.attr('transform', event.transform));
    svg.call(zoom);

    // Layout nodes
    const nodeW = 200, nodeH = 70, gapX = 80, gapY = 30;
    const nodes = subtasks.map((t, i) => ({
      id: i,
      title: t.title || t.name || `Subtask ${i + 1}`,
      score: t.trust_score || t.confidence || 0,
      deps: t.dependencies || [],
      x: 0, y: 0,
    }));

    // Simple layered layout
    const layers = [];
    const placed = new Set();

    function getLayer(node) {
      if (node.deps.length === 0) return 0;
      let maxDepLayer = 0;
      node.deps.forEach(dep => {
        const depIdx = typeof dep === 'number' ? dep : nodes.findIndex(n => n.title === dep);
        if (depIdx >= 0 && placed.has(depIdx)) {
          const depNode = nodes[depIdx];
          const depLayer = layers.findIndex(l => l.includes(depIdx));
          if (depLayer >= 0) maxDepLayer = Math.max(maxDepLayer, depLayer + 1);
        }
      });
      return maxDepLayer;
    }

    // Assign layers
    nodes.forEach((node, i) => {
      const layer = node.deps.length > 0 ? Math.min(i, nodes.length - 1) : 0;
      const layerIdx = Math.floor(i / 3);
      if (!layers[layerIdx]) layers[layerIdx] = [];
      layers[layerIdx].push(i);
      placed.add(i);
    });

    // Position nodes
    layers.forEach((layer, li) => {
      const layerWidth = layer.length * (nodeW + gapX) - gapX;
      const startX = (width - layerWidth) / 2;
      layer.forEach((ni, pos) => {
        nodes[ni].x = startX + pos * (nodeW + gapX);
        nodes[ni].y = 40 + li * (nodeH + gapY);
      });
    });

    // Draw edges
    nodes.forEach(node => {
      if (node.deps && node.deps.length > 0) {
        node.deps.forEach(dep => {
          const depIdx = typeof dep === 'number' ? dep : nodes.findIndex(n => n.title === dep);
          if (depIdx >= 0 && depIdx < nodes.length) {
            const src = nodes[depIdx];
            g.append('path')
              .attr('d', `M${src.x + nodeW / 2},${src.y + nodeH} C${src.x + nodeW / 2},${src.y + nodeH + 20} ${node.x + nodeW / 2},${node.y - 20} ${node.x + nodeW / 2},${node.y}`)
              .attr('fill', 'none')
              .attr('stroke', 'rgba(99,102,241,0.3)')
              .attr('stroke-width', 1.5)
              .attr('marker-end', 'url(#arrowhead)');
          }
        });
      }
    });

    // Arrow marker
    svg.append('defs').append('marker')
      .attr('id', 'arrowhead').attr('viewBox', '0 0 10 10')
      .attr('refX', 9).attr('refY', 5)
      .attr('markerWidth', 6).attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path').attr('d', 'M0,0 L10,5 L0,10 Z').attr('fill', 'rgba(99,102,241,0.4)');

    // Draw nodes
    const nodeGroups = g.selectAll('.dag-node')
      .data(nodes)
      .join('g')
      .attr('class', 'dag-node')
      .attr('transform', d => `translate(${d.x},${d.y})`)
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        if (typeof Pipeline !== 'undefined') Pipeline.openDrawer(d.id);
      });

    nodeGroups.append('rect')
      .attr('width', nodeW).attr('height', nodeH)
      .attr('rx', 12).attr('ry', 12)
      .attr('fill', 'rgba(255,255,255,0.028)')
      .attr('stroke', 'rgba(255,255,255,0.065)')
      .attr('stroke-width', 1);

    nodeGroups.append('text')
      .attr('x', 12).attr('y', 20)
      .text(d => `#${String(d.id + 1).padStart(2, '0')}`)
      .attr('fill', '#3D4463')
      .style('font-family', "'JetBrains Mono', monospace")
      .style('font-size', '11px');

    nodeGroups.append('text')
      .attr('x', 12).attr('y', 42)
      .text(d => d.title.length > 24 ? d.title.substring(0, 24) + '…' : d.title)
      .attr('fill', '#EEF2FF')
      .style('font-family', "'Inter', sans-serif")
      .style('font-size', '13px')
      .style('font-weight', '500');

    // Trust badge
    nodeGroups.append('rect')
      .attr('x', nodeW - 48).attr('y', nodeH - 28)
      .attr('width', 40).attr('height', 20)
      .attr('rx', 10)
      .attr('fill', d => d.score >= 75 ? 'rgba(16,185,129,0.18)' : d.score >= 50 ? 'rgba(245,158,11,0.15)' : 'rgba(244,63,94,0.18)');

    nodeGroups.append('text')
      .attr('x', nodeW - 28).attr('y', nodeH - 14)
      .text(d => d.score || '—')
      .attr('fill', d => d.score >= 75 ? '#10B981' : d.score >= 50 ? '#F59E0B' : '#F43F5E')
      .style('font-family', "'JetBrains Mono', monospace")
      .style('font-size', '11px')
      .style('text-anchor', 'middle');

    // Zoom controls
    const controls = document.createElement('div');
    controls.className = 'dag-controls';
    controls.innerHTML = `
      <button class="btn-icon" style="width:32px;height:32px;" onclick="DAG.zoomIn('${containerId}')" aria-label="Zoom in">+</button>
      <button class="btn-icon" style="width:32px;height:32px;" onclick="DAG.zoomOut('${containerId}')" aria-label="Zoom out">−</button>
      <button class="btn-icon" style="width:32px;height:32px;" onclick="DAG.zoomReset('${containerId}')" aria-label="Reset zoom">⟲</button>
    `;
    container.appendChild(controls);

    // Store zoom ref
    container._zoom = zoom;
    container._svg = svg;
  }

  function zoomIn(id) { const c = document.getElementById(id); if (c?._svg && c._zoom) c._svg.transition().call(c._zoom.scaleBy, 1.3); }
  function zoomOut(id) { const c = document.getElementById(id); if (c?._svg && c._zoom) c._svg.transition().call(c._zoom.scaleBy, 0.7); }
  function zoomReset(id) { const c = document.getElementById(id); if (c?._svg && c._zoom) c._svg.transition().call(c._zoom.transform, d3.zoomIdentity); }

  return { render, zoomIn, zoomOut, zoomReset };
})();
