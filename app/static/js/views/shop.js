import { h, ico, mount, clear, toast, openModal, countTo } from '../dom.js';
import { api } from '../api.js';
import { store, loadBoot, patchBoot, on } from '../store.js';
import { errorPanel, handleError } from './shared.js';

const CATS = [
  ['clothing', 'الملابس'],
  ['top', 'غطاء الرأس'],
  ['neck', 'الرقبة'],
  ['accessories', 'الإكسسوارات'],
  ['look', 'المظهر'],
];
const GROUP_LABEL = {
  tees: 'تيشيرتات', hoodies: 'هوديات', jackets: 'جاكيتات ومعاطف', heritage: 'الزي التراثي', jobs: 'بدلات المهن',
  caps: 'قبعات', winter: 'طواقي شتوية', heritage_head: 'شماغ وحطة', hijab: 'حجاب', jobcaps: 'قبعات المهن',
  scarves: 'لفحات', glasses: 'نظارات',
};
const DEFAULTS = { top: 'none', neck: 'none', accessories: 'blank' };

function retarget(svg, from, to) {
  return svg.split(from).join(to);
}

export async function shopView(ctx) {
  const uid = store.me.user_id;
  const base = `/students/${uid}/economy`;
  const page = h('div', { class: 'page page-enter wide' });
  ctx.root.appendChild(page);
  let catalog = [];
  let options = { skins: [], hair_styles: [], hair_colors: [] };
  let previews = {};
  let cat = 'clothing';
  let group = '';
  let saving = false;
  let previewTimer = null;

  const previewAv = h('div', { class: 'preview-av' });
  const coinEl = h('b', null, '0');
  const gemEl = h('b', null, '0');
  const content = h('div', { class: 'card' });
  const catTabs = h('div', { class: 'tabs' });
  const groupRow = h('div', { class: 'row', style: { margin: '14px 0' } });
  const grid = h('div');
  content.appendChild(catTabs);
  content.appendChild(groupRow);
  content.appendChild(grid);

  const side = h('div', { class: 'card preview-card' },
    previewAv,
    h('div', { class: 'row', style: { justifyContent: 'center' } },
      h('span', { class: 'pill coin' }, ico('coin'), coinEl), h('span', { class: 'pill gem' }, ico('gem'), gemEl)),
    h('p', { class: 'muted small', style: { marginTop: '10px' } }, 'اضغط أي قطعة لتجربتها فوراً. القطع المملوكة تُلبَس بضغطة واحدة.'));
  page.appendChild(h('div', { class: 'page-head' }, h('div', null, h('h1', null, 'متجر الشخصية'), h('p', { class: 'muted' }, 'اجمع العملات من التدريب وخصّص شخصيتك.'))));
  page.appendChild(h('div', { class: 'shop-layout' }, side, content));

  function paintPreview() {
    if (store.boot && store.boot.avatar_svg) previewAv.innerHTML = store.boot.avatar_svg;
    const w = store.boot ? store.boot.wallet : { coins: 0, gems: 0 };
    countTo(coinEl, w.coins, 500);
    countTo(gemEl, w.gems, 500);
  }
  const off = on('boot', paintPreview);
  ctx.onDestroy(() => { off(); clearTimeout(previewTimer); });

  async function loadPreviews() {
    try {
      previews = await api.get(`${base}/previews`);
      paintGrid();
    } catch (e) {
      previews = previews || {};
    }
  }

  function schedulePreviews() {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(loadPreviews, 350);
  }

  async function apply(next, guess) {
    const prev = { avatar: store.boot.avatar, avatar_svg: store.boot.avatar_svg };
    patchBoot({ avatar: next, avatar_svg: guess || prev.avatar_svg });
    paintGrid();
    saving = true;
    try {
      const res = await api.put(`${base}/avatar`, next);
      patchBoot({ avatar_svg: res.svg });
      schedulePreviews();
    } catch (err) {
      patchBoot(prev);
      paintGrid();
      handleError(err);
    } finally {
      saving = false;
    }
  }

  function guessFor(key) {
    const p = previews[key];
    return p ? retarget(p.svg, p.uid, 'me') : null;
  }

  function equipItem(item) {
    const next = { ...store.boot.avatar, [item.category]: item.id };
    for (const [c, id] of item.bundle || []) next[c] = id;
    apply(next, guessFor(`i:${item.id}`));
  }

  function price(item) {
    if (item.price_gems > 0) return h('span', { class: 'chip lime' }, ico('gem'), String(item.price_gems));
    if (item.price_coins > 0) return h('span', { class: 'chip' }, ico('coin'), String(item.price_coins));
    return h('span', { class: 'chip green' }, 'مجاني');
  }

  function buy(item) {
    const useGems = item.price_gems > 0;
    const wallet = store.boot.wallet;
    const cost = useGems ? item.price_gems : item.price_coins;
    const have = useGems ? wallet.gems : wallet.coins;
    const enough = have >= cost;
    const pv = previews[`i:${item.id}`];
    const modal = openModal({
      title: item.name,
      content: h('div', { class: 'col center' },
        h('div', { class: 'preview-av', style: { maxWidth: '200px' }, html: pv ? pv.svg : '' }),
        h('div', { class: 'row', style: { justifyContent: 'center' } }, price(item), h('span', { class: 'muted small' }, `رصيدك: ${have}`)),
        enough ? null : h('div', { class: 'err' }, useGems ? 'رصيدك من الجواهر لا يكفي.' : 'رصيدك من العملات لا يكفي، تابع التدريب لتجمع المزيد.')),
      actions: [
        { label: 'إلغاء', kind: 'ghost' },
        enough ? {
          label: 'اشترِ وارتدِ', kind: 'primary', close: false,
          onClick: async () => {
            try {
              const res = await api.post(`${base}/purchase`, { item_id: item.id, currency: useGems ? 'gems' : 'coins' });
              if (!res.success) {
                toast(res.message === 'already_owned' ? 'تملك هذه القطعة مسبقاً.' : 'تعذّر الشراء.', 'error');
              } else {
                patchBoot({ wallet: { coins: res.wallet.coins, gems: res.wallet.gems } });
              }
              item.owned = true;
              modal.close();
              equipItem(item);
              toast('تم الشراء والارتداء.', 'success');
            } catch (err) {
              handleError(err);
              return false;
            }
            return true;
          },
        } : null,
      ].filter(Boolean),
    });
  }

  function itemCard(item) {
    const on = store.boot.avatar[item.category] === item.id;
    const pv = previews[`i:${item.id}`];
    const card = h('button', { class: ['item-card', on ? 'on' : ''], type: 'button', 'aria-label': item.name },
      h('div', { class: 'pv', html: pv ? pv.svg : '' }),
      h('div', { class: 'nm' }, item.name),
      h('div', { class: 'st' }, on ? h('span', { class: 'chip green' }, ico('check'), 'مرتدى') : item.owned ? h('span', { class: 'chip' }, 'مملوك') : price(item)));
    card.addEventListener('click', () => {
      if (item.owned) equipItem(item);
      else buy(item);
    });
    return card;
  }

  function removeCard() {
    const on = store.boot.avatar[cat] === DEFAULTS[cat];
    const card = h('button', { class: ['item-card', on ? 'on' : ''], type: 'button' },
      h('div', { class: 'pv', style: { display: 'grid', placeItems: 'center', color: 'var(--muted)' } }, ico('x')),
      h('div', { class: 'nm' }, 'بدون'),
      h('div', { class: 'st' }, on ? h('span', { class: 'chip green' }, ico('check'), 'مرتدى') : ''));
    card.addEventListener('click', () => apply({ ...store.boot.avatar, [cat]: DEFAULTS[cat] }, null));
    return card;
  }

  function swatch(key, color, label, on, apply1) {
    const b = h('button', { class: ['sw', on ? 'on' : ''], type: 'button', title: label, 'aria-label': label, style: { background: color } });
    b.addEventListener('click', apply1);
    return b;
  }

  function paintLook() {
    clear(groupRow);
    clear(grid);
    const av = store.boot.avatar;
    const gender = av.gender;
    grid.appendChild(h('h4', null, 'لون البشرة'));
    grid.appendChild(h('div', { class: 'swatches', style: { justifyContent: 'flex-start', marginBottom: '18px' } },
      options.skins.map((s) => swatch(s.id, `#${s.id}`, s.name, av.skin === s.id, () => apply({ ...av, skin: s.id }, guessFor(`skin:${s.id}`))))));
    grid.appendChild(h('h4', null, 'تسريحة الشعر'));
    grid.appendChild(h('div', { class: 'row', style: { marginBottom: '18px' } },
      options.hair_styles.filter((s) => !s.gender || s.gender === gender).map((s) => {
        const b = h('button', { class: ['chip', av.hair === s.id ? 'green' : ''], type: 'button' }, s.name);
        b.addEventListener('click', () => apply({ ...av, hair: s.id }, guessFor(`hair:${s.id}`)));
        return b;
      })));
    grid.appendChild(h('h4', null, 'لون الشعر'));
    grid.appendChild(h('div', { class: 'swatches', style: { justifyContent: 'flex-start' } },
      options.hair_colors.map((c) => swatch(c.id, c.hex, c.name, av.hair_color === c.id, () => apply({ ...av, hair_color: c.id }, guessFor(`hc:${c.id}`))))));
  }

  function paintGrid() {
    clear(catTabs);
    for (const [id, label] of CATS) {
      const b = h('button', { class: cat === id ? 'on' : '', onclick: () => { cat = id; group = ''; paintGrid(); } }, label);
      catTabs.appendChild(b);
    }
    if (cat === 'look') {
      paintLook();
      return;
    }
    const gender = store.boot.avatar.gender;
    const items = catalog.filter((i) => i.category === cat && (!i.gender || i.gender === gender));
    const groups = Array.from(new Set(items.map((i) => i.group)));
    if (!group || !groups.includes(group)) group = groups[0] || '';
    clear(groupRow);
    for (const g of groups) {
      const b = h('button', { class: ['chip', g === group ? 'green' : ''], type: 'button' }, GROUP_LABEL[g] || g);
      b.addEventListener('click', () => { group = g; paintGrid(); });
      groupRow.appendChild(b);
    }
    const shown = items.filter((i) => i.group === group).sort((a, b) => (a.price_coins + a.price_gems * 10) - (b.price_coins + b.price_gems * 10));
    const wrap = h('div', { class: 'items' });
    if (DEFAULTS[cat]) wrap.appendChild(removeCard());
    shown.forEach((i) => wrap.appendChild(itemCard(i)));
    mount(grid, wrap);
  }

  mount(grid, h('div', { class: 'items' }, Array.from({ length: 8 }, () => h('div', { class: 'skeleton', style: { height: '190px' } }))));
  try {
    await loadBoot();
    [catalog, options] = await Promise.all([api.get(`${base}/catalog`), api.get(`${base}/options`, { ttl: 600000 })]);
  } catch (err) {
    mount(page, errorPanel(err, () => ctx.reload()));
    return;
  }
  paintPreview();
  paintGrid();
  loadPreviews();
}
