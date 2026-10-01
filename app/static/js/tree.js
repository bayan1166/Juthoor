import { h, ico, mathBdi, clear } from './dom.js';

const LEAF_LEN = 104;
const LEAF_W = 50;
const TRUNK = [[0, 0], [-24, -132], [30, -352], [0, -616]];
const BOUGHS = {
  1: { c: [[-8, -104], [-88, -100], [-162, -142], [-256, -212]], w: [30, 7] },
  2: { c: [[8, -168], [90, -170], [176, -212], [268, -276]], w: [28, 7] },
  3: { c: [[-2, -284], [-70, -300], [-144, -364], [-232, -466]], w: [24, 6] },
  4: { c: [[6, -364], [80, -386], [156, -454], [242, -560]], w: [22, 6] },
};

export const STATUS_LABEL = { mastered: 'متقن', learning: 'قيد التعلّم', open: 'مفتوح', locked: 'مغلق', soon: 'قريباً' };

function bez(p, t) {
  const u = 1 - t;
  const a = u * u * u, b = 3 * u * u * t, c = 3 * u * t * t, d = t * t * t;
  return [a * p[0][0] + b * p[1][0] + c * p[2][0] + d * p[3][0], a * p[0][1] + b * p[1][1] + c * p[2][1] + d * p[3][1]];
}

function bezTan(p, t) {
  const u = 1 - t;
  const x = 3 * u * u * (p[1][0] - p[0][0]) + 6 * u * t * (p[2][0] - p[1][0]) + 3 * t * t * (p[3][0] - p[2][0]);
  const y = 3 * u * u * (p[1][1] - p[0][1]) + 6 * u * t * (p[2][1] - p[1][1]) + 3 * t * t * (p[3][1] - p[2][1]);
  const n = Math.hypot(x, y) || 1;
  return [x / n, y / n];
}

function rotate(x, y, deg) {
  const r = (deg * Math.PI) / 180;
  return [x * Math.cos(r) - y * Math.sin(r), x * Math.sin(r) + y * Math.cos(r)];
}

function taper(p, w0, w1, flare, steps = 22) {
  const left = [], right = [];
  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps;
    const [x, y] = bez(p, t);
    const [tx, ty] = bezTan(p, t);
    const half = (w0 + (w1 - w0) * t + flare * Math.pow(1 - t, 6)) / 2;
    left.push([x - ty * half, y + tx * half]);
    right.push([x + ty * half, y - tx * half]);
  }
  const pts = left.concat(right.reverse());
  return `M${pts.map((q) => `${q[0].toFixed(1)} ${q[1].toFixed(1)}`).join('L')}Z`;
}

function leafPath(L, Wd) {
  const w = Wd / 2;
  return `M0 0C${(-w * 1.15).toFixed(1)} ${(-L * 0.22).toFixed(1)} ${(-w * 1.05).toFixed(1)} ${(-L * 0.7).toFixed(1)} 0 ${-L.toFixed(1)}C${(w * 1.05).toFixed(1)} ${(-L * 0.7).toFixed(1)} ${(w * 1.15).toFixed(1)} ${(-L * 0.22).toFixed(1)} 0 0Z`;
}

function veins(L, Wd) {
  const w = Wd / 2;
  let d = `M0 0L0 ${(-L * 0.9).toFixed(1)}`;
  for (const f of [0.28, 0.5, 0.7]) {
    d += `M0 ${(-L * f).toFixed(1)}l${(w * 0.62).toFixed(1)} ${(-L * 0.13).toFixed(1)}M0 ${(-L * f).toFixed(1)}l${(-w * 0.62).toFixed(1)} ${(-L * 0.13).toFixed(1)}`;
  }
  return d;
}

