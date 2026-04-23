/**
 * AegisAI — Landing Page Logic
 * Three.js hero, SplitType headline, comparison table, agents grid,
 * demo pipeline, innovations grid, pricing toggle, VanillaTilt
 */

(function () {
  'use strict';
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ══════════════════════════════════════════════════════════════
     THREE.JS PARTICLE FIELD (Hero Background)
     ══════════════════════════════════════════════════════════════ */
  function initHeroParticles() {
    if (reducedMotion || typeof THREE === 'undefined') return;
    const canvas = document.getElementById('hero-canvas');
    if (!canvas) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, canvas.clientWidth / canvas.clientHeight, 0.1, 1000);
    camera.position.z = 300;

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    const COUNT = 200;
    const positions = [];
    const velocities = [];

    for (let i = 0; i < COUNT; i++) {
      positions.push(
        (Math.random() - 0.5) * 600,
        (Math.random() - 0.5) * 400,
        (Math.random() - 0.5) * 200
      );
      velocities.push(
        (Math.random() - 0.5) * 0.03,
        (Math.random() - 0.5) * 0.03,
        (Math.random() - 0.5) * 0.01
      );
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    const material = new THREE.PointsMaterial({
      color: 0x6366F1, size: 2, transparent: true, opacity: 0.15, sizeAttenuation: true,
    });
    const points = new THREE.Points(geometry, material);
    scene.add(points);

    let animationId;
    let isVisible = true;

    function animate() {
      if (!isVisible) { animationId = requestAnimationFrame(animate); return; }
      const pos = geometry.attributes.position.array;
      for (let i = 0; i < COUNT * 3; i += 3) {
        pos[i] += velocities[i];
        pos[i + 1] += velocities[i + 1];
        pos[i + 2] += velocities[i + 2];
        if (Math.abs(pos[i]) > 300) velocities[i] *= -1;
        if (Math.abs(pos[i + 1]) > 200) velocities[i + 1] *= -1;
      }
      geometry.attributes.position.needsUpdate = true;
      camera.rotation.y += 0.00003;
      renderer.render(scene, camera);
      animationId = requestAnimationFrame(animate);
    }
    animate();

    // Pause when hidden
    if (typeof Aegis !== 'undefined') {
      Aegis.onVisibilityChange((hidden) => { isVisible = !hidden; });
    }

    window.addEventListener('resize', () => {
      camera.aspect = canvas.clientWidth / canvas.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    });
  }

  /* ══════════════════════════════════════════════════════════════
     HERO HEADLINE ANIMATION (SplitType)
     ══════════════════════════════════════════════════════════════ */
  function initHeadlineAnimation() {
    if (reducedMotion || typeof SplitType === 'undefined' || typeof gsap === 'undefined') return;
    const el = document.getElementById('hero-headline');
    if (!el) return;

    const split = new SplitType(el, { types: 'words' });
    gsap.from(split.words, {
      opacity: 0, y: 30, rotateX: -20,
      transformOrigin: '0% 50% -50px',
      duration: 0.8, stagger: 0.06, ease: 'power2.out', delay: 0.3,
    });
  }

  /* ══════════════════════════════════════════════════════════════
     HERO MOCKUP FLOAT + TILT
     ══════════════════════════════════════════════════════════════ */
  function initMockup() {
    const mockup = document.getElementById('hero-mockup');
    if (!mockup) return;

    if (typeof VanillaTilt !== 'undefined') {
      VanillaTilt.init(mockup.querySelector('.glass-card'), {
        max: 6, glare: true, 'max-glare': 0.08, speed: 300,
      });
    }

    if (!reducedMotion && typeof gsap !== 'undefined') {
      gsap.to(mockup, { y: -10, duration: 4, repeat: -1, yoyo: true, ease: 'power1.inOut' });
    }
  }

  /* ══════════════════════════════════════════════════════════════
     COMPARISON TABLE
     ══════════════════════════════════════════════════════════════ */
  function initComparisonTable() {
    const tbody = document.getElementById('comparison-body');
    if (!tbody) return;

    const features = [
      ['Trust Scoring', true, false, false, false],
      ['Ethics Scanning', true, false, false, false],
      ['Plan Revision Gate', true, false, false, true],
      ['Session Memory', true, false, true, true],
      ['Outcome Learning', true, false, false, false],
      ['Voice I/O', true, false, false, false],
      ['Real-time Streaming', true, false, false, true],
      ['Adversarial Testing', true, false, false, false],
    ];

    tbody.innerHTML = features.map(([name, ...vals]) => `
      <tr style="border-bottom:1px solid var(--border-ghost);">
        <td style="padding:10px 0;color:var(--text-secondary);">${name}</td>
        ${vals.map((v, i) => `<td style="padding:10px 8px;color:${i === 0 ? (v ? 'var(--emerald)' : 'var(--rose)') : (v ? 'var(--text-muted)' : 'var(--rose)')};">${v ? '✦' : '—'}</td>`).join('')}
      </tr>
    `).join('');
  }

  /* ══════════════════════════════════════════════════════════════
     TRUST SCORE RING ANIMATION
     ══════════════════════════════════════════════════════════════ */
  function initTrustRing() {
    const fill = document.getElementById('trust-fill-demo');
    const val = document.getElementById('trust-value-demo');
    const barsContainer = document.getElementById('trust-bars-demo');
    if (!fill || !val) return;

    const score = 82;
    const circumference = 2 * Math.PI * 70;
    const offset = circumference * (1 - score / 100);

    const dims = [
      { label: 'Goal Clarity', score: 88 },
      { label: 'Feasibility', score: 79 },
      { label: 'Risk Management', score: 76 },
      { label: 'Information Quality', score: 85 },
      { label: 'Resource Adequacy', score: 80 },
      { label: 'External Uncertainty', score: 84 },
    ];

    if (barsContainer) {
      barsContainer.innerHTML = dims.map(d => `
        <div style="display:flex;align-items:center;gap:8px;">
          <span style="font-size:11px;color:var(--text-muted);width:120px;text-align:right;">${d.label}</span>
          <div style="flex:1;height:4px;background:var(--border-ghost);border-radius:2px;overflow:hidden;">
            <div class="trust-bar-fill" data-width="${d.score}" style="height:100%;width:0%;background:${d.score >= 75 ? 'var(--emerald)' : d.score >= 50 ? 'var(--amber)' : 'var(--rose)'};border-radius:2px;transition:width 1s ease;"></div>
          </div>
          <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-secondary);width:28px;">${d.score}</span>
        </div>
      `).join('');
    }

    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      observer.disconnect();
      fill.style.strokeDashoffset = offset;

      if (typeof gsap !== 'undefined' && !reducedMotion) {
        gsap.to({ v: 0 }, { v: score, duration: 1.2, ease: 'power2.out', onUpdate: function () { val.textContent = Math.round(this.targets()[0].v); } });
      } else {
        val.textContent = score;
      }

      document.querySelectorAll('.trust-bar-fill').forEach(bar => {
        setTimeout(() => { bar.style.width = bar.dataset.width + '%'; }, 400);
      });
    }, { threshold: 0.15 });

    observer.observe(fill.closest('.glass-card') || fill);
  }

  /* ══════════════════════════════════════════════════════════════
     AGENTS GRID
     ══════════════════════════════════════════════════════════════ */
  function initAgentsGrid() {
    const grid = document.getElementById('agents-grid');
    if (!grid) return;

    const agents = [
      { name: 'Commander', icon: 'terminal', role: 'Goal Decomposition', desc: 'Breaks complex goals into structured, prioritized subtasks with dependency mapping.' },
      { name: 'Research', icon: 'search', role: 'Contextual Intelligence', desc: 'Investigates feasibility, context, and real-world constraints for each subtask.' },
      { name: 'Execution', icon: 'list-checks', role: 'Plan Generation', desc: 'Builds a detailed, ordered execution plan with milestones and timelines.' },
      { name: 'Trust', icon: 'shield-check', role: 'Confidence Scoring', desc: 'Scores the plan 0–100 across 6 dimensions. Blocks or revises if too low.' },
      { name: 'Memory', icon: 'database', role: 'Persistence & Recall', desc: 'Stores in MongoDB, retrieves similar past plans semantically.' },
      { name: 'Reflection', icon: 'brain', role: 'Continuous Learning', desc: 'Learns from outcomes. Calibrates future trust scores based on results.' },
    ];

    grid.innerHTML = agents.map((a, i) => `
      <div class="glass-card p-24" data-aos="fade-up" data-aos-delay="${i * 100}" data-tilt data-tilt-max="4" data-tilt-speed="400">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
          <div style="width:48px;height:48px;border-radius:50%;background:var(--indigo-dim);display:flex;align-items:center;justify-content:center;">
            <i data-lucide="${a.icon}" style="width:22px;height:22px;color:var(--indigo);"></i>
          </div>
          <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);">0${i + 1}</span>
        </div>
        <h3 style="font-size:18px;margin-bottom:4px;">${a.name} Agent</h3>
        <p style="font-size:13px;color:var(--indigo);margin-bottom:12px;">${a.role}</p>
        <p style="font-size:14px;color:var(--text-secondary);line-height:1.6;">${a.desc}</p>
      </div>
    `).join('');

    if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [grid] });
    if (typeof VanillaTilt !== 'undefined') {
      grid.querySelectorAll('[data-tilt]').forEach(el => VanillaTilt.init(el, { max: 4, speed: 400 }));
    }
  }

  /* ══════════════════════════════════════════════════════════════
     LIVE DEMO
     ══════════════════════════════════════════════════════════════ */
  function initDemo() {
    const btn = document.getElementById('demo-run-btn');
    const pipelineEl = document.getElementById('demo-pipeline');
    const resultEl = document.getElementById('demo-result');
    if (!btn || !pipelineEl) return;

    const agents = ['Commander', 'Research', 'Execution', 'Trust', 'Memory', 'Reflection'];

    function renderPipeline(activeIdx) {
      pipelineEl.innerHTML = agents.map((a, i) => {
        let cls = 'pipeline-node--idle';
        let icon = `<i data-lucide="circle" style="width:12px;height:12px;"></i>`;
        if (i < activeIdx) { cls = 'pipeline-node--complete'; icon = `<i data-lucide="check" style="width:12px;height:12px;"></i>`; }
        else if (i === activeIdx) { cls = 'pipeline-node--active shimmer'; icon = `<i data-lucide="loader-2" style="width:12px;height:12px;animation:spin 1s linear infinite;"></i>`; }
        return `
          <div class="pipeline-node ${cls}">${icon} ${a}</div>
          ${i < agents.length - 1 ? `<div class="pipeline-connector ${i < activeIdx ? 'active' : ''}"></div>` : ''}
        `;
      }).join('');
      if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [pipelineEl] });
    }

    btn.addEventListener('click', async () => {
      btn.disabled = true;
      btn.innerHTML = '<i data-lucide="loader-2" style="width:16px;height:16px;animation:spin 1s linear infinite;"></i> Running...';
      if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [btn] });
      resultEl.style.display = 'none';

      for (let i = 0; i < agents.length; i++) {
        renderPipeline(i);
        await new Promise(r => setTimeout(r, 700));
      }
      renderPipeline(agents.length);

      // Show result
      resultEl.style.display = 'block';
      const trustFill = document.getElementById('demo-trust-fill');
      const trustVal = document.getElementById('demo-trust-val');
      if (trustFill && typeof gsap !== 'undefined') {
        const circumference = 2 * Math.PI * 42;
        trustFill.style.strokeDasharray = circumference;
        trustFill.style.strokeDashoffset = circumference * (1 - 79 / 100);
        gsap.to({ v: 0 }, { v: 79, duration: 1, ease: 'power2.out', onUpdate: function () { trustVal.textContent = Math.round(this.targets()[0].v); } });
      }

      const subtasks = document.getElementById('demo-subtasks');
      if (subtasks) {
        subtasks.innerHTML = [
          { title: 'Define MVP scope & feature list', trust: 85 },
          { title: 'Set up CI/CD and infrastructure', trust: 78 },
          { title: 'Build core product (8-week sprint)', trust: 72 },
        ].map(s => `
          <div class="glass-card p-16" style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:13px;color:var(--text-secondary);">${s.title}</span>
            <span class="badge ${s.trust >= 75 ? 'badge--emerald' : 'badge--amber'}">${s.trust}</span>
          </div>
        `).join('');
      }

      btn.disabled = false;
      btn.innerHTML = '<i data-lucide="play" style="width:16px;height:16px;"></i> Run Demo';
      if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [btn] });
    });

    renderPipeline(-1);
  }

  /* ══════════════════════════════════════════════════════════════
     INNOVATIONS GRID
     ══════════════════════════════════════════════════════════════ */
  function initInnovations() {
    const grid = document.getElementById('innovations-grid');
    if (!grid) return;

    const items = [
      { icon: 'swords', title: 'Adversarial Red-Team Agent', desc: 'Our AI attacks its own plan before you see it.' },
      { icon: 'dna', title: 'Decision DNA', desc: 'Builds your cognitive fingerprint from every decision.' },
      { icon: 'globe', title: 'Live World Model Sync', desc: 'Validates plans against today\'s news, not training data.' },
      { icon: 'users', title: 'Stakeholder War Room', desc: 'Simulates CEO, Investor, Customer reactions to your plan.' },
      { icon: 'shield', title: 'Temporal Immune System', desc: 'Monitors your stored plans for world changes after delivery.' },
      { icon: 'git-branch', title: 'Counterfactual Engine', desc: 'Shows the alternate timeline if you\'d chosen differently.' },
    ];

    grid.innerHTML = items.map((item, i) => `
      <div class="glass-card p-24" data-aos="fade-up" data-aos-delay="${i * 100}" data-tilt data-tilt-max="4">
        <i data-lucide="${item.icon}" style="width:28px;height:28px;color:var(--indigo);margin-bottom:16px;"></i>
        <h3 style="font-size:16px;margin-bottom:8px;">${item.title}</h3>
        <p style="font-size:14px;color:var(--text-secondary);line-height:1.5;">${item.desc}</p>
      </div>
    `).join('');

    if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [grid] });
    if (typeof VanillaTilt !== 'undefined') {
      grid.querySelectorAll('[data-tilt]').forEach(el => VanillaTilt.init(el, { max: 4, speed: 400 }));
    }
  }

  /* ══════════════════════════════════════════════════════════════
     PRICING TOGGLE
     ══════════════════════════════════════════════════════════════ */
  window.setPricing = function (mode) {
    const pro = document.getElementById('pro-price');
    const team = document.getElementById('team-price');
    const mBtn = document.getElementById('price-monthly');
    const aBtn = document.getElementById('price-annual');
    if (!pro || !team) return;

    if (mode === 'annual') {
      pro.textContent = '10';
      team.textContent = '42';
      aBtn.classList.add('btn-primary'); aBtn.classList.remove('btn-ghost');
      mBtn.classList.add('btn-ghost'); mBtn.classList.remove('btn-primary');
    } else {
      pro.textContent = '12';
      team.textContent = '49';
      mBtn.classList.add('btn-primary'); mBtn.classList.remove('btn-ghost');
      aBtn.classList.add('btn-ghost'); aBtn.classList.remove('btn-primary');
    }
  };

  /* ══════════════════════════════════════════════════════════════
     VANILLA TILT INIT FOR ALL [data-tilt]
     ══════════════════════════════════════════════════════════════ */
  function initTilt() {
    if (typeof VanillaTilt === 'undefined' || reducedMotion) return;
    document.querySelectorAll('[data-tilt]').forEach(el => {
      VanillaTilt.init(el, {
        max: parseInt(el.dataset.tiltMax) || 4,
        speed: parseInt(el.dataset.tiltSpeed) || 400,
        glare: el.dataset.tiltGlare === 'true',
        'max-glare': parseFloat(el.dataset.tiltMaxGlare) || 0,
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════
     INIT
     ══════════════════════════════════════════════════════════════ */
  function init() {
    initHeroParticles();
    initHeadlineAnimation();
    initMockup();
    initComparisonTable();
    initTrustRing();
    initAgentsGrid();
    initDemo();
    initInnovations();
    initTilt();
    window.setPricing('monthly');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
