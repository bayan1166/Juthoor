import { h, ico, mount, clear, toast, openModal, openDrawer, confirmDialog, countTo, fmtDate, timeAgo, avatarEl, copyText, skeleton } from '../dom.js';
import { api } from '../api.js';
import { store } from '../store.js';
import { renderTreeStage } from '../tree.js';
import { errorPanel, handleError, upsellCard, skillList } from './shared.js';
import { leaderboardRows } from './classes.js';
import { chainFrom } from './parent.js';

const RISK = { high: 'مرتفعة', medium: 'متوسطة', low: 'منخفضة', inactive: 'غير نشط' };
const REASONS = { bullying: 'تنمّر أو إساءة', inappropriate: 'محتوى غير لائق', contact_info: 'طلب معلومات شخصية أو أرقام', spam: 'إزعاج أو رسائل متكررة', other: 'سبب آخر' };
const DAYS = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'];

function planError(err, retry) {
  if (err.upsell) {
    return upsellCard({
      title: 'هذه الميزة تحتاج باقة المدرسة',
      text: 'انتهت تجربتك المجانية أو لم تفعّل باقة المدرسة بعد. اشترك لتتابع لوحة التحليلات والواجبات والاختبارات، ويحصل طلابك على برو دون أي رسوم.',
      cta: 'اشترك في باقة المدرسة',
    });
  }
  return errorPanel(err, retry);
}

function kpi(label, value, suffix = '') {
  const v = h('span', { class: 'v' }, '0');
  setTimeout(() => countTo(v, value, 800, suffix), 30);
  return h('div', { class: 'card kpi' }, v, h('span', { class: 'l' }, label));
}