function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function computeScene(w, hgt, data) {
  const wide = w >= 760 && w >= hgt * 0.95;
  const narrow = w < 820;
  const kx = wide ? 2.3 : 1;
  const ky = wide ? 0.72 : 1;
  const sc = (pts) => pts.map(([x, y]) => [x * kx, y * ky]);
  const trunk = sc(TRUNK);
  const boughs = {};
  for (const k of Object.keys(BOUGHS)) boughs[k] = { c: sc(BOUGHS[k].c), w: BOUGHS[k].w };

  const leaves = [];
  let index = 0;
  for (const unit of data.units) {
    const b = boughs[unit.no] || boughs[4];
    const n = unit.lessons.length;
    unit.lessons.forEach((lesson, k) => {
      const t = 0.24 + 0.71 * (n > 1 ? k / (n - 1) : 0.5);
      const [x, y] = bez(b.c, t);
      const [tx, ty] = bezTan(b.c, t);
      const upper = k % 2 === 0;
      const cands = [rotate(tx, ty, 50), rotate(tx, ty, -50)];
      const v = upper ? (cands[0][1] < cands[1][1] ? cands[0] : cands[1]) : (cands[0][1] > cands[1][1] ? cands[0] : cands[1]);
      const twig = 20;
      const scale = upper ? 1 : 0.9;
      const bx = x + v[0] * twig;
      const by = y + v[1] * twig;
      const deg = (Math.atan2(v[0], -v[1]) * 180) / Math.PI;
      const L = LEAF_LEN * scale;
      leaves.push({ unit, lesson, x: bx, y: by, deg, scale, stem: [x, y], tip: [bx + Math.sin((deg * Math.PI) / 180) * L, by - Math.cos((deg * Math.PI) / 180) * L], index });
      index += 1;
    });
  }

  let minX = 0, maxX = 0, minY = 0;
  for (const l of leaves) {
    for (const [px, py] of [[l.x, l.y], l.tip]) {
      minX = Math.min(minX, px - 28);
      maxX = Math.max(maxX, px + 28);
      minY = Math.min(minY, py - 20);
    }
  }
  for (const k of Object.keys(boughs)) for (const [px, py] of boughs[k].c) {
    minX = Math.min(minX, px - 16);
    maxX = Math.max(maxX, px + 16);
    minY = Math.min(minY, py - 16);
  }
  minX = Math.min(minX, -40);
  maxX = Math.max(maxX, 40);

  const groundY = Math.round(hgt * (narrow ? 0.84 : 0.8));
  const topPad = narrow ? 120 : 84;
  const padX = narrow ? 14 : 40;
  const s = Math.max(0.2, Math.min((w - padX * 2) / (maxX - minX), (groundY - topPad) / -minY));
  const ox = w / 2 - (s * (minX + maxX)) / 2;
  return { w, h: hgt, wide, narrow, s, ox, oy: groundY, groundY, trunk, boughs, leaves, bounds: { minX, maxX, minY } };
}

function leafLook(l) {
  const st = l.lesson.status;
  const p = l.lesson.progress || 0;
  if (st === 'mastered') return { fill: '#13895F', fo: 1, stroke: '#0B5E40', so: 1, dash: '' };
  if (st === 'learning') return { fill: '#16A36B', fo: 0.3 + 0.62 * p, stroke: '#13895F', so: 0.95, dash: '' };
  if (st === 'open') return { fill: 'var(--leaf-glass)', fo: 0.95, stroke: '#16A36B', so: 1, dash: '' };
  if (st === 'locked') return { fill: 'var(--leaf-glass)', fo: 0.4, stroke: '#5E7667', so: 0.7, dash: ' stroke-dasharray="5 5"' };
  return { fill: 'var(--leaf-glass)', fo: 0.25, stroke: '#5E7667', so: 0.45, dash: ' stroke-dasharray="5 5"' };
}

