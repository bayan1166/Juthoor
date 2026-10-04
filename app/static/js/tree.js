import { h, ico, mathBdi, clear } from './dom.js';

// ---------------------------------------------------------------------------------------------
// Juthoor tree: one leaf per lesson, one bough per unit, roots = foundation.
// Drawing rules: shape + colour for every state (never colour alone), two-tone flat leaves,
// no sky/sun/clouds, no colour gradients, calm motion only for "you are here" and the root trace.
// ---------------------------------------------------------------------------------------------

const LEAF_LEN = 104;
const LEAF_W = 52;
const BUD = 0.6;
// Upright trunk with a gentle, natural sway (not a lean); the root flare is drawn symmetrically.
const TRUNK = [[0, 0], [-5, -170], [8, -350], [2, -520]];
const TRUNK_W = [60, 8];
const BOUGHS = {
  1: { c: [[-8, -104], [-88, -100], [-162, -142], [-256, -212]], w: [30, 7] },
  2: { c: [[8, -168], [90, -170], [176, -212], [268, -276]], w: [28, 7] },
  3: { c: [[-2, -284], [-70, -300], [-144, -364], [-232, -466]], w: [24, 6] },
  4: { c: [[6, -364], [80, -386], [156, -454], [242, -560]], w: [22, 6] },
};

export const STATUS_LABEL = { mastered: 'متقن', learning: 'قيد التعلّم', open: 'مفتوح', locked: 'مغلق', soon: 'قريباً' };

let sceneSeq = 0;

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

const f1 = (n) => n.toFixed(1);

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
  return `M${pts.map((q) => `${f1(q[0])} ${f1(q[1])}`).join('L')}Z`;
}

// A band inside a tapered stroke, between two fractions of the local half-width (+ = right-hand normal).
function band(p, w0, w1, fa, fb, t0 = 0, t1 = 1, steps = 22) {
  const a = [], b = [];
  for (let i = 0; i <= steps; i += 1) {
    const t = t0 + ((t1 - t0) * i) / steps;
    const [x, y] = bez(p, t);
    const [tx, ty] = bezTan(p, t);
    const half = (w0 + (w1 - w0) * t) / 2;
    a.push([x + ty * half * fa, y - tx * half * fa]);
    b.push([x + ty * half * fb, y - tx * half * fb]);
  }
  const pts = a.concat(b.reverse());
  return `M${pts.map((q) => `${f1(q[0])} ${f1(q[1])}`).join('L')}Z`;
}

function offsetLine(p, w0, w1, f, t0, t1, steps = 18) {
  const pts = [];
  for (let i = 0; i <= steps; i += 1) {
    const t = t0 + ((t1 - t0) * i) / steps;
    const [x, y] = bez(p, t);
    const [tx, ty] = bezTan(p, t);
    const half = (w0 + (w1 - w0) * t) / 2;
    pts.push(`${f1(x + ty * half * f)} ${f1(y - tx * half * f)}`);
  }
  return `M${pts.join('L')}`;
}

function curveLine(p, t0 = 0, t1 = 1, dx = 0, dy = 0, steps = 18) {
  const pts = [];
  for (let i = 0; i <= steps; i += 1) {
    const [x, y] = bez(p, t0 + ((t1 - t0) * i) / steps);
    pts.push(`${f1(x + dx)} ${f1(y + dy)}`);
  }
  return `M${pts.join('L')}`;
}

// A natural leaf: base at (0,0), tip at (0,-L); slightly fuller toward the base, pointed tip.
function leafPath(L, Wd) {
  const w = Wd / 2;
  return `M0 0C${f1(-w * 1.2)} ${f1(-L * 0.18)} ${f1(-w * 1.02)} ${f1(-L * 0.72)} 0 ${f1(-L)}C${f1(w * 1.02)} ${f1(-L * 0.72)} ${f1(w * 1.2)} ${f1(-L * 0.18)} 0 0Z`;
}

function halfPath(L, Wd, side) {
  const w = (Wd / 2) * side;
  return `M0 0C${f1(w * 1.2)} ${f1(-L * 0.18)} ${f1(w * 1.02)} ${f1(-L * 0.72)} 0 ${f1(-L)}Z`;
}

