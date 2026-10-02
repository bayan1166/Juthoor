import { iconSvg } from './icons.js';

const SVG_NS = 'http://www.w3.org/2000/svg';
const SVG_TAGS = new Set(['svg', 'path', 'circle', 'rect', 'g', 'defs', 'linearGradient', 'radialGradient', 'stop', 'text', 'ellipse', 'line', 'polygon']);

function applyProps(el, props) {
  for (const key of Object.keys(props)) {
    const value = props[key];
    if (value === null || value === undefined || value === false) continue;
    if (key === 'class' || key === 'className') {
      el.setAttribute('class', Array.isArray(value) ? value.filter(Boolean).join(' ') : value);
    } else if (key === 'style' && typeof value === 'object') {
      for (const name of Object.keys(value)) el.style[name] = value[name];
    } else if (key === 'html') {
      el.innerHTML = value;
    } else if (key === 'ref') {
      value(el);
    } else if (key === 'dataset') {
      for (const name of Object.keys(value)) el.dataset[name] = value[name];
    } else if (key.startsWith('on') && typeof value === 'function') {
      el.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key === 'value') {
      el.value = value;
      el.setAttribute('value', value);
    } else if (key === 'checked' || key === 'disabled' || key === 'selected' || key === 'hidden') {
      if (value) {
        el[key] = true;
        el.setAttribute(key, '');
      }
    } else if (value === true) {
      el.setAttribute(key, '');
    } else {
      el.setAttribute(key, String(value));
    }
  }
}

function appendChildren(el, children) {
  for (const child of children) {
    if (child === null || child === undefined || child === false || child === true) continue;
    if (Array.isArray(child)) appendChildren(el, child);
    else if (typeof child === 'object' && child.nodeType) el.appendChild(child);
    else el.appendChild(document.createTextNode(String(child)));
  }
}

export function h(tag, props, ...children) {
  const el = SVG_TAGS.has(tag) && tag !== 'text' ? document.createElementNS(SVG_NS, tag) : document.createElement(tag);
  if (props && !props.nodeType && !Array.isArray(props) && typeof props === 'object') applyProps(el, props);
  else if (props !== null && props !== undefined) children.unshift(props);
  appendChildren(el, children);
  return el;
}

export function clear(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
  return el;
}

export function mount(parent, ...nodes) {
  clear(parent);
  appendChildren(parent, nodes);
  return parent;
}

export function ico(name, cls = '') {
  return h('span', { class: ['ico', cls], html: iconSvg(name) });
}