function leafSvg(l, selected) {
  const { lesson, unit } = l;
  const look = leafLook(l);
  const L = LEAF_LEN * l.scale;
  const Wd = LEAF_W * l.scale;
  const rad = (l.deg * Math.PI) / 180;
  const cx = l.x + Math.sin(rad) * L * 0.5;
  const cy = l.y - Math.cos(rad) * L * 0.5;
  const st = lesson.status;
  const cls = ['leaf', st, lesson.current ? 'cur' : '', lesson.gap ? 'gap' : '', selected === lesson.key ? 'sel' : ''].filter(Boolean).join(' ');
  const label = `${unit.title}، الدرس ${lesson.no}: ${lesson.title} (${STATUS_LABEL[st] || st})`;
  let mark = '';
  if (st === 'locked') {
    mark = `<g transform="translate(${cx.toFixed(1)} ${cy.toFixed(1)}) scale(${(l.scale * 1.15).toFixed(2)})" fill="none" stroke="var(--num-dim,#5E7667)" stroke-width="2.2" stroke-linecap="round"><rect x="-8" y="-3" width="16" height="12" rx="3"/><path d="M-4.5 -3V-7a4.5 4.5 0 019 0v4"/></g>`;
  } else if (st === 'mastered') {
    mark = `<path d="M${(cx - 9 * l.scale).toFixed(1)} ${cy.toFixed(1)}l${(6 * l.scale).toFixed(1)} ${(6 * l.scale).toFixed(1)}l${(12 * l.scale).toFixed(1)} ${(-13 * l.scale).toFixed(1)}" fill="none" stroke="#fff" stroke-width="${(4 * l.scale).toFixed(1)}" stroke-linecap="round" stroke-linejoin="round"/>`;
  } else {
    const color = st === 'learning' && lesson.progress > 0.55 ? '#fff' : st === 'soon' ? 'var(--num-dim,#5E7667)' : 'var(--num-open,#12684A)';
    mark = `<text x="${cx.toFixed(1)}" y="${cy.toFixed(1)}" dy=".36em" text-anchor="middle" font-size="${(26 * l.scale).toFixed(0)}" font-weight="800" style="fill:${color};direction:ltr" pointer-events="none">${lesson.no}</text>`;
  }
  const ring = lesson.current
    ? `<g transform="translate(${l.x.toFixed(1)} ${l.y.toFixed(1)}) rotate(${l.deg.toFixed(1)})"><path class="pulse" d="${leafPath(L * 1.2, Wd * 1.38)}" transform="translate(0 ${(L * 0.08).toFixed(1)})" fill="none" stroke="#C6F36B" stroke-width="3"/></g>`
    : '';
  const gap = lesson.gap
    ? `<g transform="translate(${l.x.toFixed(1)} ${l.y.toFixed(1)}) rotate(${l.deg.toFixed(1)})"><path class="pulse" d="${leafPath(L * 1.14, Wd * 1.3)}" transform="translate(0 ${(L * 0.06).toFixed(1)})" fill="none" stroke="#C2503A" stroke-width="3" stroke-dasharray="6 4"/></g>`
    : '';
  const sel = `<g transform="translate(${l.x.toFixed(1)} ${l.y.toFixed(1)}) rotate(${l.deg.toFixed(1)})" class="selring" style="display:${selected === lesson.key ? 'block' : 'none'}"><path d="${leafPath(L * 1.16, Wd * 1.3)}" transform="translate(0 ${(L * 0.07).toFixed(1)})" fill="none" stroke="#C6F36B" stroke-width="2.4" stroke-dasharray="4 5"/></g>`;
  return `<g class="${cls}" data-key="${lesson.key}" tabindex="0" role="button" aria-label="${label}" style="--i:${l.index}">`
    + `<title>${label}</title>`
    + `<path d="M${l.stem[0].toFixed(1)} ${l.stem[1].toFixed(1)}L${l.x.toFixed(1)} ${l.y.toFixed(1)}" stroke="var(--bark1)" stroke-width="3.2" stroke-linecap="round" fill="none"/>`
    + `${gap}${ring}`
    + `<g transform="translate(${l.x.toFixed(1)} ${l.y.toFixed(1)}) rotate(${l.deg.toFixed(1)})"><path class="shape" d="${leafPath(L, Wd)}" fill="${look.fill}" fill-opacity="${look.fo.toFixed(2)}" stroke="${look.stroke}" stroke-opacity="${look.so}" stroke-width="1.8"${look.dash}/>`
    + `<path d="${veins(L, Wd)}" fill="none" stroke="#fff" stroke-opacity="${st === 'mastered' ? 0.25 : 0.4}" stroke-width="1.2" stroke-linecap="round" pointer-events="none"/></g>`
    + `${sel}${mark}<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${(46 * l.scale).toFixed(0)}" fill="transparent"/></g>`;
}

