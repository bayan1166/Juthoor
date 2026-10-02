import { h, mount, clear } from '../dom.js';
import { api } from '../api.js';
import { store, on } from '../store.js';
import { renderTreeStage } from '../tree.js';
import { errorPanel } from './shared.js';

let cached = null;

on('logout', () => { cached = null; });

export async function homeView(ctx) {
  const uid = store.me.user_id;
  const holder = h('div');
  ctx.root.appendChild(holder);
  let ctrl = null;

  function show(data) {
    if (ctrl) {
      ctrl.update(data);
      return;
    }
    clear(holder);
    ctrl = renderTreeStage(holder, data, { studentId: uid, canPractice: true });
  }

  async function load() {
    if (cached && cached.uid === uid) show(cached.data);
    else mount(holder, h('div', { class: 'stage' }, h('div', { class: 'empty', style: { position: 'absolute', inset: '0' } }, h('div', { class: 'spin' }), h('span', null, 'نزرع شجرتك...'))));
    try {
      const data = await api.get(`/students/${uid}/adaptive/tree`);
      const changed = !cached || cached.uid !== uid || JSON.stringify(cached.data) !== JSON.stringify(data);
      cached = { uid, data };
      store.treeStale = false;
      if (changed || !ctrl) show(data);
    } catch (err) {
      if (!ctrl) mount(holder, h('div', { class: 'page' }, errorPanel(err, load)));
    }
  }

  ctx.onDestroy(() => { if (ctrl) ctrl.destroy(); });
  await load();
}
