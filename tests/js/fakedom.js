class FNode {
  constructor() { this.parentNode = null; this.childNodes = []; }
  get firstChild() { return this.childNodes[0] || null; }
  get lastChild() { return this.childNodes[this.childNodes.length - 1] || null; }
  appendChild(n) { if (n.parentNode) n.parentNode.removeChild(n); n.parentNode = this; this.childNodes.push(n); return n; }
  removeChild(n) { const i = this.childNodes.indexOf(n); if (i >= 0) { this.childNodes.splice(i, 1); n.parentNode = null; } return n; }
  replaceChild(a, b) { const i = this.childNodes.indexOf(b); if (i < 0) throw new Error('replaceChild: not a child'); if (a.parentNode) a.parentNode.removeChild(a); const j = this.childNodes.indexOf(b); this.childNodes[j] = a; a.parentNode = this; b.parentNode = null; return b; }
  contains(n) { for (let x = n; x; x = x.parentNode) if (x === this) return true; return false; }
  remove() { if (this.parentNode) this.parentNode.removeChild(this); }
  replaceWith(n) { if (this.parentNode) this.parentNode.replaceChild(n, this); }
}
export class FText extends FNode {
  constructor(t) { super(); this.nodeType = 3; this.data = String(t); }
  get textContent() { return this.data; }
  set textContent(v) { this.data = String(v); }
}
export class FEl extends FNode {
  constructor(tag) {
    super();
    this.nodeType = 1; this.tagName = tag.toUpperCase(); this.attrs = {}; this.style = { setProperty() {} }; this.dataset = {}; this.listeners = {};
    this.value = ''; this._html = ''; this.scrollTop = 0; this.scrollHeight = 900; this.files = [];
    const self = this;
    this.classList = {
      _get() { return (self.attrs.class || '').split(/\s+/).filter(Boolean); },
      add(c) { const l = this._get(); if (!l.includes(c)) l.push(c); self.attrs.class = l.join(' '); },
      remove(c) { self.attrs.class = this._get().filter((x) => x !== c).join(' '); },
      toggle(c, f) { const on = f === undefined ? !this.contains(c) : f; if (on) this.add(c); else this.remove(c); },
      contains(c) { return this._get().includes(c); },
    };
  }
  get clientWidth() { return 1200; }
  get clientHeight() { return 700; }
  get className() { return this.attrs.class || ''; }
  getBoundingClientRect() { return { width: 1200, height: 700 }; }
  setAttribute(k, v) { this.attrs[k] = String(v); if (k === 'hidden') this.hidden = true; }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  removeAttribute(k) { delete this.attrs[k]; if (k === 'hidden') this.hidden = false; }
  set innerHTML(v) { this._html = String(v); this.childNodes.forEach((c) => { c.parentNode = null; }); this.childNodes = []; }
  get innerHTML() { return this._html; }
  get textContent() { return this._html.replace(/<[^>]*>/g, '') + this.childNodes.map((c) => c.textContent).join(''); }
  set textContent(v) { this._html = ''; this.childNodes.forEach((c) => { c.parentNode = null; }); this.childNodes = []; this.appendChild(new FText(v)); }
  addEventListener(t, fn) { (this.listeners[t] = this.listeners[t] || []).push(fn); }
  removeEventListener(t, fn) { this.listeners[t] = (this.listeners[t] || []).filter((x) => x !== fn); }
  dispatchEvent(ev) {
    ev.target = ev.target || this;
    ev.preventDefault = ev.preventDefault || (() => {});
    ev.stopPropagation = () => { ev._stop = true; };
    for (let n = this; n && !ev._stop; n = n.parentNode) {
      ev.currentTarget = n;
      (n.listeners && n.listeners[ev.type] || []).slice().forEach((fn) => fn(ev));
    }
  }
  click() { this.dispatchEvent({ type: 'click' }); }
  focus() {}
  closest(sel) {
    const classes = sel.split(',').map((s) => s.trim().replace(/^\./, ''));
    for (let n = this; n && n.nodeType === 1; n = n.parentNode) if (classes.some((c) => n.classList.contains(c))) return n;
    return null;
  }
  querySelectorAll(sel) {
    const c = sel.replace(/^\./, '');
    const out = [];
    const walk = (n) => n.childNodes.forEach((k) => { if (k.nodeType === 1) { if (k.classList.contains(c)) out.push(k); walk(k); } });
    walk(this);
    return out;
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
}

export function install(fetchImpl) {
  const store = () => { const m = new Map(); return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k) }; };
  const body = new FEl('body');
  const root = new FEl('html');
  const byId = new Map();
  globalThis.document = {
    body, documentElement: root, hidden: false,
    createElement: (t) => new FEl(t), createElementNS: (ns, t) => new FEl(t), createTextNode: (t) => new FText(t),
    getElementById: (id) => byId.get(id) || null, addEventListener() {}, removeEventListener() {},
  };
  globalThis.__registerId = (id, el) => byId.set(id, el);
  globalThis.location = { hash: '#/', replace(h) { this.hash = h; } };
  const winListeners = {};
  globalThis.window = { addEventListener(t, fn) { (winListeners[t] = winListeners[t] || []).push(fn); }, __fire(t) { (winListeners[t] || []).forEach((fn) => fn({ type: t })); }, scrollTo() {}, innerWidth: 1200, innerHeight: 800, print() { globalThis.__printed = true; }, location: globalThis.location };
  globalThis.history = { back() {} };
  Object.defineProperty(globalThis, 'navigator', { value: {}, configurable: true });
  globalThis.localStorage = store();
  globalThis.sessionStorage = store();
  globalThis.fetch = fetchImpl;
  return { body, root };
}

export const all = (node, pred, out = []) => { node.childNodes.forEach((c) => { if (c.nodeType === 1) { if (pred(c)) out.push(c); all(c, pred, out); } }); return out; };
export const find = (node, pred) => all(node, pred)[0] || null;
export const text = (node) => node.textContent;
export const byClass = (node, cls) => all(node, (e) => e.classList.contains(cls));
export const byTag = (node, tag) => all(node, (e) => e.tagName === tag.toUpperCase());
export const byText = (node, tag, str) => all(node, (e) => e.tagName === tag.toUpperCase() && e.textContent.includes(str));
export const type = (el, v) => { el.value = v; el.dispatchEvent({ type: 'input' }); };
export const submit = (form) => form.dispatchEvent({ type: 'submit' });
export const tick = (ms = 20) => new Promise((r) => setTimeout(r, ms));