function ribPath(L, Wd) {
  const w = Wd / 2;
  let d = `M0 ${f1(-L * 0.04)}Q${f1(w * 0.06)} ${f1(-L * 0.5)} 0 ${f1(-L * 0.9)}`;
  for (const f of [0.34, 0.56]) d += `M0 ${f1(-L * f)}q${f1(w * 0.5)} ${f1(-L * 0.08)} ${f1(w * 0.72)} ${f1(-L * 0.17)}M0 ${f1(-L * f)}q${f1(-w * 0.5)} ${f1(-L * 0.08)} ${f1(-w * 0.72)} ${f1(-L * 0.17)}`;
  return d;
}

export function computeScene(w, hgt, data, reserve = 0) {
  const wide = w >= 760 && w >= hgt * 0.95;
  const narrow = w < 820;
  const kx = wide ? 1.95 : 1;
  const ky = wide ? 0.8 : 1;
  const sc = (pts) => pts.map(([x, y]) => [x * kx, y * ky]);
  // The trunk is never stretched sideways (that made it look tilted on wide screens); only boughs widen.
  const trunk = TRUNK.map(([x, y]) => [x, y * ky]);
  const boughs = {};
  for (const k of Object.keys(BOUGHS)) boughs[k] = { c: sc(BOUGHS[k].c), w: BOUGHS[k].w };

  const leaves = [];
  let index = 0;
  for (const unit of data.units) {
    const bough = boughs[unit.no] ? String(unit.no) : '4';
    const b = boughs[bough];
    const n = unit.lessons.length;
    unit.lessons.forEach((lesson, k) => {
      const t = 0.24 + 0.71 * (n > 1 ? k / (n - 1) : 0.5);
      const [x, y] = bez(b.c, t);
      const [tx, ty] = bezTan(b.c, t);
      const upper = k % 2 === 0;
      const cands = [rotate(tx, ty, 50), rotate(tx, ty, -50)];
      const v = upper ? (cands[0][1] < cands[1][1] ? cands[0] : cands[1]) : (cands[0][1] > cands[1][1] ? cands[0] : cands[1]);
      const twig = 20;
      const scale = (upper ? 1 : 0.9) * (lesson.status === 'soon' ? BUD : 1);
      const bx = x + v[0] * twig;
      const by = y + v[1] * twig;
      const deg = (Math.atan2(v[0], -v[1]) * 180) / Math.PI;
      const L = LEAF_LEN * scale;
      leaves.push({ unit, lesson, bough, t, x: bx, y: by, deg, scale, stem: [x, y], tip: [bx + Math.sin((deg * Math.PI) / 180) * L, by - Math.cos((deg * Math.PI) / 180) * L], index });
      index += 1;
    });
  }

  let minX = 0, maxX = 0, minY = 0;
  for (const l of leaves) {
    const pad = l.lesson.current ? 46 : 28;
    for (const [px, py] of [[l.x, l.y], l.tip]) {
      minX = Math.min(minX, px - pad);
      maxX = Math.max(maxX, px + pad);
      minY = Math.min(minY, py - (l.lesson.current ? 40 : 20));
    }
  }
  for (const k of Object.keys(boughs)) for (const [px, py] of boughs[k].c) {
    minX = Math.min(minX, px - 16);
    maxX = Math.max(maxX, px + 16);
    minY = Math.min(minY, py - 16);
  }
  minX = Math.min(minX, -40);
  maxX = Math.max(maxX, 40);

  const groundY = Math.round(hgt * (narrow ? 0.82 : 0.78));
  const topPad = narrow ? 120 : 84;
  const padX = narrow ? 14 : 40;
  const aw = w - reserve;
  const s = Math.max(0.2, Math.min((aw - padX * 2) / (maxX - minX), (groundY - topPad) / -minY));
  const ox = aw / 2 - (s * (minX + maxX)) / 2;
  return { w, h: hgt, wide, narrow, s, ox, oy: groundY, groundY, trunk, boughs, leaves, bounds: { minX, maxX, minY } };
}

