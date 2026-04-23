/**
 * AegisAI — Pipeline Module
 * SSE connection, agent progress rendering, results cards
 */
const Pipeline = (() => {
  'use strict';
  const API = (typeof Auth !== 'undefined' && Auth.API_BASE) || 'http://localhost:8000';

  const AGENTS = ['Commander', 'Research', 'Execution', 'Trust', 'Memory', 'Reflection'];
  const AGENT_ICONS = ['terminal', 'search', 'list-checks', 'shield-check', 'database', 'brain'];

  let currentEventSource = null;

  /* ── Submit goal (standard POST) ── */
  async function submitGoal(goal, language = 'en-IN') {
    const token = typeof Auth !== 'undefined' ? Auth.getToken() : null;
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API}/goal`, {
      method: 'POST', headers,
      body: JSON.stringify({ goal, language }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(err.detail || 'Failed to process goal');
    }
    return res.json();
  }

  /* ── Render pipeline progress strip ── */
  function renderPipelineStrip(container, activeIdx, states = {}) {
    container.innerHTML = AGENTS.map((name, i) => {
      const state = states[name] || (i < activeIdx ? 'complete' : i === activeIdx ? 'active' : 'idle');
      const cls = `pipeline-node pipeline-node--${state}${state === 'active' ? ' shimmer' : ''}`;
      let icon = 'circle';
      if (state === 'complete') icon = 'check';
      else if (state === 'active') icon = 'loader-2';
      else if (state === 'error') icon = 'x';
      else icon = AGENT_ICONS[i];

      return `
        <div class="${cls}">
          <i data-lucide="${icon}" style="width:14px;height:14px;${state === 'active' ? 'animation:spin 1s linear infinite;' : ''}"></i>
          <span>${name}</span>
        </div>
        ${i < AGENTS.length - 1 ? `<div class="pipeline-connector${i < activeIdx ? ' active' : ''}"></div>` : ''}
      `;
    }).join('');
    if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [container] });
  }

  /* ── Build trust score ring SVG ── */
  function buildTrustRing(score, size = 180) {
    const r = (size / 2) - 10;
    const circ = 2 * Math.PI * r;
    const offset = circ * (1 - score / 100);
    const color = score >= 75 ? 'var(--emerald)' : score >= 50 ? 'var(--amber)' : 'var(--rose)';

    return `
      <div class="trust-ring" style="width:${size}px;height:${size}px;">
        <svg width="${size}" height="${size}" class="trust-ring__svg">
          <circle class="trust-ring__track" cx="${size/2}" cy="${size/2}" r="${r}"/>
          <circle class="trust-ring__fill" cx="${size/2}" cy="${size/2}" r="${r}"
            stroke="${color}" stroke-dasharray="${circ}" stroke-dashoffset="${offset}"
            style="transition:stroke-dashoffset 1.2s cubic-bezier(0.4,0,0.2,1);"/>
        </svg>
        <span class="trust-ring__value" style="font-size:${size > 120 ? 42 : 24}px;" data-target="${score}">0</span>
        <span class="trust-ring__label">/ 100</span>
      </div>
    `;
  }

  /* ── Animate trust counter ── */
  function animateTrustCounter(container) {
    const el = container.querySelector('.trust-ring__value');
    if (!el) return;
    const target = parseInt(el.dataset.target);
    if (typeof gsap !== 'undefined') {
      gsap.to({ v: 0 }, {
        v: target, duration: 1.2, ease: 'power2.out',
        onUpdate: function() { el.textContent = Math.round(this.targets()[0].v); }
      });
    } else {
      el.textContent = target;
    }
  }

  /* ── Render full results dashboard ── */
  function renderResults(container, data) {
    const plan = data.plan || data;
    const confidence = data.confidence || plan.confidence || 0;
    const subtasks = plan.subtasks || [];
    const research = plan.research_insights || '';
    const ethicsFlags = plan.ethics_flags || [];
    const trustDims = plan.trust_dimensions || data.trust_dimensions || {};
    const processingTime = data.processing_time_ms ? (data.processing_time_ms / 1000).toFixed(1) + 's' : '—';
    const taskId = data.task_id || plan.task_id || '—';

    container.innerHTML = `
      <!-- Mission Header -->
      <div class="glass-card p-24" style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:24px;">
        <div style="flex:1;min-width:260px;">
          <h3 style="font-size:20px;font-weight:600;margin-bottom:12px;">${plan.goal || 'Mission Complete'}</h3>
          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <span class="badge badge--indigo">${plan.domain || 'General'}</span>
            <span class="badge badge--indigo" style="font-family:var(--font-mono);">${processingTime}</span>
            <span class="badge badge--indigo" style="font-family:var(--font-mono);">ID: ${String(taskId).substring(0, 8)}</span>
          </div>
        </div>
        <div id="results-trust-ring">${buildTrustRing(Math.round(confidence))}</div>
      </div>

      <!-- Execution Plan -->
      <div class="glass-card p-24">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
          <h3 style="font-size:16px;font-weight:600;">Execution Plan</h3>
          <div style="display:flex;gap:8px;">
            <button class="btn-ghost" style="font-size:12px;padding:6px 12px;" onclick="document.getElementById('dag-view').style.display='block';document.getElementById('list-view').style.display='none';">DAG View</button>
            <button class="btn-ghost" style="font-size:12px;padding:6px 12px;" onclick="document.getElementById('dag-view').style.display='none';document.getElementById('list-view').style.display='block';">List View</button>
          </div>
        </div>
        <div id="dag-view" class="dag-container" style="display:none;min-height:300px;background:var(--bg-surface);border-radius:var(--r-md);"></div>
        <div id="list-view" style="display:flex;flex-direction:column;gap:8px;">
          ${subtasks.map((t, i) => {
            const st = t.trust_score || t.confidence || 0;
            return `
            <div class="glass-card glass-card--static p-16" style="display:flex;align-items:center;gap:12px;cursor:pointer;" onclick="Pipeline.openDrawer(${i})">
              <span style="font-family:var(--font-mono);font-size:12px;color:var(--text-muted);width:24px;">${String(i + 1).padStart(2, '0')}</span>
              <div style="flex:1;">
                <p style="font-size:14px;font-weight:500;">${t.title || t.name || 'Subtask ' + (i+1)}</p>
                <p style="font-size:12px;color:var(--text-secondary);margin-top:2px;">${t.description || ''}</p>
              </div>
              <span class="badge ${st >= 75 ? 'badge--emerald' : st >= 50 ? 'badge--amber' : 'badge--rose'}" style="font-family:var(--font-mono);">${st || '—'}</span>
            </div>`;
          }).join('')}
        </div>
      </div>

      <!-- Research Insights -->
      ${research ? `
      <div class="glass-card p-24">
        <h3 style="font-size:16px;font-weight:600;margin-bottom:12px;">Research Insights</h3>
        <p style="font-size:14px;color:var(--text-secondary);line-height:1.7;white-space:pre-wrap;">${research}</p>
      </div>` : ''}

      <!-- Ethics Scan -->
      <div class="glass-card p-24">
        <h3 style="font-size:16px;font-weight:600;margin-bottom:12px;">Ethics Scan</h3>
        ${ethicsFlags.length === 0
          ? '<div style="display:flex;align-items:center;gap:8px;color:var(--emerald);"><i data-lucide="shield-check" style="width:18px;height:18px;"></i><span>All clear — ethics scan passed</span></div>'
          : ethicsFlags.map(f => `
            <div class="glass-card glass-card--static p-16" style="border-color:rgba(245,158,11,0.3);margin-bottom:8px;">
              <div style="display:flex;align-items:center;gap:8px;">
                <span class="badge badge--amber">${f.type || 'Warning'}</span>
                <span style="font-size:13px;color:var(--text-secondary);">${f.description || f.message || f}</span>
              </div>
            </div>
          `).join('')
        }
      </div>

      <!-- Trust Breakdown -->
      <div class="glass-card p-24">
        <h3 style="font-size:16px;font-weight:600;margin-bottom:16px;">Trust Breakdown</h3>
        <div style="display:flex;flex-direction:column;gap:12px;" id="trust-breakdown-bars"></div>
      </div>

      <!-- Follow-up Chat -->
      <div class="glass-card p-24">
        <h3 style="font-size:16px;font-weight:600;margin-bottom:16px;">Follow-up</h3>
        <div class="chat-thread" id="chat-thread"></div>
        <div style="display:flex;gap:8px;margin-top:12px;">
          <input class="neo-input" id="chat-input" placeholder="Ask about this plan..." style="flex:1;padding:10px 16px;font-size:13px;" aria-label="Follow-up question">
          <button class="btn-primary" style="width:40px;height:40px;padding:0;" onclick="Pipeline.sendChat()" aria-label="Send">
            <i data-lucide="send" style="width:16px;height:16px;"></i>
          </button>
        </div>
      </div>
    `;

    if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [container] });

    // Animate trust ring
    const ringContainer = document.getElementById('results-trust-ring');
    if (ringContainer) animateTrustCounter(ringContainer);

    // Trust breakdown bars
    const barsEl = document.getElementById('trust-breakdown-bars');
    if (barsEl) {
      const defaultDims = {
        'Goal Clarity': trustDims.goal_clarity || 80,
        'Information Quality': trustDims.information_quality || 75,
        'Execution Feasibility': trustDims.execution_feasibility || 70,
        'Risk Management': trustDims.risk_manageability || 65,
        'Resource Adequacy': trustDims.resource_adequacy || 72,
        'External Uncertainty': trustDims.external_uncertainty || 78,
      };
      barsEl.innerHTML = Object.entries(defaultDims).map(([label, score]) => {
        const color = score >= 75 ? 'var(--emerald)' : score >= 50 ? 'var(--amber)' : 'var(--rose)';
        return `
          <div style="display:flex;align-items:center;gap:12px;">
            <span style="font-size:13px;color:var(--text-secondary);width:160px;text-align:right;">${label}</span>
            <div style="flex:1;height:6px;background:var(--border-ghost);border-radius:3px;overflow:hidden;">
              <div style="height:100%;width:${score}%;background:${color};border-radius:3px;transition:width 0.8s ease;"></div>
            </div>
            <span style="font-family:var(--font-mono);font-size:13px;color:var(--text-secondary);width:32px;">${score}</span>
          </div>
        `;
      }).join('');
    }

    // Init DAG if available
    if (typeof DAG !== 'undefined' && subtasks.length > 0) {
      setTimeout(() => DAG.render('dag-view', subtasks), 100);
    }

    // GSAP stagger entrance
    if (typeof gsap !== 'undefined') {
      gsap.from(container.querySelectorAll('.glass-card'), {
        y: 24, opacity: 0, stagger: 0.08, duration: 0.5, ease: 'power2.out',
      });
    }

    // Store for chat
    Pipeline._currentData = data;
  }

  /* ── Subtask drawer ── */
  let drawerEl = null;
  function openDrawer(idx) {
    if (!Pipeline._currentData) return;
    const subtasks = (Pipeline._currentData.plan || Pipeline._currentData).subtasks || [];
    const task = subtasks[idx];
    if (!task) return;

    if (!drawerEl) {
      drawerEl = document.createElement('div');
      drawerEl.className = 'drawer';
      drawerEl.id = 'subtask-drawer';
      document.body.appendChild(drawerEl);
    }

    drawerEl.innerHTML = `
      <button class="btn-icon drawer__close" onclick="Pipeline.closeDrawer()" aria-label="Close drawer" style="position:absolute;top:16px;right:16px;">
        <i data-lucide="x" style="width:16px;height:16px;"></i>
      </button>
      <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);display:block;margin-bottom:16px;">SUBTASK ${String(idx + 1).padStart(2, '0')}</span>
      <h3 style="font-size:18px;margin-bottom:8px;">${task.title || task.name || ''}</h3>
      <p style="font-size:14px;color:var(--text-secondary);line-height:1.6;margin-bottom:24px;">${task.description || ''}</p>
      ${task.dependencies ? `<p style="font-size:12px;color:var(--text-muted);margin-bottom:16px;">Dependencies: ${JSON.stringify(task.dependencies)}</p>` : ''}
      ${task.estimated_duration_minutes ? `<span class="badge badge--indigo">~${task.estimated_duration_minutes} min</span>` : ''}
    `;

    if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [drawerEl] });
    drawerEl.classList.add('open');
  }

  function closeDrawer() {
    if (drawerEl) drawerEl.classList.remove('open');
  }

  /* ── Chat ── */
  function sendChat() {
    const input = document.getElementById('chat-input');
    const thread = document.getElementById('chat-thread');
    if (!input || !thread || !input.value.trim()) return;

    const msg = input.value.trim();
    thread.innerHTML += `<div class="chat-bubble chat-bubble--user">${msg}</div>`;
    input.value = '';

    // Simulated response
    setTimeout(() => {
      thread.innerHTML += `<div class="chat-bubble chat-bubble--ai">I'll analyze that aspect of the plan. Based on the trust score breakdown, the main area to focus on is execution feasibility. Let me provide more detail...</div>`;
      thread.scrollTop = thread.scrollHeight;
    }, 800);

    thread.scrollTop = thread.scrollHeight;
  }

  return {
    submitGoal, renderPipelineStrip, renderResults,
    buildTrustRing, animateTrustCounter,
    openDrawer, closeDrawer, sendChat,
    AGENTS, AGENT_ICONS, _currentData: null,
  };
})();
