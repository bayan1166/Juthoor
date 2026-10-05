import { h, ico, mount } from '../dom.js';
import { api } from '../api.js';

// The learner-facing diagnosis card. Everything shown here comes from the backend: the diagnosis the engine
// recorded (origin, root, confidence, evidence, competing candidates) and the live state recomputed on every
// request (current BKT mastery of the root, status of the original lesson, answers since the diagnosis).
// The UI never names a root itself and never shows a diagnosis the backend did not return.

export const LEVEL_EN = { high: 'High', medium: 'Medium', low: 'Low' };
const STATUS_AR = { mastered: 'متقن', gap: 'فجوة قيد العلاج', learning: 'قيد التعلّم', untouched: 'لم يبدأ بعد' };

// Workflow stages in which a named root is active, so the "root found" entry point is offered.
export const ROOT_STAGES = ['root_identified', 'remediation', 'retry'];

export function hasActiveRoot(w) {
  return !!(w && !w.locked && w.root && ROOT_STAGES.includes(w.stage));
}

const q = (s) => `«${s}»`;

function pct(p) {
  return typeof p === 'number' && Number.isFinite(p) ? Math.round(p * 100) : null;
}

/** "What we do now", from the live outcome returned by the backend. */
export function nextStep(record) {
  const o = record.outcome || {};
  const sameLesson = record.origin_skill === record.root_skill;
  if (o.root_status === 'mastered') {
    if (!sameLesson && o.origin_status !== 'mastered') return `أصبح ${q(record.root_name_ar)} متيناً. الآن نعود إلى الدرس الأصلي ${q(record.origin_name_ar)}.`;
    return 'أُغلقت الفجوة. نتابع التقدّم في شجرتك.';
  }
  return sameLesson
    ? `نتدرّب على ${q(record.root_name_ar)} من الأسهل إلى الأصعب حتى يثبت.`
    : `نتدرّب على ${q(record.root_name_ar)} من الأسهل إلى الأصعب، ثم نعود إلى ${q(record.origin_name_ar)}.`;
}

function row(label, value) {
  return h('div', { class: 'dx-row' }, h('span', { class: 'dx-label' }, label), h('div', { class: 'dx-value' }, value));
}

/** Pure render of one diagnosis record (the shape of GET /students/{id}/adaptive/diagnoses). */
export function diagnosisPanel(record) {
  const o = record.outcome || {};
  const mastery = pct(o.root_mastery);
  const evidence = (record.evidence || []).filter((e) => (e.wrong || 0) + (e.right || 0) > 0);
  const level = record.confidence_level;
  const fill = h('i');
  if (mastery !== null) fill.style.width = `${mastery}%`;
  const competing = record.competing || [];
  return h('div', { class: 'dx-panel', 'data-testid': 'root-diagnosis' },
    h('div', { class: 'dx-head' }, h('b', null, 'بطاقة التشخيص'), h('span', { class: 'small muted' }, 'تقدير النظام من إجاباتك، ويتحدّث مع كل إجابة')),
    row('المشكلة الحالية', h('span', { class: 'dx-big', 'data-testid': 'dx-origin' }, record.origin_name_ar)),
    row('جذر المشكلة', h('span', { class: 'dx-big dx-root', 'data-testid': 'dx-root' }, record.root_name_ar)),
    row('لماذا؟', h('div', { class: 'col', style: { gap: '6px' } },
      record.explanation ? h('span', null, record.explanation) : null,
      evidence.length ? h('ul', { class: 'dx-evidence', 'data-testid': 'dx-evidence' }, evidence.map((e) => h('li', null, `${e.name_ar || e.skill}: ${e.wrong} خاطئة و${e.right} صحيحة`))) : null)),
    row('مستوى الثقة', h('span', { class: ['dx-level', level ? `lv-${level}` : ''], 'data-testid': 'dx-confidence' },
      record.confidence || '', level && LEVEL_EN[level] ? ` (${LEVEL_EN[level]})` : '')),
    row(`إتقان ${q(record.root_name_ar)} الآن`, mastery === null
      ? h('span', { class: 'muted' }, 'تعذّر تحميل نسبة الإتقان الآن.')
      : h('div', { class: 'col', style: { gap: '6px' } },
        h('span', { class: 'dx-big', 'data-testid': 'dx-mastery' }, `${mastery}%`, o.root_status ? h('span', { class: 'small muted' }, ` · ${STATUS_AR[o.root_status] || o.root_status}`) : null),
        h('div', { class: 'bar' }, fill),
        h('span', { class: 'small muted' }, 'تقدير الإتقان الذي يستخدمه النظام نفسه (p_mastery)، ويُعاد حسابه بعد كل إجابة.'))),
    row('ماذا سنفعل الآن؟', h('div', { class: 'col', style: { gap: '4px' } },
      h('span', { 'data-testid': 'dx-next' }, nextStep(record)),
      record.intervention && o.root_status !== 'mastered' ? h('span', { class: 'small' }, record.intervention) : null)),
    competing.length ? row('مرشح آخر محتمل', h('span', { 'data-testid': 'dx-competing' },
      `${competing.map((c) => q(c.name_ar || c.skill)).join('، ')}: أخطاء فيه أيضاً، لذلك خُفّضت الثقة. سنراقبه أثناء التدريب.`)) : null);
}