export function centerOfLeaf(l) {
  const rad = (l.deg * Math.PI) / 180;
  const len = LEAF_LEN * l.scale;
  return [l.x + Math.sin(rad) * len * 0.5, l.y - Math.cos(rad) * len * 0.5];
}

// Path between two leaves that travels along the tree itself (leaf -> twig -> bough -> trunk ->
// bough -> twig -> leaf), so "tracing the gap" literally follows the structure back to the foundation.
export function skeletonPath(sc, a, b) {
  const pts = [centerOfLeaf(a), [a.x, a.y], a.stem];
  const push = (p, t0, t1) => {
    const steps = Math.max(2, Math.ceil(Math.abs(t1 - t0) * 24));
    for (let i = 1; i <= steps; i += 1) pts.push(bez(p, t0 + ((t1 - t0) * i) / steps));
  };
  const ca = sc.boughs[a.bough].c;
  const cb = sc.boughs[b.bough].c;
  if (a.bough === b.bough) {
    push(ca, a.t, b.t);
  } else {
    push(ca, a.t, 0);
    pts.push(cb[0]);
    push(cb, 0, b.t);
  }
  pts.push([b.x, b.y], centerOfLeaf(b));
  return `M${pts.map(([x, y]) => `${f1(x)} ${f1(y)}`).join('L')}`;
}

const TONE = {
  mastered: ['var(--lf-m1)', 'var(--lf-m2)'],
  gap: ['var(--lf-g1)', 'var(--lf-g2)'],
  open: ['var(--lf-o1)', 'var(--lf-o2)'],
  locked: ['var(--lf-ghost)', 'var(--lf-ghost)'],
  soon: ['var(--lf-ghost)', 'var(--lf-ghost)'],
};

