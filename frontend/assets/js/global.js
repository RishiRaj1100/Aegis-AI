/* ============================================================================
   AEGISAI GLOBAL.JS — Core JavaScript Systems
   Lenis Smooth Scroll, Custom Cursor, Toast Notifications, 
   Page Transitions, Command Palette, Keyboard Shortcuts, Auth Management
   ============================================================================ */

'use strict';

/* ============================================================================
   1. LENIS SMOOTH SCROLL INITIALIZATION
   ============================================================================ */

let lenis;

function initLenis() {
  if (typeof Lenis === 'undefined') return;
  
  lenis = new Lenis({
    duration: 1.4,
    easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smooth: true,
    smoothTouch: false,
    wheelMultiplier: 1,
    touchMultiplier: 1.5,
  });

  function raf(time) {
    lenis.raf(time);
    requestAnimationFrame(raf);
  }
  requestAnimationFrame(raf);

  // Sync with GSAP ScrollTrigger if GSAP is loaded
  if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {
    lenis.on('scroll', ScrollTrigger.update);
    gsap.ticker.add((time) => {
      lenis.raf(time * 1000);
    });
    gsap.ticker.lagSmoothing(0);
  }

  console.log('✓ Lenis smooth scroll initialized');
}

/* ============================================================================
   2. GSAP PLUGINS REGISTRATION & CUSTOM EASE
   ============================================================================ */

function initGSAP() {
  if (typeof gsap === 'undefined') return;
  
  if (typeof ScrollTrigger !== 'undefined') gsap.registerPlugin(ScrollTrigger);
  if (typeof TextPlugin !== 'undefined') gsap.registerPlugin(TextPlugin);
  if (typeof CustomEase !== 'undefined') {
    gsap.registerPlugin(CustomEase);
    CustomEase.create('aegis', '0.22, 1, 0.36, 1');
  }
  
  console.log('✓ GSAP plugins initialized');
}

/* ============================================================================
   3. CUSTOM CURSOR SYSTEM (Desktop only)
   ============================================================================ */

function initCustomCursor() {
  // Skip on mobile/touch devices
  if (window.matchMedia('(pointer:coarse)').matches) {
    return;
  }

  const dot = document.createElement('div');
  const ring = document.createElement('div');

  // Dot styling
  Object.assign(dot.style, {
    position: 'fixed',
    width: '4px',
    height: '4px',
    background: 'var(--indigo)',
    borderRadius: '50%',
    pointerEvents: 'none',
    zIndex: '99999',
    left: '0px',
    top: '0px',
    boxShadow: '0 0 8px rgba(99, 102, 241, 0.5)',
  });

  // Ring styling
  Object.assign(ring.style, {
    position: 'fixed',
    width: '28px',
    height: '28px',
    border: '1px solid rgba(255, 255, 255, 0.4)',
    borderRadius: '50%',
    pointerEvents: 'none',
    zIndex: '99998',
    left: '0px',
    top: '0px',
    transition: 'transform 0.2s ease-out, border-color 0.2s ease-out',
  });

  document.body.appendChild(dot);
  document.body.appendChild(ring);

  // Use GSAP if available for smoother movement
  let moveDot, moveDotX, moveRing, moveRingX;

  if (typeof gsap !== 'undefined') {
    moveDot = gsap.quickTo(dot, 'top', { duration: 0, ease: 'none' });
    moveDotX = gsap.quickTo(dot, 'left', { duration: 0, ease: 'none' });
    moveRing = gsap.quickTo(ring, 'top', { duration: 0.08, ease: 'power3' });
    moveRingX = gsap.quickTo(ring, 'left', { duration: 0.08, ease: 'power3' });
  } else {
    // Fallback without GSAP
    moveDot = (y) => (dot.style.top = y + 'px');
    moveDotX = (x) => (dot.style.left = x + 'px');
    moveRing = (y) => (ring.style.top = y + 'px');
    moveRingX = (x) => (ring.style.left = x + 'px');
  }

  // Mouse move listener
  document.addEventListener('mousemove', (e) => {
    moveDot(e.clientY - 2);
    moveDotX(e.clientX - 2);
    moveRing(e.clientY - 14);
    moveRingX(e.clientX - 14);
  });

  // Hover effects on interactive elements
  const interactiveSelector = 'a, button, [data-cursor="pointer"], input, textarea';
  document.addEventListener('mouseover', (e) => {
    if (e.target.closest(interactiveSelector)) {
      ring.style.borderColor = 'var(--indigo)';
      ring.style.transform = 'scale(1.8)';
      dot.style.opacity = '0.5';
    }
  });

  document.addEventListener('mouseout', (e) => {
    if (e.target.closest(interactiveSelector)) {
      ring.style.borderColor = 'rgba(255, 255, 255, 0.4)';
      ring.style.transform = 'scale(1)';
      dot.style.opacity = '1';
    }
  });

  // Mouse down/up effects
  document.addEventListener('mousedown', () => {
    ring.style.transform = 'scale(0.7)';
  });

  document.addEventListener('mouseup', () => {
    ring.style.transform = 'scale(1)';
  });

  console.log('✓ Custom cursor initialized');
}