function hillPath(w, baseY, amp, seed) {
  const r = rng(seed);
  const pts = [];
  const n = 7;
  for (let i = 0; i <= n; i += 1) pts.push([(w / n) * i, baseY - r() * amp]);
  let d = `M0 ${baseY + 200}L${pts[0][0]} ${pts[0][1].toFixed(1)}`;
  for (let i = 1; i < pts.length; i += 1) {
    const [px, py] = pts[i - 1];
    const [qx, qy] = pts[i];
    d += `C${(px + (qx - px) / 2).toFixed(1)} ${py.toFixed(1)} ${(px + (qx - px) / 2).toFixed(1)} ${qy.toFixed(1)} ${qx.toFixed(1)} ${qy.toFixed(1)}`;
  }
  return `${d}L${w} ${baseY + 200}Z`;
}

function rootsSvg(sc) {
  const depth = sc.h - sc.groundY - 14;
  const out = [];
  const spans = [[-1, 0.5, 9], [1, 0.55, 9], [-1, 0.28, 6], [1, 0.3, 6], [-1, 0.78, 5], [1, 0.8, 5]];
  const reach = Math.min(sc.w * 0.34, 420);
  spans.forEach(([dir, f, wd], i) => {
    const x1 = sc.ox + dir * reach * f * 0.5;
    const x2 = sc.ox + dir * reach * f;
    const y1 = sc.groundY + depth * (0.25 + i * 0.03);
    const y2 = sc.groundY + depth * (0.55 + (i % 3) * 0.16);
    out.push(`<path d="M${sc.ox.toFixed(1)} ${sc.groundY}C${x1.toFixed(1)} ${(sc.groundY + 6).toFixed(1)} ${x1.toFixed(1)} ${y1.toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}" fill="none" stroke="var(--root)" stroke-width="${wd}" stroke-linecap="round" opacity=".9"/>`);
    out.push(`<path d="M${((x1 + x2) / 2).toFixed(1)} ${((y1 + y2) / 2).toFixed(1)}q${(dir * 18).toFixed(1)} ${(depth * 0.12).toFixed(1)} ${(dir * 34).toFixed(1)} ${(depth * 0.2).toFixed(1)}" fill="none" stroke="var(--root)" stroke-width="2.4" stroke-linecap="round" opacity=".7"/>`);
  });
  out.push(`<path d="M${sc.ox.toFixed(1)} ${sc.groundY}L${sc.ox.toFixed(1)} ${(sc.groundY + depth * 0.9).toFixed(1)}" stroke="var(--root)" stroke-width="10" stroke-linecap="round" opacity=".85"/>`);
  return out.join('');
}

