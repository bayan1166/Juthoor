import { h, ico, mount, clear, toast, countTo } from './dom.js';
import { setToken, setExpiredHandler, getToken } from './api.js';
import { store, on, applyTheme, getTheme, setTheme, loadHealth, loadMe, loadBoot, refreshSummary, logout, planLabel, isStudent } from './store.js';
import { brandHtml } from './icons.js';
import { authView } from './views/auth.js';
import { homeView } from './views/home.js';
import { practiceView } from './views/practice.js';
import { tutorView } from './views/tutor.js';
import { shopView } from './views/shop.js';
import { communityView } from './views/social.js';
import { parentView, reportView } from './views/parent.js';
import { plansView, checkoutView } from './views/plans.js';
import { errorPanel } from './views/shared.js';

// B2C roles. platform_admin is an internal moderation account with no learning screens.
const INTERNAL = ['platform_admin'];

const ROUTES = [
  { path: '/login', public: true, view: authView, params: { mode: 'login' } },
  { path: '/register', public: true, view: authView, params: { mode: 'register' } },
  { path: '/', roles: ['student'], view: homeView },
  { path: '/', roles: INTERNAL, view: internalView },
  { path: '/', roles: ['parent'], view: parentView },
  { path: '/practice', roles: ['student'], view: practiceView },
  { path: '/tutor', roles: ['student'], view: tutorView },
  { path: '/shop', roles: ['student'], view: shopView },
  { path: '/community', roles: ['*'], view: communityView },
  { path: '/plans', roles: ['*'], view: plansView },
  { path: '/checkout/:plan', roles: ['*'], view: checkoutView },
  { path: '/report/:id', roles: ['*'], view: reportView },
];

function internalView(ctx) {
  ctx.root.appendChild(h('div', { class: 'page page-enter' }, h('div', { class: 'empty card' }, ico('shield'),
    h('h3', null, 'حساب تشغيلي داخلي'),
    h('p', { class: 'muted' }, 'هذا الحساب مخصص لفريق الإشراف في جذور، ولا يملك واجهة تعلّم أو اشتراك.'))));
}

let app = null;
let navHost = null;
let mainEl = null;
let tabHost = null;
let current = null;
let summaryTimer = null;
let navOffs = [];

// Judge mode keeps the demo focused on the diagnosis flow; the Pro/upgrade entry is never hidden.
export const JUDGE_HIDDEN = ['/community', '/shop'];

export function linksFor(role) {
  const all = baseLinks(role);
  return store.health && store.health.judge ? all.filter(([to]) => !JUDGE_HIDDEN.includes(to)) : all;
}

function baseLinks(role) {
  if (role === 'student') return [['/', 'الرئيسية', 'tree'], ['/practice', 'التدريب', 'pencil'], ['/tutor', 'المساعد الذكي', 'spark'], ['/community', 'المجتمع', 'chat'], ['/shop', 'المتجر', 'bag'], ['/plans', 'برو', 'bolt']];
  if (role === 'parent') return [['/', 'أبنائي', 'users'], ['/community', 'المجتمع', 'chat'], ['/plans', 'برو', 'bolt']];
  return [];
}

