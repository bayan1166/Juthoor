import { h, ico, mount, clear, fmtDate, timeAgo, skeleton } from '../dom.js';
import { api } from '../api.js';
import { store } from '../store.js';
import { renderTreeStage } from '../tree.js';
import { errorPanel, upsellCard, lockedChain } from './shared.js';

export function chainFrom(events) {
  const chrono = events.slice().reverse();
  const names = [];
  for (const e of chrono) {
    if (!names.length) names.push(e.from_name_ar);
    if (names[names.length - 1] !== e.to_name_ar) names.push(e.to_name_ar);
  }
  return names;
}

export function reportText({ name, tree, report, insights }) {
  const s = tree.summary;
  const lines = [`تقرير جذور عن ${name}`, `صحة الشجرة: ${Math.round(tree.tree_health * 100)}%`, `الدروس المتقنة: ${s.mastered} من ${s.live}`];
  if (s.answered) lines.push(`دقة الإجابات: ${Math.round((s.correct / s.answered) * 100)}%`);
  if (tree.root_gap && tree.root_gap.found && !tree.root_gap.locked) lines.push(`الجذر المرصود: ${tree.root_gap.name_ar}`);
  else if (report.gap_locked) lines.push('رصد النظام جذراً وراء التعثّر، ويظهر كاملاً في باقة برو.');
  if (report.forecast && report.forecast.days) lines.push(`المدة المتوقعة لسدّ الفجوة: نحو ${report.forecast.days} يوماً`);
  if (insights) lines.push(`أيام التدريب المتتالية: ${insights.engagement.current_streak}`);
  lines.push('', 'منصة جذور: نجد الدرس الذي يتعثّر فيه الطالب فعلاً، لا الدرس الذي أخطأ فيه فقط.');
  return lines.join('\n');
}

export function whatsappUrl(text) {
  return `https://wa.me/?text=${encodeURIComponent(text)}`;
}

export function shareOnWhatsApp(text) {
  window.open(whatsappUrl(text), '_blank', 'noopener');
}

function chainEl(report, rootName) {
  const names = chainFrom(report.drilldowns || []);
  if (!names.length && !report.gap_locked) return h('p', { class: 'muted' }, 'لم يرصد النظام فجوة جذرية حتى الآن. استمر في التدريب.');
  const nodes = [];
  names.forEach((n, i) => {
    nodes.push(h('span', { class: ['node', i === names.length - 1 && !report.drilldowns_hidden && rootName ? 'root' : ''] }, n));
    if (i < names.length - 1 || report.drilldowns_hidden) nodes.push(h('span', { class: 'arrow' }, ico('chevl')));
  });
  const wrap = h('div', { class: 'chain' }, nodes);
  if (report.drilldowns_hidden) wrap.appendChild(lockedChain(report.drilldowns_hidden));
  return wrap;
}

const STAGE = {
  pending: 'لم يبدأ العلاج بعد',
  remediating: 'العلاج جارٍ',
  resolved: 'أُغلقت الفجوة',
};

function tally(t) {
  return `${t.right} صحيحة و${t.wrong} خاطئة`;
}

const LESSON_STATUS = { mastered: 'متقن', gap: 'فجوة قيد العلاج', learning: 'قيد التعلّم', untouched: 'لم يبدأ بعد' };

// Live part of a record (recomputed by the backend on every request): current mastery of the root and status
// of the original lesson, so the report follows the learner instead of freezing at the moment of diagnosis.
function liveLine(dg) {
  const o = dg.outcome || {};
  const parts = [];
  if (typeof o.root_mastery === 'number') parts.push(`إتقان «${dg.root_name_ar}» الآن: ${Math.round(o.root_mastery * 100)}%`);
  if (dg.origin_skill !== dg.root_skill && o.origin_status) parts.push(`الدرس الأصلي «${dg.origin_name_ar}»: ${LESSON_STATUS[o.origin_status] || o.origin_status}`);
  return parts.length ? h('div', { class: 'small', 'data-testid': 'diagnosis-live' }, h('b', null, 'الحالة الآن: '), parts.join(' | ')) : null;
}