export async function teacherView(ctx) {
  const me = store.me;
  const page = h('div', { class: 'page page-enter wide' });
  const headerBox = h('div');
  const bodyBox = h('div', { class: 'col' });
  page.appendChild(headerBox);
  page.appendChild(bodyBox);
  ctx.root.appendChild(page);
  let classes = [];
  let cid = '';
  let tab = 'overview';
  let skills = [];

  try {
    cid = sessionStorage.getItem('juthoor.class') || '';
  } catch (e) {
    cid = '';
  }

  function current() {
    return classes.find((c) => c.classroom_id === cid) || null;
  }

  async function loadClasses() {
    classes = await api.get('/classrooms');
    if (!current()) cid = classes[0] ? classes[0].classroom_id : '';
  }

  function codeModal(c) {
    openModal({
      title: 'رمز الانضمام للصف',
      content: h('div', { class: 'col center' }, h('p', { class: 'muted' }, 'شارك هذا الرمز مع طلابك ليدخلوه من صفحة «صفوفي».'),
        h('div', { class: 'ltr', style: { fontSize: '2.4rem', fontWeight: 800, letterSpacing: '.3em', color: 'var(--g-700)' } }, c.join_code),
        h('button', { class: 'btn btn-primary', onclick: async () => { toast((await copyText(c.join_code)) ? 'تم نسخ الرمز.' : 'تعذّر النسخ.', 'info'); } }, ico('copy'), 'نسخ الرمز')),
    });
  }

  function newClass() {
    const name = h('input', { class: 'input', placeholder: 'مثال: السادس أ - رياضيات', maxlength: '120' });
    const err = h('div', { class: 'err' });
    openModal({
      title: 'صف جديد',
      content: h('div', { class: 'col' }, h('div', { class: 'field' }, h('label', null, 'اسم الصف'), name), err),
      actions: [
        { label: 'إلغاء', kind: 'ghost' },
        { label: 'إنشاء الصف', kind: 'primary', close: false, onClick: async ({ close }) => {
          err.textContent = '';
          if (name.value.trim().length < 2) {
            err.textContent = 'اكتب اسماً للصف.';
            return false;
          }
          try {
            const c = await api.post('/classrooms', { name: name.value.trim() });
            close();
            cid = c.classroom_id;
            await loadClasses();
            paintAll();
            codeModal(c);
          } catch (ex) {
            if (ex.upsell) {
              close();
              handleError(ex);
            } else {
              err.textContent = ex.message;
            }
            return false;
          }
          return true;
        } },
      ],
    });
    setTimeout(() => name.focus(), 60);
  }

  function paintHeader() {
    const picker = h('select', { class: 'select', style: { width: 'auto', minWidth: '220px' }, 'aria-label': 'الصف' }, classes.map((c) => h('option', { value: c.classroom_id }, c.name)));
    picker.value = cid;
    picker.addEventListener('change', () => {
      cid = picker.value;
      try {
        sessionStorage.setItem('juthoor.class', cid);
      } catch (e) {
        cid = picker.value;
      }
      paintTab();
    });
    const banners = [];
    if (me.plan_source === 'trial') banners.push(h('div', { class: 'banner' }, ico('shield'), h('div', { class: 'grow' }, `تجربتك المجانية لباقة المدرسة تنتهي بعد ${me.trial_days_left} يوماً.`), h('a', { class: 'btn btn-primary btn-sm', href: '#/plans' }, 'اشترك الآن')));
    else if (me.plan !== 'school' && me.role !== 'platform_admin') banners.push(upsellCard({ title: 'انتهت باقة المدرسة', text: 'جدّد اشتراكك لتتابع إنشاء الصفوف والواجبات والاختبارات وعرض التحليلات.', cta: 'جدّد الاشتراك' }));
    mount(headerBox,
      h('div', { class: 'page-head' }, h('div', null, h('h1', null, 'لوحة المعلم'), h('p', { class: 'muted' }, 'تحليلات الأداء والواجبات والاختبارات ولوحات المتصدرين.')),
        h('div', { class: 'row' }, classes.length ? picker : null, h('button', { class: 'btn btn-primary', onclick: newClass }, ico('plus'), 'صف جديد'))),
      banners);
  }

  function paintTabs() {
    const tabs = h('div', { class: 'tabs', style: { marginBottom: '18px' } });
    [['overview', 'نظرة عامة'], ['classes', 'الصفوف والطلاب'], ['assignments', 'الواجبات'], ['quizzes', 'الاختبارات'], ['board', 'لوحة الصدارة'], ['safety', 'السلامة']].forEach(([id, label]) => {
      tabs.appendChild(h('button', { class: tab === id ? 'on' : '', onclick: () => { tab = id; paintTab(); } }, label));
    });
    return tabs;
  }

  function paintAll() {
    paintHeader();
    paintTab();
  }

  function paintTab() {
    if (!classes.length) {
      mount(bodyBox, h('div', { class: 'card empty' }, ico('users'), h('h2', null, 'أنشئ صفك الأول'), h('p', { class: 'muted' }, 'أنشئ صفاً وشارك رمز الانضمام مع طلابك، وستظهر هنا تحليلات كل طالب وجذر تعثّره.'),
        h('button', { class: 'btn btn-primary btn-lg', onclick: newClass }, ico('plus'), 'إنشاء صف')));
      return;
    }
    const box = h('div', { class: 'col' });
    mount(bodyBox, paintTabs(), box);
    if (tab === 'overview') overview(box);
    else if (tab === 'classes') classesTab(box);
    else if (tab === 'assignments') assignmentsTab(box);
    else if (tab === 'quizzes') quizzesTab(box);
    else if (tab === 'safety') safetyTab(box);
    else boardTab(box);
  }

  async function studentDrawer(row) {
    const holder = h('div', { class: 'col' }, skeleton(4, true));
    let ctrl = null;
    openDrawer({ title: row.full_name, content: holder, onClose: () => { if (ctrl) ctrl.destroy(); } });
    try {
      const [report, tree] = await Promise.all([api.get(`/students/${row.user_id}/adaptive/report`), api.get(`/students/${row.user_id}/adaptive/tree`)]);
      const names = chainFrom(report.drilldowns || []);
      const chain = names.length
        ? h('div', { class: 'chain' }, names.map((n, i) => [h('span', { class: ['node', i === names.length - 1 && tree.root_gap.found ? 'root' : ''] }, n), i < names.length - 1 ? h('span', { class: 'arrow' }, ico('chevl')) : null]))
        : h('p', { class: 'muted' }, 'لا فجوة جذرية مرصودة.');
      mount(holder,
        h('div', { class: 'card' }, h('div', { class: 'row nowrap' }, avatarEl(row, 'lg'), h('div', { class: 'grow' }, h('h3', { style: { margin: 0 } }, row.full_name), h('div', { class: 'small muted ltr' }, `#${row.handle || ''}`), h('span', { class: ['risk', row.risk] }, RISK[row.risk])))),
        h('div', { class: 'grid g2' },
          h('div', { class: 'card kpi' }, h('span', { class: 'v' }, `${Math.round(tree.tree_health * 100)}%`), h('span', { class: 'l' }, 'صحة الشجرة')),
          h('div', { class: 'card kpi' }, h('span', { class: 'v' }, `${tree.summary.mastered}/${tree.summary.live}`), h('span', { class: 'l' }, 'دروس متقنة'))),
        h('div', { class: 'card' }, h('h3', null, 'سلسلة الجذر'), chain,
          report.forecast ? h('div', { class: 'banner', style: { marginTop: '12px' } }, ico('clock'), h('div', null, `توقّع سدّ الفجوة في «${report.forecast.name_ar}»: ${report.forecast.remaining_correct === 0 ? 'اكتملت المتطلبات تقريباً' : report.forecast.days ? `نحو ${report.forecast.days} يوماً` : 'يحتاج الطالب لبدء التدريب'}.`)) : null),
        h('div', { class: 'card' }, h('div', { class: 'small muted' }, `آخر نشاط: ${row.last_active ? timeAgo(row.last_active) : 'لم يبدأ بعد'}`), h('div', { class: 'small muted' }, `الدرس الحالي: ${row.current_skill || '-'}`), h('div', { class: 'small muted' }, `الواجبات المسلّمة: ${row.submissions_done} من ${row.assignments_total}`)),
        h('button', { class: 'btn btn-primary', onclick: () => {
          const host = h('div');
          let inner = null;
          openModal({ title: `شجرة ${row.full_name}`, size: 'lg', content: host, onClose: () => { if (inner) inner.destroy(); } });
          inner = renderTreeStage(host, tree, { embedded: true, canPractice: false, studentId: row.user_id, title: 'صحة الشجرة' });
        } }, ico('tree'), 'عرض الشجرة كاملة'));
    } catch (err) {
      mount(holder, planError(err));
    }
  }

  async function overview(box) {
    mount(box, skeleton(5, true));
    let r;
    try {
      r = await api.get(`/classrooms/${cid}/analytics`);
    } catch (err) {
      mount(box, planError(err, () => overview(box)));
      return;
    }
    if (ctx.destroyed) return;
    const k = r.kpis;
    const maxAnswers = Math.max(1, ...r.activity.map((a) => a.answers));
    const bars = h('div', { class: 'bars' }, r.activity.map((a) => {
      const i = h('i');
      setTimeout(() => { i.style.height = `${Math.max(3, Math.round((a.answers / maxAnswers) * 100))}%`; }, 40);
      return h('div', { class: 'b' }, h('b', { class: 'small' }, String(a.answers)), i, h('span', null, DAYS[new Date(`${a.date}T12:00:00`).getDay()]));
    }));
    const mastery = r.skill_mastery.map((s) => {
      const fill = h('i');
      setTimeout(() => { fill.style.width = `${Math.round(s.avg * 100)}%`; }, 40);
      return h('div', { class: 'hbar' }, h('span', { class: 'small' }, s.name_ar), h('div', { class: 'bar' }, fill), h('b', { class: 'small' }, `${Math.round(s.avg * 100)}%`));
    });
    let sortKey = 'risk';
    let dir = 1;
    let q = '';
    const order = { high: 0, medium: 1, low: 2, inactive: 3 };
    const tableHost = h('div');
    const val = (row, key) => (key === 'risk' ? order[row.risk] : key === 'full_name' ? row.full_name : key === 'last_active' ? (row.days_since_active === null ? 1e6 : row.days_since_active) : row[key] === null ? -1 : row[key]);
    function paintTable() {
      const rows = r.students.filter((s) => s.full_name.includes(q.trim())).sort((a, b) => {
        const x = val(a, sortKey);
        const y = val(b, sortKey);
        return (x < y ? -1 : x > y ? 1 : 0) * dir;
      });
      const head = [['full_name', 'الطالب'], ['tree_health', 'صحة الشجرة'], ['accuracy', 'الدقة'], ['last_active', 'آخر نشاط'], ['quiz_points', 'نقاط الاختبارات'], ['submissions_done', 'الواجبات'], ['risk', 'الخطورة']];
      mount(tableHost, h('div', { class: 'table-wrap' }, h('table', { class: 't' },
        h('thead', null, h('tr', null, head.map(([key, label]) => h('th', { class: 'sort', onclick: () => { dir = sortKey === key ? -dir : 1; sortKey = key; paintTable(); } }, label), h('th', null, 'الفجوات')))),
        h('tbody', null, rows.length ? rows.map((s) => {
          const fill = h('i');
          setTimeout(() => { fill.style.width = `${Math.round(s.tree_health * 100)}%`; }, 40);
          const tr = h('tr', { class: 'click' },
            h('td', null, h('div', { class: 'row nowrap' }, avatarEl(s, 'sm'), h('div', null, h('b', null, s.full_name), h('div', { class: 'small muted' }, s.current_skill || '-')))),
            h('td', { style: { minWidth: '120px' } }, h('div', { class: 'row nowrap' }, h('div', { class: 'bar grow' }, fill), h('b', { class: 'small' }, `${Math.round(s.tree_health * 100)}%`))),
            h('td', null, s.accuracy === null ? '-' : `${Math.round(s.accuracy * 100)}%`),
            h('td', null, s.last_active ? timeAgo(s.last_active) : 'لم يبدأ'),
            h('td', null, String(s.quiz_points)),
            h('td', null, `${s.submissions_done}/${s.assignments_total}`),
            h('td', null, h('span', { class: ['risk', s.risk] }, RISK[s.risk])),
            h('td', null, s.root_gaps.length ? s.root_gaps.map((g) => h('span', { class: 'chip red', style: { margin: '2px' } }, g)) : h('span', { class: 'muted' }, '-')));
          tr.addEventListener('click', () => studentDrawer(s));
          return tr;
        }) : h('tr', null, h('td', { colspan: '8', class: 'center muted' }, 'لا طلاب في هذا الصف بعد.'))))));
    }
    const search = h('input', { class: 'input', placeholder: 'ابحث عن طالب', style: { maxWidth: '260px' } });
    search.addEventListener('input', () => { q = search.value; paintTable(); });
    mount(box,
      h('div', { class: 'kpis' }, kpi('عدد الطلاب', k.students), kpi('متوسط صحة الشجرة', Math.round(k.avg_tree_health * 100), '%'), kpi('متوسط الدقة', k.avg_accuracy === null ? 0 : Math.round(k.avg_accuracy * 100), '%'), kpi('طلاب نشطون هذا الأسبوع', k.active_last_7), kpi('طلاب في خطر', k.at_risk)),
      h('div', { class: 'grid g2' },
        h('div', { class: 'card' }, h('div', { class: 'card-title' }, h('h3', null, 'نشاط الصف خلال 7 أيام')), bars),
        h('div', { class: 'card' }, h('div', { class: 'card-title' }, h('h3', null, 'أكثر الفجوات انتشاراً')),
          r.top_gaps.length ? r.top_gaps.map((g) => h('div', { class: 'row between', style: { padding: '8px 0', borderBottom: '1px dashed var(--line)' } }, h('div', { class: 'row' }, h('b', null, g.name_ar), h('span', { class: 'chip red' }, `${g.students} طالب`)), h('button', { class: 'btn btn-primary btn-sm', type: 'button', onclick: () => assignRemediation(g, r.students) }, ico('target'), 'تكليف علاجي'))) : h('p', { class: 'muted' }, 'لا فجوات جذرية مرصودة حالياً.'))),
      h('div', { class: 'card' }, h('div', { class: 'card-title' }, h('h3', null, 'إتقان المهارات (متوسط الصف)')), mastery),
      h('div', { class: 'card' }, h('div', { class: 'card-title' }, h('h3', null, 'الطلاب'),
        h('div', { class: 'row' }, search, h('button', { class: 'btn btn-ghost btn-sm', onclick: async () => {
          try {
            await api.download(`/classrooms/${cid}/export.csv`, 'class-report.csv');
          } catch (err) {
            handleError(err);
          }
        } }, ico('download'), 'تصدير CSV'))), tableHost));
    paintTable();
  }

  async function assignRemediation(gap, students) {
    const targets = students.filter((s) => (s.root_gap_ids || []).includes(gap.skill_id));
    const names = targets.map((s) => s.full_name).join('، ');
    const ok = await confirmDialog(`سيُنشأ واجب علاجي «تقوية: ${gap.name_ar}» موجّه إلى ${targets.length} طلاب لديهم هذه الفجوة فقط: ${names}.`, { title: 'تكليف علاجي بنقرة واحدة', confirmLabel: 'إنشاء التكليف' });
    if (!ok) return;
    try {
      const res = await api.post(`/classrooms/${cid}/remediation`, { skill_id: gap.skill_id });
      await loadClasses();
      openModal({
        title: 'تم إنشاء التكليف العلاجي',
        content: h('div', { class: 'col' },
          h('p', null, `وُجّه الواجب إلى ${res.count} طلاب:`),
          h('div', { class: 'row' }, res.students.map((st) => h('span', { class: 'chip green' }, st.full_name))),
          h('div', { class: 'banner' }, ico('info'), h('div', null, h('b', null, 'اقتراح تدخل للمعلم: '), res.tip))),
        actions: [
          { label: 'إغلاق', kind: 'ghost' },
          { label: 'عرض الواجبات', kind: 'primary', onClick: () => { tab = 'assignments'; paintTab(); } },
        ],
      });
    } catch (err) {
      handleError(err);
    }
  }

  let safetyFilter = 'open';

  function reportCard(r, box) {
    return h('div', { class: 'card lift' },
      h('div', { class: 'row between' },
        h('div', null, h('h3', { style: { margin: 0 } }, REASONS[r.reason] || r.reason), h('div', { class: 'small muted' }, `${r.reporter.full_name} أبلغ عن ${r.reported.full_name} | ${timeAgo(r.created_at)}`)),
        h('div', { class: 'row' }, r.has_message ? h('span', { class: 'chip' }, 'مع رسالة') : null, h('button', { class: 'btn btn-primary btn-sm', type: 'button', onclick: () => reportDrawer(r, box) }, 'مراجعة'))),
      r.details ? h('p', { class: 'small', style: { marginTop: '8px' } }, r.details) : null);
  }

  async function reportDrawer(r, box) {
    const holder = h('div', { class: 'col' }, skeleton(3, true));
    openDrawer({ title: 'مراجعة بلاغ', content: holder });
    try {
      const d = await api.get(`/classrooms/${cid}/safety/reports/${r.report_id}`);
      const note = h('textarea', { class: 'textarea', maxlength: '1000', placeholder: 'ملاحظة المعالجة (اختياري)' });
      const decide = async (action) => {
        try {
          await api.post(`/classrooms/${cid}/safety/reports/${r.report_id}/resolve`, { action, note: note.value.trim() });
          toast(action === 'resolved' ? 'تم تسجيل معالجة البلاغ.' : 'تم استبعاد البلاغ.', 'success');
          mount(holder, h('div', { class: 'banner' }, ico('check'), h('div', null, 'تم تسجيل القرار.')));
          safetyTab(box);
        } catch (err) {
          handleError(err);
        }
      };
      const status = { open: 'مفتوح', resolved: 'تمت المعالجة', dismissed: 'مستبعد' }[d.status] || d.status;
      mount(holder,
        h('div', { class: 'card' },
          h('div', { class: 'row' }, h('span', { class: 'chip red' }, REASONS[d.reason] || d.reason), h('span', { class: 'chip' }, status)),
          h('p', { class: 'small muted' }, `${d.reporter.full_name} أبلغ عن ${d.reported.full_name}`),
          d.details ? h('p', null, d.details) : null),
        h('div', { class: 'card' },
          h('h3', null, 'آخر الرسائل بين الطرفين'),
          d.thread.length
            ? d.thread.map((m) => h('div', { class: ['thread-row', m.flagged ? 'flagged' : ''] },
              h('div', { class: 'row between' }, h('b', null, m.sender_name), h('span', { class: 'small muted' }, timeAgo(m.created_at))),
              h('div', null, m.body),
              m.flagged ? h('span', { class: 'chip red' }, 'الرسالة المُبلَّغ عنها') : null))
            : h('p', { class: 'muted' }, 'لا رسائل.')),
        d.status === 'open'
          ? h('div', { class: 'card col' }, note,
            h('div', { class: 'row' },
              h('button', { class: 'btn btn-primary', type: 'button', onclick: () => decide('resolved') }, 'تمت المعالجة'),
              h('button', { class: 'btn btn-ghost', type: 'button', onclick: () => decide('dismissed') }, 'استبعاد البلاغ')))
          : (d.resolution_note ? h('div', { class: 'banner' }, ico('info'), h('div', null, d.resolution_note)) : null));
    } catch (err) {
      mount(holder, errorPanel(err, () => reportDrawer(r, box)));
    }
  }

  async function safetyTab(box) {
    mount(box, skeleton(3, true));
    try {
      const rows = await api.get(`/classrooms/${cid}/safety/reports?status_filter=${safetyFilter}`);
      const filters = h('div', { class: 'tabs' }, [['open', 'مفتوحة'], ['resolved', 'تمت معالجتها'], ['dismissed', 'مستبعدة']].map(([id, label]) => h('button', { class: safetyFilter === id ? 'on' : '', onclick: () => { safetyFilter = id; safetyTab(box); } }, label)));
      mount(box,
        h('div', { class: 'banner' }, ico('shield'), h('div', null, 'الدردشة في جذور بين الأصدقاء فقط، وتُمنع الروابط وأرقام الهاتف بين الطلاب. لا تظهر لك محادثات الطلاب إلا عندما يبلّغ أحدهم عن رسالة، وعندها ترى آخر الرسائل بين الطرفين فقط.')),
        filters,
        rows.length ? rows.map((r) => reportCard(r, box)) : h('div', { class: 'empty card' }, ico('shield'), h('p', null, safetyFilter === 'open' ? 'لا بلاغات مفتوحة. الصف بخير.' : 'لا بلاغات في هذه القائمة.')));
    } catch (err) {
      mount(box, planError(err, () => safetyTab(box)));
    }
  }

  async function classesTab(box) {
    const c = current();
    mount(box, skeleton(3, true));
    try {
      const members = await api.get(`/classrooms/${cid}/members`);
      mount(box,
        h('div', { class: 'card' }, h('div', { class: 'card-title' }, h('h3', null, c.name), h('button', { class: 'btn btn-ghost btn-sm', onclick: () => codeModal(c) }, ico('copy'), 'رمز الانضمام')),
          h('div', { class: 'row' }, h('span', { class: 'chip green' }, `${c.member_count} طالب`), h('span', { class: 'chip' }, `${c.assignment_count} واجب`), h('span', { class: 'chip' }, `${c.quiz_count} اختبار`), h('span', { class: 'chip lime ltr' }, c.join_code))),
        h('div', { class: 'card' }, h('div', { class: 'card-title' }, h('h3', null, 'الطلاب')),
          members.length ? members.map((m) => h('div', { class: 'row nowrap', style: { padding: '8px 0', borderBottom: '1px dashed var(--line)' } }, avatarEl(m, 'sm'), h('div', { class: 'grow' }, h('b', null, m.full_name), h('div', { class: 'small muted ltr' }, `#${m.handle || ''}`)),
            h('button', { class: 'btn btn-ghost btn-sm', 'aria-label': 'إزالة', onclick: async () => {
              if (!(await confirmDialog(`إزالة ${m.full_name} من الصف؟`, { confirmLabel: 'إزالة', danger: true }))) return;
              try {
                await api.del(`/classrooms/${cid}/members/${m.user_id}`);
                await loadClasses();
                paintTab();
              } catch (err) {
                handleError(err);
              }
            } }, ico('trash'))))
            : h('p', { class: 'muted' }, 'لم ينضم أحد بعد. شارك رمز الانضمام مع طلابك.')));
    } catch (err) {
      mount(box, planError(err, () => classesTab(box)));
    }
  }

  function assignmentForm() {
    const title = h('input', { class: 'input', maxlength: '200' });
    const desc = h('textarea', { class: 'textarea', placeholder: 'تعليمات الواجب' });
    const skill = h('select', { class: 'select' }, h('option', { value: '' }, 'بدون درس محدد'), skills.map((s) => h('option', { value: s.skill_id }, s.name_ar)));
    const target = h('input', { class: 'input', type: 'number', min: '0', max: '200', value: '0' });
    const max = h('input', { class: 'input', type: 'number', min: '1', max: '1000', value: '100' });
    const due = h('input', { class: 'input', type: 'datetime-local' });
    const err = h('div', { class: 'err' });
    openModal({
      title: 'واجب جديد', size: 'lg',
      content: h('div', { class: 'col' },
        h('div', { class: 'field' }, h('label', null, 'عنوان الواجب'), title), h('div', { class: 'field' }, h('label', null, 'الوصف'), desc),
        h('div', { class: 'grid g2' }, h('div', { class: 'field' }, h('label', null, 'الدرس المرتبط'), skill), h('div', { class: 'field' }, h('label', null, 'موعد التسليم'), due)),
        h('div', { class: 'grid g2' }, h('div', { class: 'field' }, h('label', null, 'عدد أسئلة التدريب المطلوبة (اختياري)'), target), h('div', { class: 'field' }, h('label', null, 'الدرجة العظمى'), max)), err),
      actions: [
        { label: 'إلغاء', kind: 'ghost' },
        { label: 'نشر الواجب', kind: 'primary', close: false, onClick: async ({ close }) => {
          err.textContent = '';
          if (title.value.trim().length < 2) {
            err.textContent = 'اكتب عنواناً للواجب.';
            return false;
          }
          const body = { title: title.value.trim(), description: desc.value.trim(), target_questions: Number(target.value) || 0, max_score: Number(max.value) || 100 };
          if (skill.value) body.skill_id = skill.value;
          if (due.value) body.due_at = new Date(due.value).toISOString();
          try {
            await api.post(`/classrooms/${cid}/assignments`, body);
            close();
            toast('تم نشر الواجب.', 'success');
            await loadClasses();
            paintTab();
          } catch (ex) {
            if (ex.upsell) {
              close();
              handleError(ex);
            } else err.textContent = ex.message;
            return false;
          }
          return true;
        } },
      ],
    });
  }

  async function assignmentDrawer(a) {
    const holder = h('div', { class: 'col' }, skeleton(4, true));
    openDrawer({ title: a.title, content: holder });
    try {
      const detail = await api.get(`/classrooms/assignments/${a.assignment_id}`);
      mount(holder,
        h('div', { class: 'card' }, detail.description ? h('p', null, detail.description) : null, h('div', { class: 'small muted' }, `${detail.due_at ? `التسليم: ${fmtDate(detail.due_at, true)}` : 'بلا موعد نهائي'} | الدرجة العظمى ${detail.max_score}`)),
        detail.students.map((s) => {
          const sub = s.submission;
          const score = h('input', { class: 'input', type: 'number', min: '0', max: String(detail.max_score), value: sub && sub.score !== null ? String(sub.score) : '', style: { maxWidth: '110px' }, 'aria-label': 'الدرجة' });
          const fb = h('input', { class: 'input', placeholder: 'تغذية راجعة للطالب', value: sub ? sub.feedback : '' });
          score.value = sub && sub.score !== null ? String(sub.score) : '';
          fb.value = sub ? sub.feedback : '';
          return h('div', { class: 'card' },
            h('div', { class: 'row between' }, h('div', { class: 'row nowrap' }, avatarEl(s, 'sm'), h('b', null, s.full_name)),
              sub ? h('span', { class: ['chip', sub.graded_at ? 'green' : 'lime'] }, sub.graded_at ? `صُحّح: ${sub.score}/${detail.max_score}` : 'بانتظار التصحيح') : h('span', { class: 'chip' }, 'لم يسلّم')),
            sub ? h('div', { class: 'col', style: { marginTop: '10px' } },
              sub.text ? h('div', { class: 'explain' }, sub.text) : null,
              sub.has_file ? h('div', null, h('button', { class: 'btn btn-ghost btn-sm', onclick: async () => {
                try {
                  await api.download(`/classrooms/submissions/${sub.submission_id}/file`, sub.file_name || 'submission');
                } catch (err) {
                  handleError(err);
                }
              } }, ico('download'), sub.file_name)) : null,
              sub.late ? h('span', { class: 'chip amber' }, 'تسليم متأخر') : null,
              h('div', { class: 'row nowrap' }, score, h('div', { class: 'grow' }, fb), h('button', { class: 'btn btn-primary btn-sm', onclick: async (e) => {
                const value = Number(score.value);
                if (score.value === '' || Number.isNaN(value) || value < 0 || value > detail.max_score) {
                  toast(`الدرجة بين 0 و ${detail.max_score}.`, 'error');
                  return;
                }
                e.currentTarget.classList.add('is-busy');
                try {
                  await api.post(`/classrooms/submissions/${sub.submission_id}/grade`, { score: value, feedback: fb.value.trim() });
                  toast('تم حفظ الدرجة.', 'success');
                } catch (err) {
                  handleError(err);
                } finally {
                  e.currentTarget.classList.remove('is-busy');
                }
              } }, 'حفظ')))
              : null);
        }));
    } catch (err) {
      mount(holder, planError(err));
    }
  }

  async function assignmentsTab(box) {
    mount(box, skeleton(3, true));
    try {
      if (!skills.length) skills = await skillList();
      const all = await api.get('/classrooms/assignments');
      const rows = all.filter((a) => a.classroom_id === cid);
      mount(box,
        h('div', { class: 'row end' }, h('button', { class: 'btn btn-primary', onclick: assignmentForm }, ico('plus'), 'واجب جديد')),
        rows.length ? rows.map((a) => h('div', { class: 'card lift' },
          h('div', { class: 'row between' }, h('div', null, h('h3', { style: { margin: 0 } }, a.title), h('div', { class: 'small muted' }, `${a.due_at ? `التسليم: ${fmtDate(a.due_at, true)}` : 'بلا موعد نهائي'}${a.skill_name_ar ? ` | ${a.skill_name_ar}` : ''}`)),
            h('div', { class: 'row' }, a.kind === 'remediation' ? h('span', { class: 'chip amber' }, ico('target'), 'علاجي') : null, h('span', { class: 'chip' }, `${a.submissions}/${a.members} سلّموا`), h('span', { class: 'chip green' }, `${a.graded} مصحّح`), h('button', { class: 'btn btn-primary btn-sm', onclick: () => assignmentDrawer(a) }, 'فتح وتصحيح')))))
          : h('div', { class: 'empty card' }, ico('file'), h('p', null, 'لا واجبات في هذا الصف بعد. أنشئ أول واجب.')));
    } catch (err) {
      mount(box, planError(err, () => assignmentsTab(box)));
    }
  }

  function quizForm() {
    let mode = 'auto';
    const title = h('input', { class: 'input', maxlength: '200' });
    const kind = h('select', { class: 'select' }, h('option', { value: 'quiz' }, 'اختبار عادي'), h('option', { value: 'race' }, 'سباق سرعة (مكافأة للأسرع)'));
    const minutes = h('input', { class: 'input', type: 'number', min: '0', max: '120', value: '5' });
    const skill = h('select', { class: 'select' }, skills.map((s) => h('option', { value: s.skill_id }, s.name_ar)));
    const count = h('input', { class: 'input', type: 'number', min: '3', max: '20', value: '8' });
    const err = h('div', { class: 'err' });
    const questions = [];
    const list = h('div');
    const autoBox = h('div', { class: 'grid g2' }, h('div', { class: 'field' }, h('label', null, 'الدرس'), skill), h('div', { class: 'field' }, h('label', null, 'عدد الأسئلة'), count));
    const manualBox = h('div', null, list, h('button', { class: 'btn btn-ghost btn-sm', type: 'button', onclick: () => { questions.push({ prompt: '', options: ['', '', '', ''], correct: 0, points: 100 }); paintQs(); } }, ico('plus'), 'إضافة سؤال'));
    function paintQs() {
      mount(list, questions.map((q, i) => h('div', { class: 'qb' },
        h('div', { class: 'row between' }, h('b', null, `السؤال ${i + 1}`), h('button', { class: 'btn btn-ghost btn-sm', type: 'button', 'aria-label': 'حذف', onclick: () => { questions.splice(i, 1); paintQs(); } }, ico('trash'))),
        h('input', { class: 'input', placeholder: 'نص السؤال', value: q.prompt, oninput: (e) => { q.prompt = e.target.value; } }),
        q.options.map((o, j) => h('div', { class: 'row nowrap', style: { marginTop: '8px' } },
          h('input', { type: 'radio', name: `c${i}`, checked: q.correct === j, onchange: () => { q.correct = j; }, 'aria-label': 'الإجابة الصحيحة' }),
          h('input', { class: 'input', placeholder: `الخيار ${j + 1}`, value: o, oninput: (e) => { q.options[j] = e.target.value; } }))))));
    }
    const modeSeg = h('div', { class: 'seg' });
    function paintMode() {
      mount(modeSeg, h('button', { type: 'button', class: mode === 'auto' ? 'on' : '', onclick: () => { mode = 'auto'; paintMode(); } }, 'توليد تلقائي من درس'), h('button', { type: 'button', class: mode === 'manual' ? 'on' : '', onclick: () => { mode = 'manual'; if (!questions.length) questions.push({ prompt: '', options: ['', '', '', ''], correct: 0, points: 100 }); paintQs(); paintMode(); } }, 'إدخال الأسئلة يدوياً'));
      if (mode === 'auto') {
        autoBox.removeAttribute('hidden');
        manualBox.setAttribute('hidden', '');
      } else {
        manualBox.removeAttribute('hidden');
        autoBox.setAttribute('hidden', '');
      }
    }
    manualBox.setAttribute('hidden', '');
    paintMode();
    openModal({
      title: 'اختبار جديد', size: 'lg',
      content: h('div', { class: 'col' }, modeSeg,
        h('div', { class: 'field' }, h('label', null, 'عنوان الاختبار'), title),
        h('div', { class: 'grid g2' }, h('div', { class: 'field' }, h('label', null, 'النوع'), kind), h('div', { class: 'field' }, h('label', null, 'المدة بالدقائق (0 بلا حد)'), minutes)),
        autoBox, manualBox, err),
      actions: [
        { label: 'إلغاء', kind: 'ghost' },
        { label: 'نشر الاختبار', kind: 'primary', close: false, onClick: async ({ close }) => {
          err.textContent = '';
          if (title.value.trim().length < 2) {
            err.textContent = 'اكتب عنواناً للاختبار.';
            return false;
          }
          const base = { title: title.value.trim(), mode: kind.value, time_limit_seconds: Math.max(0, Math.round(Number(minutes.value) || 0) * 60) };
          let url = `/classrooms/${cid}/quizzes/generate`;
          let body;
          if (mode === 'auto') {
            body = { ...base, skill_id: skill.value, count: Math.min(20, Math.max(3, Number(count.value) || 8)) };
          } else {
            const built = [];
            for (let i = 0; i < questions.length; i += 1) {
              const q = questions[i];
              const filled = q.options.map((o, idx) => ({ text: o.trim(), idx })).filter((o) => o.text);
              const unique = new Set(filled.map((o) => o.text));
              const correct = filled.findIndex((o) => o.idx === q.correct);
              if (!q.prompt.trim() || filled.length < 2 || unique.size !== filled.length || correct < 0) {
                err.textContent = `راجع السؤال ${i + 1}: نص السؤال وخياران مختلفان على الأقل والإجابة الصحيحة غير فارغة.`;
                return false;
              }
              built.push({ prompt: q.prompt.trim(), options: filled.map((o) => o.text), correct_index: correct, points: q.points });
            }
            if (!built.length) {
              err.textContent = 'أضف سؤالاً واحداً على الأقل.';
              return false;
            }
            url = `/classrooms/${cid}/quizzes`;
            body = { ...base, questions: built };
          }
          try {
            await api.post(url, body);
            close();
            toast('تم نشر الاختبار.', 'success');
            await loadClasses();
            paintTab();
          } catch (ex) {
            if (ex.upsell) {
              close();
              handleError(ex);
            } else err.textContent = ex.message;
            return false;
          }
          return true;
        } },
      ],
    });
  }

  async function quizResults(q) {
    const holder = h('div', null, skeleton(3));
    openModal({ title: `نتائج: ${q.title}`, size: 'lg', content: holder });
    try {
      const res = await api.get(`/classrooms/quizzes/${q.quiz_id}/leaderboard`);
      mount(holder, res.rows.length ? res.rows.map((r) => h('div', { class: ['lb-row', `r${r.rank}`] }, h('span', { class: 'rk' }, String(r.rank)), avatarEl(r, 'sm'),
        h('div', { class: 'grow' }, h('b', null, r.full_name), h('div', { class: 'small muted' }, `${r.correct}/${r.total} صحيحة، ${Math.round(r.duration_seconds)} ثانية`)),
        h('b', null, `${r.score}`),
        h('button', { class: 'btn btn-ghost btn-sm', title: 'السماح بإعادة المحاولة', onclick: async (e) => {
          if (!(await confirmDialog(`السماح لـ ${r.full_name} بإعادة الاختبار؟ ستُحذف نتيجته الحالية.`, { confirmLabel: 'إعادة فتح', danger: true }))) return;
          try {
            await api.del(`/classrooms/quizzes/${q.quiz_id}/attempts/${r.user_id}`);
            e.target.closest('.lb-row').remove();
            toast('تمت إعادة فتح المحاولة.', 'success');
          } catch (err) {
            handleError(err);
          }
        } }, ico('refresh')))) : h('div', { class: 'empty' }, ico('trophy'), h('p', null, 'لم يسلّم أحد بعد.')));
    } catch (err) {
      mount(holder, errorPanel(err));
    }
  }

  async function quizzesTab(box) {
    mount(box, skeleton(3, true));
    try {
      if (!skills.length) skills = await skillList();
      const rows = await api.get(`/classrooms/${cid}/quizzes`);
      mount(box,
        h('div', { class: 'row end' }, h('button', { class: 'btn btn-primary', onclick: quizForm }, ico('plus'), 'اختبار جديد')),
        rows.length ? rows.map((q) => {
          const toggle = h('button', { class: 'btn btn-ghost btn-sm' }, q.is_open ? 'إغلاق' : 'فتح');
          toggle.addEventListener('click', async () => {
            try {
              await api.patch(`/classrooms/quizzes/${q.quiz_id}`, { is_open: !q.is_open });
              paintTab();
            } catch (err) {
              handleError(err);
            }
          });
          return h('div', { class: 'card lift' }, h('div', { class: 'row between' },
            h('div', null, h('h3', { style: { margin: 0 } }, q.title), h('div', { class: 'small muted' }, `${q.question_count} أسئلة${q.time_limit_seconds ? ` | ${Math.round(q.time_limit_seconds / 60)} دقيقة` : ''}`)),
            h('div', { class: 'row' }, h('span', { class: ['chip', q.mode === 'race' ? 'lime' : ''] }, q.mode === 'race' ? 'سباق سرعة' : 'اختبار'), h('span', { class: ['chip', q.is_open ? 'green' : ''] }, q.is_open ? 'مفتوح' : 'مغلق'), h('span', { class: 'chip' }, `${q.attempts} سلّموا`), toggle,
              h('button', { class: 'btn btn-primary btn-sm', onclick: () => quizResults(q) }, ico('trophy'), 'النتائج'))));
        }) : h('div', { class: 'empty card' }, ico('flag'), h('p', null, 'لا اختبارات بعد. أنشئ اختباراً أو سباقاً لطلابك.')));
    } catch (err) {
      mount(box, planError(err, () => quizzesTab(box)));
    }
  }

  async function boardTab(box) {
    mount(box, skeleton(4, true));
    try {
      const res = await api.get(`/classrooms/${cid}/leaderboard`);
      mount(box, h('div', { class: 'card' }, h('div', { class: 'card-title' }, h('h3', null, 'ترتيب الصف'), h('span', { class: 'chip' }, `${res.quiz_count} اختبار`)), leaderboardRows(res.rows, '')));
    } catch (err) {
      mount(box, planError(err, () => boardTab(box)));
    }
  }

  mount(bodyBox, skeleton(4, true));
  try {
    await loadClasses();
  } catch (err) {
    mount(bodyBox, errorPanel(err, () => ctx.reload()));
    return;
  }
  paintAll();
}