function leafSvg(l, selected, sc, uid) {
  const { lesson, unit } = l;
  const st = lesson.status;
  const kind = lesson.gap ? 'gap' : st;
  const L = LEAF_LEN * l.scale;
  const Wd = LEAF_W * l.scale;
  const [cx, cy] = centerOfLeaf(l);
  const inv = 1 / sc.s;
  const cls = ['leaf', st, lesson.current ? 'cur' : '', lesson.gap ? 'gap' : '', selected === lesson.key ? 'sel' : ''].filter(Boolean).join(' ');
  const label = `${unit.title}، الدرس ${lesson.no}: ${lesson.title} (${lesson.gap ? 'الجذر المرصود' : STATUS_LABEL[st] || st})`;
  const rot = `translate(${f1(l.x)} ${f1(l.y)}) rotate(${f1(l.deg)})`;

  const [sx, sy] = l.stem;
  const mx = (sx + l.x) / 2 + (l.y - sy) * 0.18;
  const my = (sy + l.y) / 2 - (l.x - sx) * 0.18;
  const stem = `<path d="M${f1(sx)} ${f1(sy)}Q${f1(mx)} ${f1(my)} ${f1(l.x)} ${f1(l.y)}" stroke="var(--bark1)" stroke-width="2.4" stroke-linecap="round" fill="none"/>`;

  let fill;
  if (st === 'learning' && !lesson.gap) {
    const p = Math.max(0.12, Math.min(1, lesson.progress || 0));
    const clip = `${uid}-c${l.index}`;
    fill = `<clipPath id="${clip}"><rect x="${f1(-Wd)}" y="${f1(-L * p)}" width="${f1(Wd * 2)}" height="${f1(L * p + 2)}"/></clipPath>`
      + `<path class="half" d="${halfPath(L, Wd, -1)}" fill="${TONE.open[0]}"/><path class="half" d="${halfPath(L, Wd, 1)}" fill="${TONE.open[1]}"/>`
      + `<g clip-path="url(#${clip})"><path class="half fillp" d="${halfPath(L, Wd, -1)}" fill="${TONE.mastered[0]}"/><path class="half fillp" d="${halfPath(L, Wd, 1)}" fill="${TONE.mastered[1]}"/></g>`;
  } else {
    const [a, b] = TONE[kind] || TONE.locked;
    fill = `<path class="half" d="${halfPath(L, Wd, -1)}" fill="${a}"/><path class="half" d="${halfPath(L, Wd, 1)}" fill="${b}"/>`;
  }
  const line = { mastered: 'var(--lf-m1)', gap: 'var(--lf-g1)', learning: 'var(--lf-line)', open: 'var(--lf-line)', locked: 'var(--lf-muted)', soon: 'var(--lf-muted)' }[kind];
  const lineW = kind === 'locked' || kind === 'soon' ? 1.1 : 1.6;
  const lineO = kind === 'soon' ? 0.45 : kind === 'locked' ? 0.7 : 1;
  const outline = `<path class="outline" d="${leafPath(L, Wd)}" fill="none" stroke="${line}" stroke-opacity="${lineO}" stroke-width="${lineW}" stroke-linejoin="round"/>`;
  const ribO = kind === 'mastered' || kind === 'gap' ? 0.35 : kind === 'soon' ? 0 : 0.22;
  const rib = ribO ? `<path d="${ribPath(L, Wd)}" fill="none" stroke="${kind === 'mastered' || kind === 'gap' ? '#fff' : 'var(--lf-muted)'}" stroke-opacity="${ribO}" stroke-width="1" stroke-linecap="round" pointer-events="none"/>` : '';

  let mark = '';
  const k = l.scale;
  if (lesson.gap) {
    mark = `<g transform="translate(${f1(cx)} ${f1(cy)}) scale(${(k * 1.05).toFixed(2)})" fill="none" stroke="#fff" stroke-width="2.4"><circle r="10"/><circle r="3.6" fill="#fff"/></g>`;
  } else if (st === 'mastered') {
    mark = `<path d="M${f1(cx - 9 * k)} ${f1(cy)}l${f1(6 * k)} ${f1(6 * k)}l${f1(12 * k)} ${f1(-13 * k)}" fill="none" stroke="#fff" stroke-width="${f1(3.6 * k)}" stroke-linecap="round" stroke-linejoin="round"/>`;
  } else if (st === 'locked') {
    mark = `<g transform="translate(${f1(cx)} ${f1(cy)}) scale(${(k * 0.95).toFixed(2)})" fill="none" stroke="var(--lf-muted)" stroke-opacity=".85" stroke-width="2" stroke-linecap="round"><rect x="-7" y="-2" width="14" height="10.5" rx="2.6"/><path d="M-4 -2V-5.6a4 4 0 018 0V-2"/></g>`;
  } else if (st !== 'soon') {
    const color = st === 'learning' && (lesson.progress || 0) > 0.5 ? '#fff' : 'var(--num-open)';
    mark = `<text x="${f1(cx)}" y="${f1(cy)}" dy=".36em" text-anchor="middle" font-size="${(24 * k).toFixed(0)}" font-weight="800" style="fill:${color};direction:ltr" pointer-events="none">${lesson.no}</text>`;
  }

  // Rings live in their own <g> so CSS animation (transform) never overrides an SVG transform attribute.
  const halo = (scaleL, scaleW, attrs, cls = '') => `<g transform="${rot}"><g transform="translate(0 ${f1(L * (scaleL - 1) * 0.42)})"><g class="${cls}"><path d="${leafPath(L * scaleL, Wd * scaleW)}" fill="none" ${attrs}/></g></g></g>`;
  const cur = lesson.current
    ? halo(1.28, 1.52, 'stroke="var(--cur-ring)" stroke-opacity=".14" stroke-width="10"') + halo(1.22, 1.44, 'stroke="var(--cur-ring)" stroke-width="2.2"', 'pulse')
    : '';
  const gapRing = lesson.gap ? halo(1.2, 1.4, 'stroke="var(--lf-g1)" stroke-width="2"', 'pulse') : '';
  const sel = `<g class="selring" style="display:${selected === lesson.key ? 'block' : 'none'}">${halo(1.18, 1.36, 'stroke="var(--cur-ring)" stroke-width="2.2" stroke-dasharray="4 5"')}</g>`;

  let pin = '';
  if (lesson.current) {
    const rad = (l.deg * Math.PI) / 180;
    const [tx, ty] = l.tip;
    const px = tx + Math.sin(rad) * 26 * inv;
    const py = ty - Math.cos(rad) * 26 * inv;
    pin = `<g transform="translate(${f1(px)} ${f1(py)}) scale(${inv.toFixed(3)})" pointer-events="none"><g class="here"><rect x="-33" y="-12" width="66" height="24" rx="12" fill="var(--cur-ring)"/><text y="1" dy=".34em" text-anchor="middle" font-size="12.5" font-weight="800" style="fill:var(--cur-ink);direction:rtl">أنت هنا</text></g></g>`;
  }

  return `<g class="${cls}" data-key="${lesson.key}" tabindex="0" role="button" aria-label="${label}" style="--i:${l.index}">`
    + `<title>${label}</title>${stem}${gapRing}${cur}`
    + `<g transform="${rot}"><g class="shape">${fill}${outline}${rib}</g></g>`
    + `${sel}${mark}${pin}<circle cx="${f1(cx)}" cy="${f1(cy)}" r="${(46 * l.scale).toFixed(0)}" fill="transparent"/></g>`;
}