// The explainable diagnosis record for the parent: where the gap started, the evidence, the honest
// confidence level, the suggested intervention and what happened after it (remediation, retry).
export function diagnosisRecord(report) {
  if (report.gap_locked) return null;
  const list = report.diagnoses || [];
  if (!list.length) return h('div', { class: 'card', 'data-testid': 'diagnosis-record' }, h('h3', null, 'سجل التشخيص'), h('p', { class: 'muted' }, 'لم يُسمَّ جذر بعد: جذور لا يحكم قبل توفر أدلة كافية.'));
  return h('div', { class: 'card', 'data-testid': 'diagnosis-record' }, h('h3', null, 'سجل التشخيص'),
    list.slice(0, 3).map((dg) => h('div', { class: 'diag', style: { marginBottom: '10px' } },
      h('div', { class: 'diag-path' }, (dg.path || []).map((p, i) => [i ? h('span', { class: 'diag-arrow' }, ico('chevl')) : null,
        h('span', { class: ['chip', p.skill === dg.root_skill ? 'red' : ''] }, p.name_ar)])),
      h('div', { class: 'small' }, h('b', null, 'التعثّر الظاهر في: '), dg.origin_name_ar),
      h('div', { class: 'small' }, h('b', null, 'الجذر الأرجح: '), dg.root_name_ar, ` | الثقة: ${dg.confidence}`, ` | ${timeAgo(dg.created_at)}`),
      dg.explanation ? h('div', { class: 'small' }, dg.explanation) : null,
      (dg.evidence || []).length ? h('div', { class: 'small muted' }, 'الأدلة: ', dg.evidence.map((e) => `${e.name_ar}: ${e.wrong} خاطئة و${e.right} صحيحة`).join(' | ')) : null,
      (dg.competing || []).length ? h('div', { class: 'small' }, h('b', null, 'مرشح آخر محتمل: '), dg.competing.map((c) => `«${c.name_ar}»`).join('، '), '، لذلك خُفّضت الثقة.') : null,
      dg.intervention ? h('div', { class: 'small' }, h('b', null, 'الخطوة التالية المقترحة: '), dg.intervention) : null,
      h('div', { class: 'small' }, h('b', null, 'بعد التشخيص: '), STAGE[dg.outcome.stage] || dg.outcome.stage,
        ` | على الجذر: ${tally(dg.outcome.root_after)}`,
        dg.origin_skill !== dg.root_skill ? ` | إعادة المحاولة على «${dg.origin_name_ar}»: ${tally(dg.outcome.origin_retry)}` : ''),
      liveLine(dg))),
    h('p', { class: 'small muted', style: { margin: 0 } }, 'التشخيص تقدير مبني على الأدلة، والثقة مستوى وليست نسبة احتمال.'));
}

function forecastEl(f) {
  if (!f) return null;
  return h('div', { class: 'banner' }, ico('clock'), h('div', null, h('b', null, `توقّع سدّ الفجوة في «${f.name_ar}»: `),
    f.remaining_correct === 0 ? 'اكتملت المتطلبات تقريباً.' : f.days ? `نحو ${f.days} يوماً بمعدل ${f.per_day} إجابة صحيحة يومياً (يتبقى ${f.remaining_correct} إجابة صحيحة).` : 'ابدأ التدريب ليتمكن النظام من حساب المدة.'));
}

function alertsEl(insights) {
  if (!insights.struggle_alerts.length) return h('p', { class: 'muted' }, 'لا تنبيهات تعثّر حالياً.');
  return h('div', { class: 'table-wrap' }, h('table', { class: 't' },
    h('thead', null, h('tr', null, ['الدرس', 'الخطورة', 'الإتقان', 'إخفاقات متتالية', 'الإجراء المقترح'].map((t) => h('th', null, t)))),
    h('tbody', null, insights.struggle_alerts.map((a) => h('tr', null,
      h('td', null, a.skill_name_ar),
      h('td', null, h('span', { class: ['risk', a.severity === 'high' ? 'high' : a.severity === 'medium' ? 'medium' : 'low'] }, { high: 'مرتفعة', medium: 'متوسطة', low: 'منخفضة' }[a.severity] || a.severity)),
      h('td', null, `${Math.round(a.p_mastery * 100)}%`), h('td', null, String(a.consecutive_misses)), h('td', null, a.recommended_action))))));
}