/* ============================================================================
   4. TOAST NOTIFICATION SYSTEM
   ============================================================================ */

class ToastManager {
  constructor() {
    this.toasts = [];
    this.maxVisible = 3;
    this.init();
  }

  init() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    Object.assign(container.style, {
      position: 'fixed',
      top: '24px',
      right: '24px',
      zIndex: '10000',
      display: 'flex',
      flexDirection: 'column',
      gap: '12px',
      pointerEvents: 'none',
    });
    document.body.appendChild(container);
  }

  show(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');

    // Color mapping
    const colors = {
      success: { bg: 'rgba(16, 185, 129, 0.1)', border: '#10B981', icon: '✓' },
      error: { bg: 'rgba(244, 63, 94, 0.1)', border: '#F43F5E', icon: '✕' },
      warning: { bg: 'rgba(245, 158, 11, 0.1)', border: '#F59E0B', icon: '⚠' },
      info: { bg: 'rgba(99, 102, 241, 0.1)', border: '#6366F1', icon: 'ⓘ' },
    };

    const color = colors[type] || colors.info;

    Object.assign(toast.style, {
      background: color.bg,
      border: `1px solid ${color.border}`,
      borderRadius: 'var(--r-md)',
      padding: '16px 20px',
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      minWidth: '320px',
      maxWidth: '400px',
      boxShadow: '0 10px 30px rgba(0, 0, 0, 0.3)',
      backdropFilter: 'blur(8px)',
      color: 'var(--text-primary)',
      fontSize: '14px',
      fontWeight: '500',
      pointerEvents: 'auto',
      animation: 'slide-in-right 0.3s cubic-bezier(0.22, 1, 0.36, 1)',
    });

    toast.innerHTML = `
      <span style="color: ${color.border}; font-weight: 700; font-size: 16px;">${color.icon}</span>
      <span style="flex: 1;">${message}</span>
      <button style="background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 16px; padding: 0;">×</button>
    `;

    // Close button
    toast.querySelector('button').addEventListener('click', () => {
      this.removeToast(toast);
    });

    container.appendChild(toast);
    this.toasts.push(toast);

    // Auto-remove
    const timeoutId = setTimeout(() => {
      this.removeToast(toast);
    }, duration);

    toast.timeoutId = timeoutId;
  }

  removeToast(toast) {
    if (toast.timeoutId) clearTimeout(toast.timeoutId);
    toast.style.animation = 'slide-in-right 0.25s cubic-bezier(0.22, 1, 0.36, 1) reverse forwards';
    setTimeout(() => {
      toast.remove();
      this.toasts = this.toasts.filter((t) => t !== toast);
    }, 250);
  }
}

const toast = new ToastManager();

/* ============================================================================
   5. PAGE TRANSITION SYSTEM
   ============================================================================ */

function initPageTransitions() {
  // Add transition animation on all internal links
  document.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    if (!link) return;

    const href = link.getAttribute('href');
    if (!href || href.startsWith('http') || href.startsWith('//') || href.startsWith('#')) {
      return; // External link or anchor
    }

    e.preventDefault();

    // Fade out animation
    if (typeof gsap !== 'undefined') {
      gsap.to(document.body, {
        opacity: 0,
        scale: 0.99,
        duration: 0.18,
        ease: 'power2.in',
        onComplete: () => {
          window.location.href = href;
        },
      });
    } else {
      // Fallback
      document.body.style.opacity = '0';
      setTimeout(() => {
        window.location.href = href;
      }, 180);
    }
  });

  // Fade in animation on page load
  window.addEventListener('load', () => {
    if (typeof gsap !== 'undefined') {
      gsap.from(document.body, {
        opacity: 0,
        scale: 0.99,
        duration: 0.22,
        ease: 'power2.out',
      });
    } else {
      document.body.style.opacity = '1';
    }
  });

  console.log('✓ Page transitions initialized');
}

/* ============================================================================
   6. COMMAND PALETTE (Cmd+K / Ctrl+K)
   ============================================================================ */

class CommandPalette {
  constructor() {
    this.isOpen = false;
    this.selectedIndex = 0;
    this.init();
  }