function rootsSvg(sc) {
  const g = sc.groundY;
  const depth = sc.h - g - 10;
  const reach = Math.min(sc.w * 0.34, 440);
  const ox = sc.ox;
  const out = [];
  const roots = [[-1, 0.95, 0.42, 7], [1, 1, 0.48, 7], [-1, 0.62, 0.78, 5.5], [1, 0.58, 0.82, 5.5], [-1, 0.3, 0.95, 4], [1, 0.26, 0.7, 4]];
  roots.forEach(([dir, f, ey, wd]) => {
    const p = [[ox + dir * 6, g + 1], [ox + dir * reach * f * 0.22, g + depth * 0.1], [ox + dir * reach * f * 0.62, g + depth * ey * 0.45], [ox + dir * reach * f, g + depth * ey]];
    out.push(`<path d="${taper(p, wd, 0.6, 0, 16)}" style="fill:var(--root)"/>`);
    const [bx, by] = bez(p, 0.5);
    const sub = [[bx, by], [bx + dir * reach * 0.06, by + depth * 0.08], [bx + dir * reach * 0.12, by + depth * 0.18], [bx + dir * reach * 0.16, by + depth * 0.3]];
    out.push(`<path d="${taper(sub, wd * 0.45, 0.4, 0, 10)}" style="fill:var(--root)" opacity=".7"/>`);
  });
  const tap = [[ox, g], [ox - 6, g + depth * 0.3], [ox + 8, g + depth * 0.6], [ox, g + depth * 0.92]];
  out.push(`<path d="${taper(tap, 9, 0.8, 0, 16)}" style="fill:var(--root)"/>`);
  return `<g class="roots">${out.join('')}</g>`;
}

// Static trace from the current lesson back to the diagnosed root (only when the gap is visible, not locked).
function rootTrace(sc, data) {
  const gap = data && data.root_gap;
  if (!gap || !gap.found || gap.locked) return '';
  const from = sc.leaves.find((l) => l.lesson.current);
  const to = sc.leaves.find((l) => l.lesson.skill === gap.skill);
  if (!from || !to || from === to) return '';
  const d = skeletonPath(sc, from, to);
  return `<path class="root-trace-glow" d="${d}" fill="none" stroke="var(--lf-g1)" stroke-opacity=".18" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>`
    + `<path class="root-trace" d="${d}" fill="none" stroke="var(--lf-g1)" stroke-width="2.4" stroke-dasharray="2 7" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>`;
}