/** The latest backend record for this root (or the newest one). `live` is the diagnosis returned with the answer
 *  that named the root; it only fills the competing list if the stored record has none (older databases). */
export function pickRecord(list, live, names) {
  const records = list || [];
  let rec = live ? records.find((r) => r.root_skill === live.root && r.origin_skill === live.origin) : null;
  rec = rec || records[0] || null;
  if (rec && live && rec.root_skill === live.root && !(rec.competing || []).length && (live.competing || []).length) {
    rec = { ...rec, competing: live.competing.map((s) => ({ skill: s, name_ar: (names && names[s]) || s })) };
  }
  return rec;
}

/** The "root found" call to action plus its expandable card. The card is fetched fresh every time it is opened. */
export function rootCta({ uid, live = null, names = {}, fresh = false }) {
  const slot = h('div', { class: 'dx-slot', hidden: true });
  const btn = h('button', { class: ['root-cta', fresh ? 'fresh' : ''], type: 'button', 'data-testid': 'root-cta', 'aria-expanded': 'false' },
    h('span', { class: 'root-cta-ico' }, ico('target')),
    h('span', { class: 'grow col', style: { gap: '0' } }, h('b', null, 'ظهر جذر المشكلة'), h('span', { class: 'small' }, 'اضغط لعرض بطاقة التشخيص')),
    ico('chevl'));
  let open = false;
  let token = 0;
  async function show() {
    const mine = ++token;
    slot.removeAttribute('hidden');
    slot.hidden = false;
    mount(slot, h('div', { class: 'dx-panel' }, h('div', { class: 'row' }, h('div', { class: 'spin' }), h('span', null, 'نحمّل التشخيص الحالي…'))));
    let rec = null;
    try {
      const res = await api.get(`/students/${uid}/adaptive/diagnoses`);
      rec = pickRecord(res && res.diagnoses, live, names);
    } catch (e) {
      rec = null;
    }
    if (mine !== token || !open) return;
    if (!rec) {
      mount(slot, h('div', { class: 'dx-panel' }, h('p', { class: 'muted', style: { margin: 0 } }, 'تعذّر تحميل بطاقة التشخيص الآن. حاول مرة أخرى بعد قليل.')));
      return;
    }
    mount(slot, diagnosisPanel(rec));
  }
  btn.addEventListener('click', () => {
    open = !open;
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    btn.classList.remove('fresh');
    if (open) show();
    else {
      token += 1;
      slot.setAttribute('hidden', '');
      slot.hidden = true;
    }
  });
  return h('div', { class: 'root-cta-wrap' }, btn, slot);
}