  init() {
    // Create palette HTML
    const palette = document.createElement('div');
    palette.id = 'command-palette';
    palette.innerHTML = `
      <div style="position: fixed; inset: 0; background: rgba(5, 7, 15, 0.7); backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px); z-index: 10001; display: none;" id="palette-backdrop"></div>
      <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 10002; display: none;" id="palette-card">
        <div style="background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: var(--r-lg); backdrop-filter: blur(16px); width: 600px; max-width: 90vw; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);">
          <div style="padding: 16px; border-bottom: 1px solid var(--border-ghost);">
            <input type="text" id="palette-input" placeholder="Search commands..." style="width: 100%; background: transparent; border: none; color: var(--text-primary); font-size: 15px; outline: none;" />
          </div>
          <div id="palette-results" style="max-height: 400px; overflow-y: auto;"></div>
        </div>
      </div>
    `;
    document.body.appendChild(palette);

    // Commands
    this.commands = [
      { name: 'New Mission', action: () => this.navigateTo('/'), keys: 'N' },
      { name: 'Analytics', action: () => this.navigateTo('/?tab=analytics'), keys: 'A' },
      { name: 'History', action: () => this.navigateTo('/?tab=history'), keys: 'H' },
      { name: 'Settings', action: () => this.navigateTo('/?tab=settings'), keys: 'S' },
      { name: 'Sign Out', action: () => this.signOut(), keys: 'Q' },
    ];

    // Keyboard listeners
    document.addEventListener('keydown', (e) => {
      // Cmd+K / Ctrl+K
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        this.toggle();
      }

      // ESC to close
      if (e.key === 'Escape' && this.isOpen) {
        this.close();
      }

      // Arrow keys for navigation
      if (this.isOpen) {
        const results = document.querySelectorAll('.palette-item');
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          this.selectedIndex = Math.min(this.selectedIndex + 1, results.length - 1);
          this.updateSelection(results);
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
          this.updateSelection(results);
        } else if (e.key === 'Enter') {
          e.preventDefault();
          results[this.selectedIndex]?.click();
        }
      }
    });

    // Input listener
    document.getElementById('palette-input')?.addEventListener('input', (e) => {
      this.filterCommands(e.target.value);
    });

    // Backdrop click to close
    document.getElementById('palette-backdrop')?.addEventListener('click', () => {
      this.close();
    });
  }

  toggle() {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  open() {
    this.isOpen = true;
    this.selectedIndex = 0;
    document.getElementById('palette-backdrop').style.display = 'block';
    document.getElementById('palette-card').style.display = 'block';
    document.getElementById('palette-input').focus();
    this.filterCommands('');
  }

  close() {
    this.isOpen = false;
    document.getElementById('palette-backdrop').style.display = 'none';
    document.getElementById('palette-card').style.display = 'none';
    document.getElementById('palette-input').value = '';
  }

  filterCommands(query) {
    const results = document.getElementById('palette-results');
    const filtered = this.commands.filter((cmd) =>
      cmd.name.toLowerCase().includes(query.toLowerCase())
    );

    results.innerHTML = filtered
      .map(
        (cmd, index) => `
      <div class="palette-item" data-index="${index}" style="padding: 12px 16px; border-bottom: 1px solid var(--border-ghost); cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: background var(--t-fast); background: ${
          index === this.selectedIndex ? 'var(--bg-glass)' : 'transparent'
        }">
        <span style="color: var(--text-primary); font-size: 14px;">${cmd.name}</span>
        <span style="color: var(--text-muted); font-size: 11px; letter-spacing: 0.05em; text-transform: uppercase;">${cmd.keys}</span>
      </div>
    `
      )
      .join('');

    document.querySelectorAll('.palette-item').forEach((item) => {
      item.addEventListener('click', () => {
        const index = parseInt(item.dataset.index);
        filtered[index].action();
        this.close();
      });
    });
  }

  updateSelection(results) {
    results.forEach((item, index) => {
      item.style.background = index === this.selectedIndex ? 'var(--bg-glass)' : 'transparent';
    });
  }

  navigateTo(path) {
    window.location.href = path;
  }

  signOut() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_id');
    window.location.href = '/login.html';
  }
}

const commandPalette = new CommandPalette();

/* ============================================================================
   7. KEYBOARD SHORTCUTS & REFERENCE MODAL
   ============================================================================ */

function initKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // ? key to show shortcuts
    if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
      const input = document.activeElement;
      if (input.tagName !== 'INPUT' && input.tagName !== 'TEXTAREA') {
        showShortcutsModal();
      }
    }

    // Cmd+Enter / Ctrl+Enter to submit goal
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      const submitBtn = document.querySelector('[data-action="submit-goal"]');
      if (submitBtn) {
        e.preventDefault();
        submitBtn.click();
      }
    }
  });
}

