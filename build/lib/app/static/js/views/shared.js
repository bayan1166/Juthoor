import { h, ico, openModal, toast } from '../dom.js';
import { api } from '../api.js';

let skills = null;

export async function skillList() {
  if (!skills) skills = await api.get('/curriculum/skills', { ttl: 3600000 });
  return skills;
}

export async function skillNames() {
  const list = await skillList();
  const out = {};
  for (const s of list) out[s.skill_id] = s.name_ar;
  return out;
}

export function errorPanel(err, retry) {
  return h('div', { class: 'empty' }, ico('alert'), h('h3', null, 'تعذّر تحميل البيانات'), h('p', { class: 'muted' }, err && err.message ? err.message : 'حدث خطأ غير متوقع.'),
    retry ? h('button', { class: 'btn btn-primary', onclick: retry }, ico('refresh'), 'إعادة المحاولة') : null);
}

export function upsellCard({ title, text, cta = 'عرض الباقات', href = '#/plans', secondary = null }) {
  return h('div', { class: 'upsell' },
    h('h3', { style: { color: '#fff' } }, title),
    h('p', null, text),
    h('div', { class: 'row' },
      h('a', { class: 'btn btn-lime', href }, ico('bolt'), cta),
      secondary ? h('a', { class: 'btn btn-ghost', href: secondary.href }, secondary.label) : null));
}

export function openUpsellModal(err) {
  const kind = err.upsell && err.upsell.type;
  const copy = {
    quota: ['وصلت إلى حدّك اليومي', 'الباقة الأساسية تمنحك عدداً محدداً من الأسئلة ورسائل المعلم الذكي كل يوم. افتح الاستخدام غير المحدود مع باقة برو.'],
    plan: ['ميزة متاحة في باقة أعلى', err.message],
    friends: ['أضف المزيد من الأصدقاء', 'الباقة الأساسية تسمح بثلاثة أصدقاء. باقة برو تفتح الأصدقاء بلا حد.'],
  }[kind] || ['ميزة مدفوعة', err.message];
  const target = err.upsell && err.upsell.plan === 'school' ? '#/plans' : '#/plans';
  const modal = openModal({
    title: copy[0],
    content: h('div', { class: 'col' }, h('p', null, copy[1]),
      h('ul', { style: { margin: 0, paddingInlineStart: '20px' } }, h('li', null, 'كشف سلسلة الجذر كاملة'), h('li', null, 'تدريب ومعلم ذكي بلا حد يومي'), h('li', null, 'تقرير فجوة قابل للطباعة'))),
    actions: [
      { label: 'لاحقاً', kind: 'ghost' },
      { label: 'عرض الباقات', kind: 'primary', onClick: () => { location.hash = target; } },
    ],
  });
  return modal;
}

export function handleError(err) {
  if (err && err.upsell) openUpsellModal(err);
  else toast(err && err.message ? err.message : 'حدث خطأ غير متوقع.', 'error');
}

export function lockedChain(count) {
  const nodes = [];
  for (let i = 0; i < Math.min(count, 4); i += 1) {
    nodes.push(h('span', { class: 'node blur-lock' }, 'درس سابق مخفي'));
    nodes.push(h('span', { class: 'arrow' }, ico('chevl')));
  }
  return h('div', { class: 'chain' }, nodes);
}

export async function withBusy(btn, fn) {
  btn.classList.add('is-busy');
  try {
    return await fn();
  } finally {
    btn.classList.remove('is-busy');
  }
}