export function sceneSvg(sc, { selected = null } = {}) {
  const r = rng(26);
  const stars = Array.from({ length: 46 }, () => `<circle class="star" cx="${(r() * sc.w).toFixed(0)}" cy="${(r() * sc.groundY * 0.55).toFixed(0)}" r="${(0.7 + r() * 1.5).toFixed(1)}" fill="#fff" style="animation-delay:${(r() * 4).toFixed(1)}s"/>`).join('');
  const pollen = Array.from({ length: 14 }, () => `<circle class="pollen" cx="${(r() * sc.w).toFixed(0)}" cy="${(sc.groundY * (0.3 + r() * 0.65)).toFixed(0)}" r="${(1.6 + r() * 2).toFixed(1)}" fill="#fff" style="animation-delay:${(r() * 9).toFixed(1)}s"/>`).join('');
  const sunR = Math.max(34, Math.min(sc.w, sc.h) * 0.075);
  const sunX = sc.narrow ? sc.w * 0.8 : sc.w * 0.84;
  const sunY = sc.narrow ? 150 : sc.groundY * 0.26;
  const cloud = (cx, cy, k, cls) => `<g class="cloud ${cls}"><g transform="translate(${cx} ${cy}) scale(${k})" fill="var(--cloud)" opacity=".85"><ellipse cx="0" cy="0" rx="62" ry="20"/><ellipse cx="-26" cy="-14" rx="34" ry="22"/><ellipse cx="14" cy="-20" rx="40" ry="26"/></g></g>`;
  const tr = sc.trunk;
  const trunkD = taper(tr, 64, 20, 46);
  const boughD = Object.keys(sc.boughs).map((k) => taper(sc.boughs[k].c, sc.boughs[k].w[0], sc.boughs[k].w[1], 0, 16)).join('');
  const medallions = sc.leaves.length ? Object.keys(sc.boughs).map((k) => {
    const c = sc.boughs[k].c;
    const [mx, my] = bez(c, 0.08);
    return `<g transform="translate(${mx.toFixed(1)} ${my.toFixed(1)})"><circle r="17" fill="var(--bark2)" stroke="var(--bark1)" stroke-width="2"/><text y="1" dy=".36em" text-anchor="middle" font-size="18" font-weight="800" fill="#FFF6E2" style="direction:ltr">${k}</text></g>`;
  }).join('') : '';
  const leaves = sc.leaves.map((l) => leafSvg(l, selected)).join('');
  return `<svg class="scene" viewBox="0 0 ${sc.w} ${sc.h}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg" role="group" aria-label="شجرة المنهج: ورقة لكل درس">`
    + `<defs><radialGradient id="sunG"><stop offset="0" style="stop-color:var(--sun)" stop-opacity="1"/><stop offset=".45" style="stop-color:var(--sun)" stop-opacity=".45"/><stop offset="1" style="stop-color:var(--sun)" stop-opacity="0"/></radialGradient>`
    + `<linearGradient id="soilG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--soil1)"/><stop offset="1" style="stop-color:var(--soil2)"/></linearGradient>`
    + `<linearGradient id="barkG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" style="stop-color:var(--bark2)"/><stop offset=".5" style="stop-color:var(--bark1)"/><stop offset="1" style="stop-color:var(--bark2)"/></linearGradient></defs>`
    + `${stars}`
    + `<circle class="sun-glow" cx="${sunX.toFixed(0)}" cy="${sunY.toFixed(0)}" r="${(sunR * 3.2).toFixed(0)}" fill="url(#sunG)"/><circle cx="${sunX.toFixed(0)}" cy="${sunY.toFixed(0)}" r="${sunR.toFixed(0)}" style="fill:var(--sun)"/>`
    + `${cloud(sc.w * 0.12, 120, 1.1, 'c1')}${cloud(sc.w * 0.5, 90, 0.8, 'c2')}${cloud(sc.w * 0.3, 190, 0.9, 'c3')}`
    + `<path d="${hillPath(sc.w, sc.groundY - sc.h * 0.04, sc.h * 0.14, 3)}" style="fill:var(--hill1)"/><path d="${hillPath(sc.w, sc.groundY, sc.h * 0.07, 11)}" style="fill:var(--hill2)"/>`
    + `${pollen}`
    + `<rect x="0" y="${sc.groundY}" width="${sc.w}" height="${(sc.h - sc.groundY + 2).toFixed(0)}" fill="url(#soilG)"/>`
    + `<rect x="0" y="${sc.groundY - 5}" width="${sc.w}" height="12" rx="6" style="fill:var(--grass)"/>`
    + `${rootsSvg(sc)}`
    + `<g transform="translate(${sc.ox.toFixed(1)} ${sc.oy}) scale(${sc.s.toFixed(4)})"><path d="${trunkD}" fill="url(#barkG)"/><path d="${boughD}" fill="url(#barkG)"/>${medallions}${leaves}<g class="scan-layer"></g></g>`
    + `</svg>`;
}

export function demoTreeData(map) {
  const cycle = ['mastered', 'mastered', 'learning', 'learning', 'open', 'locked', 'locked', 'soon'];
  let i = 0;
  return {
    units: map.units.map((u) => ({
      no: u.no,
      title: u.title,
      lessons: u.lessons.map((l) => {
        const status = l.skill ? cycle[i % cycle.length] : 'soon';
        if (l.skill) i += 1;
        return { ...l, status, progress: status === 'mastered' ? 1 : status === 'learning' ? 0.6 : 0, current: false, gap: false, concepts: [], missing: [] };
      }),
    })),
  };
}

function unitOf(data, key) {
  for (const unit of data.units) for (const lesson of unit.lessons) if (lesson.key === key) return { unit, lesson };
  return null;
}

