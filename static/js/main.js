/**
 * main.js – shared utilities for Campus Network Fault Reporter
 * -------------------------------------------------------------
 * - Count-up animation for stat cards
 * - Toast notification helper
 * - Dark mode toggle
 * - Generic fetch helper with loading state
 */

/* ------------------------------------------------------------------ */
/*  Count-up animation                                                  */
/* ------------------------------------------------------------------ */
function animateCountUp(el, target, duration = 900) {
  const start    = 0;
  const startTime = performance.now();
  function step(now) {
    const elapsed  = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // ease-out cubic
    const ease = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.floor(ease * target);
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = target;
  }
  requestAnimationFrame(step);
}

function initCountUps() {
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = parseInt(el.dataset.count, 10) || 0;
    animateCountUp(el, target);
  });
}

/* ------------------------------------------------------------------ */
/*  Toast helper                                                        */
/* ------------------------------------------------------------------ */
function showToast(message, type = 'success', duration = 4000) {
  // type: 'success' | 'warning' | 'info'
  const colors = {
    success: 'var(--emerald)',
    warning: 'var(--amber)',
    info:    'var(--primary)',
    error:   'var(--orange)',
  };
  const icons = {
    success: 'bi-check-circle-fill',
    warning: 'bi-exclamation-triangle-fill',
    info:    'bi-info-circle-fill',
    error:   'bi-x-circle-fill',
  };

  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(container);
  }

  const id   = 'toast-' + Date.now();
  const html = `
    <div id="${id}" class="toast align-items-center border-0 show" role="alert"
         style="border-left: 4px solid ${colors[type] || colors.info} !important;">
      <div class="d-flex">
        <div class="toast-body d-flex align-items-center gap-2">
          <i class="bi ${icons[type] || icons.info}" style="color:${colors[type]}; font-size:1.1rem;"></i>
          <span>${message}</span>
        </div>
        <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    </div>`;
  container.insertAdjacentHTML('beforeend', html);
  const toastEl = document.getElementById(id);
  setTimeout(() => {
    toastEl.classList.remove('show');
    setTimeout(() => toastEl.remove(), 400);
  }, duration);
}

/* ------------------------------------------------------------------ */
/*  Generic JSON fetch helper                                           */
/* ------------------------------------------------------------------ */
async function apiFetch(url, options = {}) {
  const defaults = {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
  };
  const cfg = Object.assign({}, defaults, options);
  const res = await fetch(url, cfg);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Network error' }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

/* ------------------------------------------------------------------ */
/*  Badge helpers                                                       */
/* ------------------------------------------------------------------ */
function priorityBadge(priority) {
  const cls = {
    'High':   'badge-priority-high',
    'Medium': 'badge-priority-medium',
    'Low':    'badge-priority-low',
  };
  return `<span class="badge ${cls[priority] || ''}">${priority}</span>`;
}

function statusBadge(status) {
  const key = status.toLowerCase().replace(/ /g, '-');
  return `<span class="badge badge-status-${key}">${status}</span>`;
}

function categoryBadge(category) {
  const key = category.toLowerCase();
  return `<span class="badge badge-cat-${key}">${category}</span>`;
}

function availabilityBadge(avail) {
  const cls = avail === 'Available' ? 'badge-available' : 'badge-busy';
  const icon = avail === 'Available' ? 'bi-circle-fill' : 'bi-dash-circle-fill';
  return `<span class="badge ${cls}"><i class="bi ${icon} me-1" style="font-size:.6rem;"></i>${avail}</span>`;
}

/* ------------------------------------------------------------------ */
/*  Dark mode toggle                                                    */
/* ------------------------------------------------------------------ */
function initDarkMode() {
  const toggle = document.getElementById('darkModeToggle');
  if (!toggle) return;

  const saved = localStorage.getItem('darkMode');
  if (saved === 'true') document.body.classList.add('dark-mode');
  toggle.checked = document.body.classList.contains('dark-mode');

  toggle.addEventListener('change', () => {
    document.body.classList.toggle('dark-mode', toggle.checked);
    localStorage.setItem('darkMode', toggle.checked);
  });
}

/* ------------------------------------------------------------------ */
/*  Clipboard copy                                                       */
/* ------------------------------------------------------------------ */
function copyToClipboard(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.innerHTML;
    btn.innerHTML = '<i class="bi bi-check2"></i> Copied!';
    btn.disabled = true;
    setTimeout(() => { btn.innerHTML = orig; btn.disabled = false; }, 2000);
    showToast('Complaint ID copied to clipboard!', 'success');
  });
}

/* ------------------------------------------------------------------ */
/*  Table search / filter                                               */
/* ------------------------------------------------------------------ */
function initTableSearch(inputId, tableId) {
  const input = document.getElementById(inputId);
  const table = document.getElementById(tableId);
  if (!input || !table) return;

  input.addEventListener('input', () => {
    const q = input.value.toLowerCase();
    table.querySelectorAll('tbody tr').forEach(row => {
      row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  });
}

/* ------------------------------------------------------------------ */
/*  Auto-init on DOM ready                                               */
/* ------------------------------------------------------------------ */
document.addEventListener('DOMContentLoaded', () => {
  initCountUps();
  initDarkMode();

  // Fade-in page content
  document.querySelectorAll('.fade-in').forEach((el, i) => {
    el.style.animationDelay = `${i * 0.07}s`;
  });
});