function showShortcutsModal() {
  const modal = document.createElement('div');
  modal.style.cssText = `
    position: fixed;
    inset: 0;
    background: rgba(5, 7, 15, 0.7);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
  `;

  modal.innerHTML = `
    <div style="background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: var(--r-lg); backdrop-filter: blur(16px); padding: 32px; max-width: 500px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
        <h2 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0;">Keyboard Shortcuts</h2>
        <button style="background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 24px;">×</button>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; font-size: 13px; line-height: 1.8;">
        <div><kbd style="background: var(--bg-elevated); padding: 4px 8px; border-radius: 4px; margin-right: 8px;">Cmd+K</kbd>Command palette</div>
        <div><kbd style="background: var(--bg-elevated); padding: 4px 8px; border-radius: 4px; margin-right: 8px;">Cmd+↵</kbd>Submit goal</div>
        <div><kbd style="background: var(--bg-elevated); padding: 4px 8px; border-radius: 4px; margin-right: 8px;">N</kbd>New mission</div>
        <div><kbd style="background: var(--bg-elevated); padding: 4px 8px; border-radius: 4px; margin-right: 8px;">A</kbd>Analytics</div>
        <div><kbd style="background: var(--bg-elevated); padding: 4px 8px; border-radius: 4px; margin-right: 8px;">H</kbd>History</div>
        <div><kbd style="background: var(--bg-elevated); padding: 4px 8px; border-radius: 4px; margin-right: 8px;">?</kbd>Shortcuts</div>
      </div>
    </div>
  `;

  modal.querySelector('button').addEventListener('click', () => {
    modal.remove();
  });

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.remove();
    }
  });

  document.body.appendChild(modal);
}

/* ============================================================================
   8. AUTHENTICATION & SESSION MANAGEMENT
   ============================================================================ */

class AuthManager {
  constructor() {
    this.token = localStorage.getItem('auth_token');
    this.userId = localStorage.getItem('user_id');
    this.userData = null;
  }

  isLoggedIn() {
    return !!this.token && !!this.userId;
  }

  getToken() {
    return this.token;
  }

  getUserId() {
    return this.userId;
  }

  setSession(token, userId) {
    this.token = token;
    this.userId = userId;
    localStorage.setItem('auth_token', token);
    localStorage.setItem('user_id', userId);
  }

  clearSession() {
    this.token = null;
    this.userId = null;
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_data');
  }

  getAuthHeader() {
    return {
      Authorization: `Bearer ${this.token}`,
    };
  }

  async validateToken() {
    if (!this.token) {
      return false;
    }

    try {
      const response = await fetch('/api/auth/validate', {
        method: 'GET',
        headers: this.getAuthHeader(),
      });

      if (response.status === 401) {
        this.clearSession();
        return false;
      }

      return response.ok;
    } catch (error) {
      console.error('Token validation error:', error);
      return false;
    }
  }

  redirectToLogin() {
    window.location.href = '/login.html';
  }

  requireAuth() {
    if (!this.isLoggedIn()) {
      this.redirectToLogin();
      return false;
    }
    return true;
  }
}

const auth = new AuthManager();

/* ============================================================================
   9. INITIALIZATION & EXPORTS
   ============================================================================ */

async function initializeGlobalState() {
  try {
    // Configure logging
    if (typeof window !== 'undefined') {
      window.logger = logger;
      window.api = APIClient;
      window.auth = auth;
      window.store = globalStore;
    }

    // Initialize keyboard shortcuts
    initKeyboardShortcuts();

    // Validate session
    if (auth.isLoggedIn()) {
      const isValid = await auth.validateToken();
      if (!isValid) {
        auth.redirectToLogin();
        return;
      }
    }

    // Initialize global listeners
    setupGlobalErrorHandling();

    logger.info('Global state initialized');
  } catch (error) {
    logger.error('Global initialization error:', error);
    showErrorNotification('Failed to initialize application');
  }
}

function setupGlobalErrorHandling() {
  window.addEventListener('error', (event) => {
    logger.error('Uncaught error:', {
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
    });
  });

  window.addEventListener('unhandledrejection', (event) => {
    logger.error('Unhandled promise rejection:', {
      reason: event.reason,
    });
  });
}

function showErrorNotification(message) {
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: var(--color-error);
    color: white;
    padding: 16px 24px;
    border-radius: var(--r-md);
    z-index: 9999;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    animation: slideIn 0.3s ease-out;
  `;
  notification.textContent = message;
  document.body.appendChild(notification);

  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease-out';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initializeGlobalState);

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    APIClient,
    logger,
    auth,
    globalStore,
    NotificationManager,
    UIManager,
    initKeyboardShortcuts,
    showShortcutsModal,
    showErrorNotification,
  };
}