function panelContent(found, opts, close) {
  const { unit, lesson } = found;
  const body = h('div', { class: 'body' });
  const head = h('div', { class: 'head' },
    h('div', { class: 'grow' },
      h('span', { class: ['chip', lesson.status === 'mastered' ? 'green' : lesson.status === 'learning' ? 'lime' : lesson.status === 'open' ? 'green' : ''] }, STATUS_LABEL[lesson.status] || lesson.status),
      h('h3', { style: { margin: '8px 0 2px' } }, lesson.title),
      h('div', { class: 'muted small' }, `الوحدة ${unit.no}: ${unit.title}`)),
    h('button', { class: 'icon-btn', 'aria-label': 'إغلاق', onclick: close }, ico('x')));

  if (lesson.skill) {
    const fill = h('i');
    const pctVal = Math.round((lesson.progress || 0) * 100);
    body.appendChild(h('div', { class: 'row between small', style: { marginBottom: '6px' } }, h('b', null, 'التقدّم في الدرس'), h('b', null, `${pctVal}%`)));
    body.appendChild(h('div', { class: 'bar' }, fill));
    setTimeout(() => { fill.style.width = `${pctVal}%`; }, 40);
    body.appendChild(h('div', { class: 'row', style: { margin: '14px 0' } },
      h('span', { class: 'chip' }, `المحاولات: ${lesson.attempts ?? 0}`),
      h('span', { class: 'chip' }, `الصحيحة: ${lesson.correct ?? 0}`),
      lesson.accuracy !== null && lesson.accuracy !== undefined ? h('span', { class: 'chip green' }, `الدقة: ${Math.round(lesson.accuracy * 100)}%`) : null));
  }
  if (lesson.gap) {
    body.appendChild(h('div', { class: 'gap-banner', style: { marginBottom: '14px' } }, ico('alert'), h('div', null, 'هذا الدرس هو الجذر المرصود للتعثّر الحالي. أتقنه لتنفتح بقية الدروس.')));
  }
  if (lesson.missing && lesson.missing.length) {
    body.appendChild(h('div', { class: 'banner' }, ico('lock'), h('div', null, h('b', null, 'أتقن هذه الدروس أولاً: '), lesson.missing.join('، '))));
  }
  if (lesson.status === 'soon') {
    body.appendChild(h('p', { class: 'muted' }, 'أسئلة هذا الدرس قيد الإعداد وستُضاف قريباً.'));
  }
  if (lesson.concepts && lesson.concepts.length) {
    body.appendChild(h('h4', { style: { margin: '6px 0 10px' } }, 'أهم الأفكار'));
    lesson.concepts.forEach((c, i) => {
      const box = h('div', { class: ['concept', i === 0 ? 'open' : ''] });
      const txt = h('div', { class: 'txt' }, mathBdi(c.segments));
      box.appendChild(h('button', { onclick: () => box.classList.toggle('open'), 'aria-expanded': i === 0 ? 'true' : 'false' }, h('span', { class: 'no' }, String(i + 1)), h('span', null, c.title), h('span', { class: 'chev' }, ico('chevl'))));
      box.appendChild(txt);
      body.appendChild(box);
    });
  }
  const foot = h('div', { class: 'foot' });
  if (opts.canPractice !== false) {
    if (lesson.skill && ['open', 'learning', 'mastered'].includes(lesson.status)) {
      foot.appendChild(h('a', { class: 'btn btn-primary grow', href: '#/practice' }, ico('pencil'), lesson.status === 'mastered' ? 'راجع بالتدريب' : 'ابدأ التدريب'));
    } else {
      foot.appendChild(h('button', { class: 'btn grow', disabled: true }, lesson.status === 'soon' ? 'قريباً' : 'أتقن المتطلبات أولاً'));
    }
  }
  foot.appendChild(h('button', { class: 'btn btn-ghost', onclick: close }, 'إغلاق'));
  return [head, body, foot];
}