export async function parentView(ctx) {
  const page = h('div', { class: 'page page-enter wide' });
  ctx.root.appendChild(page);
  mount(page, skeleton(4, true));
  let kids;
  try {
    kids = await api.get('/me/students');
  } catch (err) {
    mount(page, errorPanel(err, () => ctx.reload()));
    return;
  }
  if (!kids.length) {
    mount(page, h('div', { class: 'empty card' }, ico('users'), h('h3', null, 'لا يوجد أبناء مرتبطون بحسابك'), h('p', { class: 'muted' }, 'اطلب من ابنك إدخال بريدك الإلكتروني في خانة بريد ولي الأمر عند إنشاء حسابه.')));
    return;
  }
  let childId = kids[0].student_id;
  try {
    childId = sessionStorage.getItem('juthoor.child') || childId;
  } catch (e) {
    childId = kids[0].student_id;
  }
  if (!kids.find((k) => k.student_id === childId)) childId = kids[0].student_id;
  const picker = h('select', { class: 'select', style: { width: 'auto', minWidth: '220px' }, 'aria-label': 'الابن' }, kids.map((k) => h('option', { value: k.student_id }, k.full_name)));
  picker.value = childId;
  const body = h('div', { class: 'col' });
  let ctrl = null;
  ctx.onDestroy(() => { if (ctrl) ctrl.destroy(); });

  async function load(silent = false) {
    const kid = kids.find((k) => k.student_id === childId);
    if (!silent) {
      if (ctrl) { ctrl.destroy(); ctrl = null; }
      mount(body, skeleton(4, true));
    }
    try {
      const [tree, report, insights] = await Promise.all([
        api.get(`/students/${childId}/adaptive/tree`), api.get(`/students/${childId}/adaptive/report`), api.get(`/students/${childId}/insights`),
      ]);
      if (ctx.destroyed) return;
      if (ctrl) { ctrl.destroy(); ctrl = null; }
      const holder = h('div');
      const planChip = h('span', { class: ['chip', report.plan.plan === 'basic' ? '' : 'green'] }, report.plan.plan === 'basic' ? 'الباقة المجانية' : 'برو');
      mount(body,
        holder,
        h('div', { class: 'card' }, h('div', { class: 'card-title' }, h('h3', null, `سلسلة الجذر لدى ${kid.full_name}`), h('div', { class: 'row' }, planChip, h('a', { class: 'btn btn-ghost btn-sm', href: `#/report/${childId}` }, ico('print'), 'تقرير قابل للطباعة'),
            h('button', { class: 'btn btn-primary btn-sm', type: 'button', onclick: () => shareOnWhatsApp(reportText({ name: kid.full_name, tree, report, insights })) }, ico('send'), 'مشاركة عبر واتساب'))),
          chainEl(report, tree.root_gap.found && !tree.root_gap.locked ? tree.root_gap.name_ar : ''), forecastEl(report.forecast)),
        report.gap_locked || report.drilldowns_hidden ? upsellCard({
          title: `اكشف الجذر الكامل لدى ${kid.full_name}`,
          text: 'نرصد أن هناك درساً سابقاً وراء التعثّر الحالي. باقة برو تكشف السلسلة كاملة، وتعطيك تقريراً مطبوعاً وتوقعاً للمدة اللازمة لسدّ الفجوة.',
          cta: 'فعّل برو لابنك', href: `#/checkout/pro?period=monthly&for=${childId}`,
        }) : null,
        diagnosisRecord(report),
        h('div', { class: 'card' }, h('div', { class: 'card-title' }, h('h3', null, 'تنبيهات التعثّر')), alertsEl(insights)),
        h('div', { class: 'grid g3' },
          h('div', { class: 'card kpi' }, h('span', { class: 'v' }, String(insights.engagement.current_streak)), h('span', { class: 'l' }, 'أيام متتالية من التدريب')),
          h('div', { class: 'card kpi' }, h('span', { class: 'v' }, String(insights.engagement.questions_answered_last_7)), h('span', { class: 'l' }, 'سؤال خلال 7 أيام')),
          h('div', { class: 'card kpi' }, h('span', { class: 'v' }, String(insights.engagement.active_days_last_30)), h('span', { class: 'l' }, 'يوم نشاط خلال 30 يوماً'))));
      ctrl = renderTreeStage(holder, tree, { embedded: true, canPractice: false, studentId: childId, title: `صحة شجرة ${kid.full_name}` });
    } catch (err) {
      if (!silent) mount(body, errorPanel(err, () => load()));
    }
  }

  // The report follows the child: coming back to this tab re-reads the live state (mastery, remediation,
  // retry outcome) instead of keeping what was loaded earlier.
  const onVisible = () => {
    if (!document.hidden && !ctx.destroyed) load(true);
  };
  document.addEventListener('visibilitychange', onVisible);
  ctx.onDestroy(() => document.removeEventListener('visibilitychange', onVisible));

  picker.addEventListener('change', () => {
    childId = picker.value;
    try {
      sessionStorage.setItem('juthoor.child', childId);
    } catch (e) {
      childId = picker.value;
    }
    load();
  });
  mount(page, h('div', { class: 'page-head' }, h('div', null, h('h1', null, 'متابعة الأبناء'), h('p', { class: 'muted' }, 'شجرة ابنك وجذر تعثّره وخطة سدّ الفجوة.')), picker), body);
  await load();
}

