import { api, getToken, setToken } from './api.js';

export const store = {
  me: null,
  boot: null,
  health: { demo: false, ai_tutor: 'offline_fallback' },
  summary: { unread_messages: 0, pending_requests: 0 },
  treeStale: true,
};

const listeners = new Map();

export function on(event, fn) {
  if (!listeners.has(event)) listeners.set(event, new Set());
  listeners.get(event).add(fn);
  return () => listeners.get(event).delete(fn);
}

export function emit(event, payload) {
  const set = listeners.get(event);
  if (set) for (const fn of Array.from(set)) fn(payload);
}

export function getTheme() {
  try {
    return localStorage.getItem('juthoor.theme') === 'dark' ? 'dark' : 'light';
  } catch (e) {
    return 'light';
  }
}

export function setTheme(theme) {
  try {
    localStorage.setItem('juthoor.theme', theme);
  } catch (e) {
    theme = theme === 'dark' ? 'dark' : 'light';
  }
  document.documentElement.setAttribute('data-theme', theme);
  emit('theme', theme);
}

export function applyTheme() {
  document.documentElement.setAttribute('data-theme', getTheme());
}

export function isStudent() {
  return !!store.me && store.me.role === 'student';
}

// Internal operations account (moderation). It has no learning screens and never buys anything.
export function isInternal() {
  return !!store.me && store.me.role === 'platform_admin';
}

export function isParent() {
  return !!store.me && store.me.role === 'parent';
}

export async function loadHealth() {
  try {
    store.health = await api.get('/health', { ttl: 60000 });
  } catch (e) {
    store.health = { demo: false, ai_tutor: 'offline_fallback' };
  }
  return store.health;
}

export async function loadMe() {
  store.me = await api.get('/auth/me');
  return store.me;
}

export async function loadBoot(force = false) {
  if (!isStudent()) return null;
  if (store.boot && !force) return store.boot;
  store.boot = await api.get(`/students/${store.me.user_id}/adaptive/bootstrap`);
  emit('boot', store.boot);
  return store.boot;
}

export function patchBoot(patch) {
  if (!store.boot) return;
  store.boot = { ...store.boot, ...patch };
  emit('boot', store.boot);
}

export function addWallet(coins = 0, gems = 0) {
  if (!store.boot || (!coins && !gems)) return;
  const wallet = { coins: store.boot.wallet.coins + coins, gems: store.boot.wallet.gems + gems };
  patchBoot({ wallet });
}

export async function refreshSummary() {
  if (!store.me) return;
  try {
    store.summary = await api.get('/community/summary');
    emit('summary', store.summary);
  } catch (e) {
    return;
  }
}

export function login(token) {
  setToken(token);
}

export function logout() {
  setToken('');
  store.me = null;
  store.boot = null;
  store.treeStale = true;
  api.invalidate();
  emit('logout');
}

export function hasSession() {
  return !!getToken();
}

export function planLabel(plan) {
  return { basic: 'المجانية', pro: 'برو' }[plan] || plan;
}