function hudContent(data, opts) {
  const nodes = [];
  if (data.summary) {
    const health = Math.round((data.tree_health || 0) * 100);
    const ring = h('div', { class: 'ring', style: { '--p': String(health) } }, h('b', null, `${health}%`));
    nodes.push(h('div', { class: 'hud-card' },
      h('div', { class: 'row nowrap' }, ring,
        h('div', { class: 'grow' },
          h('div', { style: { fontWeight: 800 } }, opts.title || 'صحة الشجرة'),
          h('div', { class: 'muted small' }, `${data.summary.mastered} من ${data.summary.live} دروس مُتقنة`),
          h('div', { class: 'muted small' }, `${data.summary.correct} إجابة صحيحة من ${data.summary.answered}`))),
      opts.canPractice !== false ? h('a', { class: 'btn btn-primary btn-sm btn-block', style: { marginTop: '12px' }, href: '#/practice' }, ico('pencil'), 'تابع التدريب') : null));
  }
  const gap = data.root_gap;
  if (gap && gap.found) {
    if (gap.locked) {
      nodes.push(h('div', { class: 'hud-card' }, h('div', { class: 'gap-banner locked' }, ico('lock'), h('div', null, `رصدنا فجوة جذرية على بعد ${gap.steps_back} خطوات إلى الخلف.`)),
        h('a', { class: 'btn btn-lime btn-sm btn-block', style: { marginTop: '10px' }, href: '#/plans' }, 'اكشف الجذر بباقة برو')));
    } else {
      nodes.push(h('div', { class: 'hud-card' }, h('div', { class: 'gap-banner' }, ico('target'), h('div', null, `الجذر المرصود: ${gap.name_ar}، على بعد ${gap.steps_back} خطوات.`)),
        opts.studentId ? h('a', { class: 'btn btn-ghost btn-sm btn-block', style: { marginTop: '10px' }, href: `#/report/${opts.studentId}` }, ico('file'), 'افتح تقرير الفجوة') : null));
    }
  }
  return nodes;
}

function legendContent(data) {
  return data.units.map((u) => {
    const total = u.lessons.length;
    const done = u.lessons.filter((l) => l.status === 'mastered').length;
    return h('span', { class: 'chip' }, h('b', null, String(u.no)), ` ${u.title}`, h('span', { class: 'muted' }, ` ${done}/${total}`));
  });
}