export async function reportView(ctx) {
  const id = ctx.params.id;
  const page = h('div', { class: 'page page-enter' });
  ctx.root.appendChild(page);
  mount(page, skeleton(5, true));
  try {
    const [report, tree, insights] = await Promise.all([
      api.get(`/students/${id}/adaptive/report`), api.get(`/students/${id}/adaptive/tree`), api.get(`/students/${id}/insights`),
    ]);
    const s = tree.summary;
    mount(page,
      h('div', { class: 'row between no-print', style: { maxWidth: '820px', margin: '0 auto 14px' } },
        h('button', { class: 'btn btn-ghost', onclick: () => history.back() }, ico('chevr'), 'رجوع'),
        h('div', { class: 'row' },
          h('button', { class: 'btn btn-ghost', type: 'button', onclick: () => shareOnWhatsApp(reportText({ name: report.student.full_name, tree, report, insights })) }, ico('send'), 'مشاركة عبر واتساب'),
          h('button', { class: 'btn btn-primary', onclick: () => window.print() }, ico('print'), 'طباعة التقرير'))),
      h('div', { class: 'report' },
        h('div', { class: 'row between' }, h('div', null, h('h1', { style: { marginBottom: '2px' } }, 'تقرير مسح الجذر'), h('div', { class: 'muted' }, `${report.student.full_name} | ${fmtDate(new Date().toISOString())}`)), h('b', { class: 'report-brand' }, 'جذور')),
        h('hr', { class: 'report-rule' }),
        h('div', { class: 'grid g3' },
          h('div', { class: 'kpi' }, h('span', { class: 'v' }, `${Math.round(tree.tree_health * 100)}%`), h('span', { class: 'l' }, 'صحة الشجرة')),
          h('div', { class: 'kpi' }, h('span', { class: 'v' }, `${s.mastered}/${s.live}`), h('span', { class: 'l' }, 'دروس متقنة')),
          h('div', { class: 'kpi' }, h('span', { class: 'v' }, `${s.answered ? Math.round((s.correct / s.answered) * 100) : 0}%`), h('span', { class: 'l' }, 'دقة الإجابات'))),
        h('h3', { style: { marginTop: '24px' } }, 'سلسلة الجذر'),
        chainEl(report, tree.root_gap.found && !tree.root_gap.locked ? tree.root_gap.name_ar : ''),
        tree.root_gap.found && !tree.root_gap.locked ? h('p', { style: { marginTop: '10px' } }, `الجذر المرصود: ${tree.root_gap.name_ar}، على بعد ${tree.root_gap.steps_back} خطوات من الدرس الحالي.`) : null,
        report.gap_locked ? h('div', { class: 'banner no-print' }, ico('lock'), h('div', null, 'سلسلة الجذر الكاملة متاحة في باقة برو.', ' ', h('a', { href: '#/plans' }, 'اعرف المزيد'))) : null,
        report.forecast ? h('div', { style: { marginTop: '14px' } }, forecastEl(report.forecast)) : null,
        diagnosisRecord(report) ? h('div', { style: { marginTop: '18px' } }, diagnosisRecord(report)) : null,
        h('h3', { style: { marginTop: '24px' } }, 'تنبيهات التعثّر'), alertsEl(insights),
        h('h3', { style: { marginTop: '24px' } }, 'النشاط'),
        h('p', null, `${insights.engagement.questions_answered_last_7} سؤالاً خلال آخر 7 أيام، و${insights.engagement.active_days_last_30} يوم نشاط خلال 30 يوماً، وسلسلة حالية ${insights.engagement.current_streak} أيام.`),
        h('p', { class: 'small muted', style: { marginTop: '24px' } }, 'أُنشئ هذا التقرير آلياً بواسطة منصة جذور.')));
  } catch (err) {
    mount(page, errorPanel(err, () => ctx.reload()));
  }
}