export function parseHash(hash) {
  const raw = (hash || '').replace(/^#/, '') || '/';
  const [path, q] = raw.split('?');
  const query = {};
  new URLSearchParams(q || '').forEach((v, k) => { query[k] = v; });
  return { path: path || '/', query };
}

export function matchRoute(path, role) {
  const parts = path.split('/').filter(Boolean);
  for (const route of ROUTES) {
    const segs = route.path.split('/').filter(Boolean);
    if (segs.length !== parts.length) continue;
    const params = { ...(route.params || {}) };
    let ok = true;
    segs.forEach((seg, i) => {
      if (seg.startsWith(':')) params[seg.slice(1)] = decodeURIComponent(parts[i]);
      else if (seg !== parts[i]) ok = false;
    });
    if (!ok) continue;
    if (route.roles && !route.roles.includes('*') && role && !route.roles.includes(role)) continue;
    return { route, params };
  }
  return null;
}

function go(hash) {
  if (location.hash === hash) route();
  else location.hash = hash;
}

function badge(count) {
  return count > 0 ? h('span', { class: 'dot' }, count > 9 ? '9+' : String(count)) : null;
}

function paintNav() {
  navOffs.forEach((off) => off());
  navOffs = [];
  clear(navHost);
  clear(tabHost);
  if (!store.me) return;
  const me = store.me;
  const links = linksFor(me.role);
  const isInternalRole = INTERNAL.includes(me.role);
  const { path } = parseHash(location.hash);
  const linkEls = [];
  const tabEls = [];
  const communityDots = [];
  links.forEach(([to, label, icon]) => {
    const active = to === '/' ? path === '/' : path.startsWith(to);
    const dot = to === '/community' ? h('span') : null;
    const el = h('a', { class: ['nav-link', active ? 'on' : ''], href: `#${to}` }, ico(icon), h('span', null, label), dot);
    const tdot = to === '/community' ? h('span') : null;
    const tab = h('a', { class: [active ? 'on' : ''], href: `#${to}` }, ico(icon), h('span', null, label), tdot);
    if (dot) communityDots.push([el, dot], [tab, tdot]);
    linkEls.push(el);
    tabEls.push(tab);
  });
  const paintDots = () => {
    const n = store.summary.unread_messages + store.summary.pending_requests;
    communityDots.forEach(([host, slot]) => {
      const fresh = badge(n) || h('span');
      host.replaceChild(fresh, slot);
      communityDots[communityDots.findIndex((x) => x[1] === slot)][1] = fresh;
    });
  };
  navOffs.push(on('summary', paintDots));

  const coinEl = h('b', null, '0');
  const gemEl = h('b', null, '0');
  const wallet = isStudent() ? h('div', { class: 'row nowrap', style: { gap: '8px' } }, h('span', { class: 'pill coin', title: 'العملات' }, ico('coin'), coinEl), h('span', { class: 'pill gem hide-sm', title: 'الجواهر' }, ico('gem'), gemEl)) : null;
  const paintWallet = () => {
    if (!store.boot) return;
    countTo(coinEl, store.boot.wallet.coins, 500);
    countTo(gemEl, store.boot.wallet.gems, 500);
  };
  if (wallet) {
    navOffs.push(on('boot', paintWallet));
    loadBoot().then(paintWallet).catch(() => null);
  }

  const upgradeBtn = !isInternalRole && me.plan !== 'pro'
    ? h('a', { class: 'btn btn-primary btn-sm upgrade-cta', href: '#/plans', 'data-testid': 'upgrade-cta' }, ico('bolt'), h('span', null, 'ترقية إلى برو'))
    : null;
  const themeBtn = h('button', { class: 'icon-btn', 'aria-label': 'تبديل المظهر' }, ico(getTheme() === 'dark' ? 'sun' : 'moon'));
  themeBtn.addEventListener('click', () => {
    const next = getTheme() === 'dark' ? 'light' : 'dark';
    setTheme(next);
    clear(themeBtn);
    themeBtn.appendChild(ico(next === 'dark' ? 'sun' : 'moon'));
  });

  const menuWrap = h('div', { class: 'menu-wrap' });
  const avatarBtn = h('button', { class: 'icon-btn', style: { padding: 0, overflow: 'hidden' }, 'aria-label': 'الحساب', 'aria-haspopup': 'true' });
  const paintAvatar = () => {
    clear(avatarBtn);
    if (store.boot && store.boot.avatar_svg) avatarBtn.innerHTML = store.boot.avatar_svg;
    else avatarBtn.appendChild(ico('user'));
  };
  paintAvatar();
  if (wallet) navOffs.push(on('boot', paintAvatar));
  let menu = null;
  const closeMenu = () => {
    if (menu) {
      menu.remove();
      menu = null;
    }
  };
  const outside = (e) => {
    if (menu && !menuWrap.contains(e.target)) closeMenu();
  };
  document.addEventListener('click', outside);
  navOffs.push(() => document.removeEventListener('click', outside));
  avatarBtn.addEventListener('click', () => {
    if (menu) {
      closeMenu();
      return;
    }
    const planText = isInternalRole ? 'حساب داخلي' : planLabel(me.plan);
    menu = h('div', { class: 'menu', role: 'menu' },
      h('div', { class: 'col', style: { gap: '4px', padding: '4px 4px 0' } }, h('b', null, me.full_name), h('span', { class: 'small muted' }, me.email),
        h('div', { class: 'row', style: { marginTop: '6px' } }, h('span', { class: ['chip', me.plan === 'basic' ? '' : 'green'] }, planText), me.handle ? h('span', { class: 'chip ltr' }, `#${me.handle}`) : null)),
      h('hr'),
      isInternalRole ? null : h('a', { class: 'item', href: '#/plans', onclick: closeMenu }, ico('card'), me.plan === 'pro' ? 'اشتراك برو' : 'ترقية إلى برو'),
      h('button', { class: 'item', onclick: () => { closeMenu(); logout(); paintNav(); clearInterval(summaryTimer); go('#/login'); } }, ico('logout'), 'تسجيل الخروج'));
    menuWrap.appendChild(menu);
  });
  menuWrap.appendChild(avatarBtn);

  navHost.appendChild(h('nav', { class: 'nav', 'aria-label': 'التنقل الرئيسي' },
    h('a', { class: 'brand', href: '#/', html: brandHtml() }),
    h('div', { class: 'nav-links' }, linkEls),
    h('div', { class: 'nav-right' }, wallet, upgradeBtn, themeBtn, menuWrap)));
  tabHost.appendChild(h('div', { class: 'tabbar' }, tabEls));
  paintDots();
}

function startSummary() {
  clearInterval(summaryTimer);
  refreshSummary();
  summaryTimer = setInterval(() => { if (!document.hidden && store.me) refreshSummary(); }, 20000);
}

async function login(token, landing = '#/') {
  setToken(token);
  store.boot = null;
  await loadMe();
  paintNav();
  startSummary();
  go(landing);
}

async function route() {
  if (current) {
    current.destroyed = true;
    for (const fn of current.cbs) {
      try {
        fn();
      } catch (e) {
        continue;
      }
    }
    current = null;
  }
  const { path, query } = parseHash(location.hash);
  const found = matchRoute(path, store.me && store.me.role);
  if (!found) {
    location.replace(store.me ? '#/' : '#/login');
    return;
  }
  const isPublic = !!found.route.public;
  if (!store.me && !isPublic) {
    location.replace('#/login');
    return;
  }
  if (store.me && isPublic) {
    location.replace('#/');
    return;
  }
  const root = h('div', { class: 'view-root page-enter' });
  const ctx = {
    root, params: found.params, query, destroyed: false, cbs: [],
    onDestroy(fn) {
      if (ctx.destroyed) fn();
      else ctx.cbs.push(fn);
    },
    login,
    reload: () => route(),
    refreshShell: paintNav,
    navigate: go,
  };
  current = ctx;
  mount(mainEl, root);
  paintNav();
  window.scrollTo(0, 0);
  try {
    await found.route.view(ctx);
  } catch (err) {
    if (!ctx.destroyed) mount(root, h('div', { class: 'page' }, errorPanel(err, () => route())));
  }
}

function dismissSplash() {
  const splash = document.getElementById('splash');
  if (!splash) return;
  splash.classList.add('done');
  setTimeout(() => splash.remove(), 450);
}

async function start() {
  applyTheme();
  app = document.getElementById('app');
  navHost = h('div');
  mainEl = h('main', { class: 'view', id: 'view' });
  tabHost = h('div');
  mount(app, navHost, mainEl, tabHost);
  setExpiredHandler(() => {
    logout();
    paintNav();
    clearInterval(summaryTimer);
    toast('انتهت الجلسة، سجّل الدخول من جديد.', 'info');
    go('#/login');
  });
  await Promise.race([loadHealth(), new Promise((resolve) => setTimeout(resolve, 1500))]);
  if (getToken()) {
    try {
      await loadMe();
      startSummary();
    } catch (err) {
      if (err.status === 401 || err.status === 403) logout();
    }
  }
  window.addEventListener('hashchange', route);
  await route();
  dismissSplash();
}

if (typeof document !== 'undefined' && document.getElementById('app')) {
  start().catch(() => dismissSplash());
}