export function renderTreeStage(host, data, opts = {}) {
  const stage = h('section', { class: ['stage', opts.embedded ? 'embedded' : '', opts.fill ? 'fill' : '', opts.compact ? 'compact' : ''] });
  const sceneBox = h('div', { style: { position: 'absolute', inset: '0' } });
  const hud = h('div', { class: 'hud' });
  const legend = h('div', { class: 'legend' });
  const panel = h('aside', { class: 'leaf-panel', hidden: true, 'aria-live': 'polite' });
  stage.appendChild(sceneBox);
  if (!opts.bare) {
    stage.appendChild(hud);
    stage.appendChild(legend);
    stage.appendChild(panel);
  }
  host.appendChild(stage);

  let current = data;
  let selected = null;
  let size = { w: 0, h: 0 };

  function measure() {
    const w = Math.round(stage.clientWidth || (typeof window !== 'undefined' ? window.innerWidth : 1200));
    const hh = Math.round(stage.clientHeight || (typeof window !== 'undefined' ? window.innerHeight - 64 : 700));
    return { w: Math.max(320, w), h: Math.max(380, hh) };
  }

  function draw() {
    size = measure();
    sceneBox.innerHTML = sceneSvg(computeScene(size.w, size.h, current), { selected });
  }

  function closePanel() {
    selected = null;
    panel.hidden = true;
    panel.removeAttribute('hidden');
    panel.setAttribute('hidden', '');
    for (const g of sceneBox.querySelectorAll('.leaf')) {
      g.classList.remove('sel');
      const ring = g.querySelector('.selring');
      if (ring) ring.style.display = 'none';
    }
  }

  function select(key) {
    const found = unitOf(current, key);
    if (!found || opts.interactive === false) return;
    selected = key;
    clear(panel);
    for (const node of panelContent(found, opts, closePanel)) panel.appendChild(node);
    panel.removeAttribute('hidden');
    panel.hidden = false;
    for (const g of sceneBox.querySelectorAll('.leaf')) {
      const on = g.dataset.key === key;
      g.classList.toggle('sel', on);
      const ring = g.querySelector('.selring');
      if (ring) ring.style.display = on ? 'block' : 'none';
    }
    if (opts.onSelect) opts.onSelect(found);
  }

  function paintOverlays() {
    clear(hud);
    for (const node of hudContent(current, opts)) hud.appendChild(node);
    clear(legend);
    for (const node of legendContent(current)) legend.appendChild(node);
  }

  const scanTimers = [];
  const SCAN_CLASSES = ['scan', 'scan-root', 'scan-locked'];

  function cancelScanTimers() {
    while (scanTimers.length) clearTimeout(scanTimers.pop());
  }

  function clearScan() {
    cancelScanTimers();
    for (const g of sceneBox.querySelectorAll('.leaf')) for (const c of SCAN_CLASSES) g.classList.remove(c);
    const layer = sceneBox.querySelector('.scan-layer');
    if (layer) clear(layer);
  }

  function centerOf(l) {
    const rad = (l.deg * Math.PI) / 180;
    const len = LEAF_LEN * l.scale;
    return [l.x + Math.sin(rad) * len * 0.5, l.y - Math.cos(rad) * len * 0.5];
  }

  function scan(skills, o = {}) {
    clearScan();
    const sc = computeScene(size.w, size.h, current);
    const bySkill = new Map(sc.leaves.map((l) => [l.lesson.skill, l]));
    const steps = skills.map((s) => bySkill.get(s)).filter(Boolean);
    const reduced = typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const stepMs = reduced ? 0 : (o.stepMs || 720);
    const layer = sceneBox.querySelector('.scan-layer');
    return new Promise((resolve) => {
      if (!steps.length) {
        resolve(0);
        return;
      }
      const leaves = Array.from(sceneBox.querySelectorAll('.leaf'));
      let i = 0;
      const step = () => {
        const l = steps[i];
        const last = i === steps.length - 1;
        const g = leaves.find((n) => n.dataset.key === l.lesson.key);
        if (g) {
          g.classList.add('scan');
          if (last) g.classList.add(o.lockedTail ? 'scan-locked' : 'scan-root');
        }
        if (layer) {
          const [cx, cy] = centerOf(l);
          if (i > 0) {
            const [px, py] = centerOf(steps[i - 1]);
            layer.appendChild(h('path', { class: 'scan-seg', d: `M${px.toFixed(1)} ${py.toFixed(1)}L${cx.toFixed(1)} ${cy.toFixed(1)}`, pathLength: '1' }));
          }
          layer.appendChild(h('circle', { class: ['scan-dot', last ? 'end' : ''], cx: cx.toFixed(1), cy: cy.toFixed(1), r: last ? '15' : '9' }));
        }
        if (o.onStep) o.onStep(i, l.lesson, last);
        i += 1;
        if (i < steps.length) scanTimers.push(setTimeout(step, stepMs));
        else scanTimers.push(setTimeout(() => resolve(steps.length), reduced ? 0 : 450));
      };
      step();
    });
  }

  stage.addEventListener('click', (e) => {
    const leaf = e.target.closest ? e.target.closest('.leaf') : null;
    if (leaf) {
      select(leaf.dataset.key);
      return;
    }
    if (!e.target.closest || !e.target.closest('.leaf-panel, .hud')) closePanel();
  });
  stage.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closePanel();
      return;
    }
    const leaf = e.target.closest ? e.target.closest('.leaf') : null;
    if (leaf && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      select(leaf.dataset.key);
    }
  });

  let observer = null;
  let timer = null;
  if (typeof ResizeObserver === 'function') {
    observer = new ResizeObserver(() => {
      const next = measure();
      if (Math.abs(next.w - size.w) < 2 && Math.abs(next.h - size.h) < 2) return;
      clearTimeout(timer);
      timer = setTimeout(draw, 120);
    });
    observer.observe(stage);
  }

  paintOverlays();
  draw();
  panel.hidden = true;
  panel.setAttribute('hidden', '');

  return {
    stage,
    select,
    scan,
    clearScan,
    close: closePanel,
    update(next) {
      current = next;
      paintOverlays();
      draw();
      if (selected) {
        const found = unitOf(current, selected);
        if (found) select(selected);
        else closePanel();
      }
    },
    destroy() {
      if (observer) observer.disconnect();
      clearTimeout(timer);
      cancelScanTimers();
      stage.remove();
    },
  };
}