export function esc(text) {
  return String(text ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

export function parseUtc(iso) {
  if (!iso) return null;
  const hasZone = /[zZ]|[+-]\d\d:?\d\d$/.test(iso);
  const date = new Date(hasZone ? iso : `${iso}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function fmtDate(iso, withTime = false) {
  const date = parseUtc(iso);
  if (!date) return '';
  const opts = withTime ? { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' } : { year: 'numeric', month: 'short', day: 'numeric' };
  return date.toLocaleString('ar-u-nu-latn', opts);
}

export function fmtTime(iso) {
  const date = parseUtc(iso);
  return date ? date.toLocaleTimeString('ar-u-nu-latn', { hour: '2-digit', minute: '2-digit' }) : '';
}

export function dayLabel(iso) {
  const date = parseUtc(iso);
  if (!date) return '';
  const today = new Date();
  const start = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diff = Math.round((start(today) - start(date)) / 86400000);
  if (diff === 0) return 'اليوم';
  if (diff === 1) return 'أمس';
  return date.toLocaleDateString('ar-u-nu-latn', { day: 'numeric', month: 'long' });
}

export function timeAgo(iso) {
  const date = parseUtc(iso);
  if (!date) return 'لم يبدأ بعد';
  const mins = Math.floor((Date.now() - date.getTime()) / 60000);
  if (mins < 1) return 'الآن';
  if (mins < 60) return `منذ ${mins} دقيقة`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `منذ ${hours} ساعة`;
  const days = Math.floor(hours / 24);
  return days === 1 ? 'منذ يوم' : `منذ ${days} أيام`;
}

export function jod(minor) {
  return (minor / 1000).toFixed(2);
}

export function pct(value) {
  return value === null || value === undefined ? '-' : `${Math.round(value * 100)}%`;
}

export function initial(name) {
  return (name || '?').trim().charAt(0);
}

export function debounce(fn, ms) {
  let timer = null;
  const wrapped = (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
  wrapped.cancel = () => clearTimeout(timer);
  return wrapped;
}

export function countTo(el, to, ms = 700, suffix = '') {
  const target = Number(to) || 0;
  if (typeof requestAnimationFrame !== 'function' || ms <= 0) {
    el.textContent = `${target}${suffix}`;
    return;
  }
  const from = Number(el.dataset.v || 0);
  const start = performance.now();
  el.dataset.v = String(target);
  const step = (now) => {
    const t = Math.min(1, (now - start) / ms);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = `${Math.round(from + (target - from) * eased)}${suffix}`;
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

export function avatarEl(person, size = '') {
  const el = h('span', { class: ['avatar', size] });
  if (person && person.avatar_svg) el.innerHTML = person.avatar_svg;
  else el.textContent = initial(person && person.full_name);
  return el;
}

export function mathBdi(segments) {
  return segments.map((s) => (s.m ? h('bdi', { class: 'm' }, s.t) : s.t));
}

export function skeleton(lines = 3, block = false) {
  const wrap = h('div', { class: 'col' });
  if (block) wrap.appendChild(h('div', { class: 'skeleton sk-block' }));
  for (let i = 0; i < lines; i += 1) wrap.appendChild(h('div', { class: 'skeleton sk-line', style: { width: `${95 - i * 12}%` } }));
  return wrap;
}

let toastBox = null;

export function toast(message, kind = 'info', ms = 3600) {
  if (!toastBox || !toastBox.parentNode) {
    toastBox = h('div', { class: 'toasts', role: 'status', 'aria-live': 'polite' });
    document.body.appendChild(toastBox);
  }
  const node = h('div', { class: ['toast', kind] }, message);
  toastBox.appendChild(node);
  setTimeout(() => {
    node.classList.add('out');
    setTimeout(() => node.remove(), 260);
  }, ms);
}

export function openModal({ title, content, actions = [], size = '', persistent = false, onClose }) {
  const back = h('div', { class: 'modal-back' });
  const box = h('div', { class: ['modal', size], role: 'dialog', 'aria-modal': 'true' });
  const close = () => {
    document.removeEventListener('keydown', onKey);
    back.remove();
    if (onClose) onClose();
  };
  const onKey = (e) => {
    if (e.key === 'Escape' && !persistent) close();
  };
  const head = h('div', { class: 'mh' }, h('h3', { style: { margin: 0 } }, title || ''), h('button', { class: 'icon-btn', 'aria-label': 'إغلاق', onclick: close }, ico('x')));
  const body = h('div', { class: 'mb' }, content);
  box.appendChild(head);
  box.appendChild(body);
  if (actions.length) {
    const foot = h('div', { class: 'mf' });
    for (const a of actions) {
      foot.appendChild(h('button', {
        class: ['btn', a.kind === 'primary' ? 'btn-primary' : a.kind === 'danger' ? 'btn-danger' : 'btn-ghost'],
        onclick: async (e) => {
          const btn = e.currentTarget;
          if (a.onClick) {
            btn.classList.add('is-busy');
            try {
              const keep = await a.onClick({ close, body });
              if (keep === false) return;
            } finally {
              btn.classList.remove('is-busy');
            }
          }
          if (a.close !== false) close();
        },
      }, a.label));
    }
    box.appendChild(foot);
  }
  back.appendChild(box);
  if (!persistent) back.addEventListener('mousedown', (e) => { if (e.target === back) close(); });
  document.addEventListener('keydown', onKey);
  document.body.appendChild(back);
  return { close, el: box, body };
}

export function confirmDialog(message, { title = 'تأكيد', confirmLabel = 'تأكيد', danger = false } = {}) {
  return new Promise((resolve) => {
    let settled = false;
    const done = (v) => { if (!settled) { settled = true; resolve(v); } };
    openModal({
      title,
      content: h('p', null, message),
      onClose: () => done(false),
      actions: [
        { label: 'إلغاء', kind: 'ghost', onClick: () => done(false) },
        { label: confirmLabel, kind: danger ? 'danger' : 'primary', onClick: () => done(true) },
      ],
    });
  });
}

export function openDrawer({ title, content, onClose }) {
  const back = h('div', { class: 'drawer-back' });
  const drawer = h('aside', { class: 'drawer', role: 'dialog', 'aria-modal': 'true' });
  const close = () => {
    document.removeEventListener('keydown', onKey);
    back.remove();
    drawer.remove();
    if (onClose) onClose();
  };
  const onKey = (e) => { if (e.key === 'Escape') close(); };
  drawer.appendChild(h('div', { class: 'dh' }, h('h3', { style: { margin: 0 } }, title), h('button', { class: 'icon-btn', 'aria-label': 'إغلاق', onclick: close }, ico('x'))));
  const body = h('div', { class: 'db' }, content);
  drawer.appendChild(body);
  back.addEventListener('mousedown', close);
  document.addEventListener('keydown', onKey);
  document.body.appendChild(back);
  document.body.appendChild(drawer);
  return { close, body };
}

export function copyText(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(text).then(() => true).catch(() => false);
  return Promise.resolve(false);
}