export function sceneSvg(sc, { selected = null, data = null } = {}) {
  sceneSeq += 1;
  const uid = `jt${sceneSeq}`;
  const tr = sc.trunk;
  const [tw0, tw1] = TRUNK_W;
  const trunkD = taper(tr, tw0, tw1, 0, 26);
  // Symmetric root flare: the trunk widens evenly into the ground instead of ending in a slanted wedge.
  const flare = `M-82 2C-48 -1 -34 -20 -28 -80L28 -80C34 -20 48 -1 82 2Z`;
  const flareShade = `M82 2C48 -1 34 -20 28 -80L16 -80C18 -34 26 -8 34 2Z`;
  const shade = band(tr, tw0, tw1, -1, -0.5, 0, 0.96);
  const light = band(tr, tw0, tw1, 0.22, 0.62, 0.02, 0.9);
  const bark = [offsetLine(tr, tw0, tw1, -0.18, 0.05, 0.6), offsetLine(tr, tw0, tw1, 0.05, 0.28, 0.82), offsetLine(tr, tw0, tw1, -0.55, 0.32, 0.7)]
    .map((d) => `<path d="${d}" fill="none" stroke="var(--bark-line)" stroke-opacity=".38" stroke-width="1.1" stroke-linecap="round"/>`).join('');
  const boughD = Object.keys(sc.boughs).map((k) => taper(sc.boughs[k].c, sc.boughs[k].w[0] * 0.78, 1.4, 0, 22)).join('');
  const boughHi = Object.keys(sc.boughs).map((k) => {
    const c = sc.boughs[k].c;
    const up = bezTan(c, 0.5)[0] > 0 ? 0.42 : -0.42;
    return `<path d="${offsetLine(c, sc.boughs[k].w[0] * 0.78, 1.4, up, 0.06, 0.92)}" fill="none" stroke="var(--bark-hi)" stroke-opacity=".6" stroke-width="1.5" stroke-linecap="round"/>`;
  }).join('');
  // A small fork at every bough tip so branches end like branches, not like cut sticks.
  const forks = [...Object.keys(sc.boughs).map((k) => sc.boughs[k].c), tr].map((c) => {
    const [x, y] = bez(c, 0.985);
    const [tx, ty] = bezTan(c, 0.985);
    return [26, -26].map((deg) => {
      const [dx, dy] = rotate(tx, ty, deg);
      const L = deg * (tx > 0 ? -1 : 1) > 0 ? 30 : 22;
      const w = c === tr ? 5 : 2.6;
      return taper([[x, y], [x + dx * L * 0.35, y + dy * L * 0.35], [x + dx * L * 0.7, y + dy * L * 0.7 - 3], [x + dx * L, y + dy * L - 6]], w, 0.5, 0, 8);
    }).join('');
  }).join('');
  const medallions = sc.leaves.length ? Object.keys(sc.boughs).map((k) => {
    const [mx, my] = bez(sc.boughs[k].c, 0.08);
    return `<g transform="translate(${f1(mx)} ${f1(my)})"><circle r="15" fill="var(--medal)" stroke="var(--bark1)" stroke-width="2"/><text y="1" dy=".36em" text-anchor="middle" font-size="15" font-weight="800" fill="var(--medal-ink)" style="direction:ltr">${k}</text></g>`;
  }).join('') : '';
  const leaves = sc.leaves.map((l) => leafSvg(l, selected, sc, uid)).join('');
  const { minX, maxX, minY } = sc.bounds;
  const hx = sc.ox + (sc.s * (minX + maxX)) / 2;
  const hy = sc.oy + sc.s * minY * 0.48;
  const hr = Math.max(120, sc.s * (maxX - minX) * 0.36);
  const g = sc.groundY;
  const ground = `M0 ${g}C${f1(sc.ox * 0.55)} ${g} ${f1(sc.ox - 80)} ${g - 10} ${f1(sc.ox)} ${g - 10}C${f1(sc.ox + 80)} ${g - 10} ${f1(sc.ox + (sc.w - sc.ox) * 0.45)} ${g} ${sc.w} ${g}`;
  return `<svg class="scene" viewBox="0 0 ${sc.w} ${sc.h}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg" role="group" aria-label="خريطة الجذور: ورقة لكل درس، والجذور هي الأساس">`
    + `<defs><filter id="${uid}-soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="${f1(hr * 0.32)}"/></filter></defs>`
    + `<ellipse class="halo" cx="${f1(hx)}" cy="${f1(hy)}" rx="${f1(hr * 1.25)}" ry="${f1(hr * 0.8)}" style="fill:var(--halo)" filter="url(#${uid}-soft)"/>`
    + `<path d="${ground}L${sc.w} ${sc.h}L0 ${sc.h}Z" style="fill:var(--soil)"/>`
    + `<path d="${ground}" fill="none" style="stroke:var(--ground-line)" stroke-width="1.5"/>`
    + `${rootsSvg(sc)}`
    + `<g transform="translate(${f1(sc.ox)} ${sc.oy}) scale(${sc.s.toFixed(4)})">`
    + `<ellipse cx="0" cy="3" rx="170" ry="11" style="fill:var(--tree-shadow)"/>`
    + `<path d="${boughD}" style="fill:var(--bark1)"/><path d="${forks}" style="fill:var(--bark1)"/>${boughHi}`
    + `<path d="${trunkD}" style="fill:var(--bark1)"/><path d="${flare}" style="fill:var(--bark1)"/><path d="${flareShade}" style="fill:var(--bark2)" opacity=".32"/><path d="${shade}" style="fill:var(--bark2)" opacity=".32"/><path d="${light}" style="fill:var(--bark-hi)" opacity=".38"/>${bark}`
    + `${medallions}${rootTrace(sc, data)}${leaves}<g class="scan-layer"></g></g>`
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
    body.appendChild(h('div', { class: 'gap-banner', style: { marginBottom: '14px' } }, ico('target'), h('div', null,
      h('b', null, 'الجذر المرصود للتعثّر الحالي. '),
      `${lesson.attempts ? `الأدلة المسجّلة في هذا الدرس: ${lesson.correct ?? 0} صحيحة من ${lesson.attempts} محاولة. ` : ''}أصلحه ثم ارجع إلى درسك الحالي لتنفتح بقية الدروس.`)));
  } else if (lesson.skill && !lesson.attempts && lesson.status !== 'soon') {
    body.appendChild(h('div', { class: 'banner' }, ico('info'), h('div', null, 'لا أدلة بعد على هذا الدرس، ولا يحكم النظام عليه قبل أن يجيب الطالب.')));
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
          data.course ? h('div', { class: 'course-chip', title: data.course.curriculum_ar || '' }, ico('book'), h('span', { class: 'cc-label' }, 'المحتوى الحالي: '), h('span', null, `${data.course.subject_ar} · ${data.course.grade_ar}`)) : null,
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

const STATE_KEY = [['mastered', 'متقن'], ['learning', 'قيد التعلّم'], ['current', 'أنت هنا'], ['gap', 'الجذر المرصود'], ['locked', 'ينتظر إتقان المتطلبات'], ['soon', 'محتوى قيد الإعداد']];

function legendContent(data) {
  const key = h('div', { class: 'state-key', 'aria-label': 'دليل الألوان' }, STATE_KEY.map(([k, label]) => h('span', { class: 'sk' }, h('i', { class: `sw sw-${k}` }), label)));
  const units = data.units.map((u) => {
    const total = u.lessons.length;
    const done = u.lessons.filter((l) => l.status === 'mastered').length;
    return h('span', { class: 'chip unit-chip' }, h('b', null, String(u.no)), ` ${u.title}`, h('span', { class: 'muted' }, ` ${done}/${total}`));
  });
  return [key, h('div', { class: 'unit-row' }, units)];
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

  function reserveFor() {
    const wide = size.w >= 900 && !opts.compact && !opts.embedded && !opts.bare;
    return wide && current.summary ? 400 : 0;
  }

  function draw() {
    size = measure();
    sceneBox.innerHTML = sceneSvg(computeScene(size.w, size.h, current, reserveFor()), { selected, data: current });
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

  const centerOf = centerOfLeaf;

  function scan(skills, o = {}) {
    clearScan();
    const sc = computeScene(size.w, size.h, current, reserveFor());
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
            layer.appendChild(h('path', { class: 'scan-seg', d: skeletonPath(sc, steps[i - 1], l), pathLength: '1', 'vector-effect': 'non-scaling-stroke' }));
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
