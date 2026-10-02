import { h, ico, mount, clear, toast, openModal, fmtDate, avatarEl, skeleton } from '../dom.js';
import { api } from '../api.js';
import { store } from '../store.js';
import { errorPanel, handleError } from './shared.js';

const STATE = { open: ['مفتوح', 'green'], submitted: ['تم التسليم', 'lime'], graded: ['تم التصحيح', 'green'], overdue: ['متأخر', 'red'] };

export function leaderboardRows(rows, meId, scoreLabel = 'نقطة') {
  if (!rows.length) return h('div', { class: 'empty' }, ico('trophy'), h('p', null, 'لا نتائج بعد. كن أول المتصدرين.'));
  return h('div', null, rows.map((r) => h('div', { class: ['lb-row', `r${r.rank}`, r.user_id === meId ? 'me' : ''] },
    h('span', { class: 'rk' }, String(r.rank)), avatarEl(r, 'sm'),
    h('div', { class: 'grow' }, h('b', null, r.full_name), h('div', { class: 'small muted' }, r.total !== undefined ? `${r.correct}/${r.total} صحيحة، ${Math.round(r.duration_seconds)} ثانية` : `${r.quizzes_taken || 0} اختبار`)),
    h('b', { style: { color: 'var(--g-600)' } }, `${r.score} ${scoreLabel}`))));
}

export function runQuiz(quiz, onDone) {
  const overlay = h('div', { class: 'quiz-overlay' });
  const wrap = h('div', { class: 'quiz-wrap' });
  overlay.appendChild(wrap);
  document.body.appendChild(overlay);
  mount(wrap, skeleton(5, true));
  let data = null;
  let index = 0;
  const answers = {};
  let timerId = null;
  let endsAt = null;
  let startedAt = Date.now();
  let finished = false;

  const close = () => {
    clearInterval(timerId);
    overlay.remove();
    if (onDone) onDone();
  };

  async function finish() {
    if (finished) return;
    finished = true;
    clearInterval(timerId);
    mount(wrap, skeleton(4, true));
    try {
      const res = await api.post(`/classrooms/quizzes/${quiz.quiz_id}/submit`, { answers });
      const board = await api.get(`/classrooms/quizzes/${quiz.quiz_id}/leaderboard`);
      showResult(res, board.rows);
    } catch (err) {
      finished = false;
      handleError(err);
      close();
    }
  }

  function showResult(res, rows) {
    const reviewMap = {};
    res.review.forEach((r) => { reviewMap[r.id] = r; });
    mount(wrap,
      h('div', { class: 'card center', style: { padding: '28px' } },
        h('h1', null, `${res.score} نقطة`),
        h('p', { class: 'muted' }, `${res.correct} إجابة صحيحة من ${res.total}${res.bonus ? `، منها ${res.bonus} نقطة مكافأة سرعة` : ''}`),
        res.rank ? h('span', { class: 'chip lime' }, ico('trophy'), `المركز ${res.rank} من ${res.participants}`) : null),
      h('h3', { style: { margin: '20px 0 10px' } }, 'مراجعة الإجابات'),
      data.questions.map((q, i) => {
        const r = reviewMap[q.id];
        const ok = r && r.picked === r.correct_index;
        return h('div', { class: 'qb' },
          h('div', { class: 'row between' }, h('b', null, `${i + 1}. ${q.prompt}`), h('span', { class: ['chip', ok ? 'green' : 'red'] }, ok ? 'صحيحة' : 'خاطئة')),
          h('div', { class: 'small muted', style: { marginTop: '6px' } }, 'الإجابة الصحيحة: ', h('bdi', { class: 'm' }, q.options[r.correct_index]), r.picked !== null && r.picked !== undefined && !ok ? ['، إجابتك: ', h('bdi', null, q.options[r.picked])] : ''));
      }),
      h('h3', { style: { margin: '20px 0 10px' } }, 'لوحة المتصدرين'),
      leaderboardRows(rows, store.me.user_id),
      h('div', { class: 'row end', style: { marginTop: '16px' } }, h('button', { class: 'btn btn-primary btn-lg', onclick: close }, 'إغلاق')));
  }

  function paintQuestion() {
    const q = data.questions[index];
    const timer = h('span', { class: 'timer' }, ico('clock'), h('span', null, '00:00'));
    const timerText = timer.lastChild;
    const update = () => {
      const secs = endsAt ? Math.max(0, Math.round((endsAt - Date.now()) / 1000)) : Math.round((Date.now() - startedAt) / 1000);
      timerText.textContent = `${String(Math.floor(secs / 60)).padStart(2, '0')}:${String(secs % 60).padStart(2, '0')}`;
      if (endsAt && secs <= 15) timer.classList.add('low');
      if (endsAt && secs <= 0) finish();
    };
    clearInterval(timerId);
    update();
    timerId = setInterval(update, 500);
    const bar = h('i');
    const opts = h('div', { class: 'opts' });
    q.options.forEach((text, i) => {
      const b = h('button', { class: ['opt', answers[q.id] === i ? 'good' : ''], type: 'button' }, h('span', { class: 'k' }, String(i + 1)), h('span', { class: 'grow' }, text));
      b.addEventListener('click', () => {
        answers[q.id] = i;
        paintQuestion();
      });
      opts.appendChild(b);
    });
    const last = index === data.questions.length - 1;
    mount(wrap,
      h('div', { class: 'row between', style: { marginBottom: '14px' } }, h('div', null, h('h3', { style: { margin: 0 } }, data.title), h('span', { class: 'chip' }, data.mode === 'race' ? 'سباق سرعة' : 'اختبار')), timer),
      h('div', { class: 'bar', style: { marginBottom: '18px' } }, bar),
      h('div', { class: 'q-card' }, h('div', { class: 'small muted' }, `السؤال ${index + 1} من ${data.questions.length} - ${q.points} نقطة`), h('div', { class: 'q-text' }, q.prompt), opts),
      h('div', { class: 'row between', style: { marginTop: '16px' } },
        h('button', { class: 'btn btn-ghost', disabled: index === 0, onclick: () => { index -= 1; paintQuestion(); } }, 'السابق'),
        last
          ? h('button', { class: 'btn btn-primary btn-lg', onclick: finish }, 'إنهاء وتسليم')
          : h('button', { class: 'btn btn-primary', onclick: () => { index += 1; paintQuestion(); } }, 'التالي')));
    setTimeout(() => { bar.style.width = `${Math.round(((index + 1) / data.questions.length) * 100)}%`; }, 20);
  }

  (async () => {
    try {
      data = await api.post(`/classrooms/quizzes/${quiz.quiz_id}/start`, {});
    } catch (err) {
      handleError(err);
      close();
      return;
    }
    startedAt = Date.now();
    endsAt = data.seconds_left === null || data.seconds_left === undefined ? null : Date.now() + data.seconds_left * 1000;
    paintQuestion();
  })();
  return { close };
}

export async function classesView(ctx) {
  const me = store.me;
  const page = h('div', { class: 'page page-enter' });
  const body = h('div', { class: 'col' });
  ctx.root.appendChild(page);
  page.appendChild(h('div', { class: 'page-head' }, h('div', null, h('h1', null, 'صفوفي'), h('p', { class: 'muted' }, 'واجباتك واختباراتك ولوحة المتصدرين في مكان واحد.'))));
  page.appendChild(body);
  let classes = [];
  let tab = 'assignments';
  let current = null;

  async function join() {
    const code = h('input', { class: 'input', placeholder: 'مثال: JUTH26', dir: 'ltr', maxlength: '8', style: { textTransform: 'uppercase' } });
    const err = h('div', { class: 'err' });
    openModal({
      title: 'الانضمام إلى صف',
      content: h('div', { class: 'col' }, h('p', { class: 'muted' }, 'اطلب رمز الصف من معلمك.'), code, err),
      actions: [
        { label: 'إلغاء', kind: 'ghost' },
        { label: 'انضم', kind: 'primary', close: false, onClick: async ({ close }) => {
          err.textContent = '';
          if (code.value.trim().length < 6) {
            err.textContent = 'الرمز يتكون من 6 خانات.';
            return false;
          }
          try {
            await api.post('/classrooms/join', { join_code: code.value.trim() });
            close();
            toast('تم الانضمام إلى الصف.', 'success');
            const { loadMe } = await import('../store.js');
            await loadMe();
            ctx.reload();
          } catch (ex) {
            err.textContent = ex.message;
            return false;
          }
          return true;
        } },
      ],
    });
    setTimeout(() => code.focus(), 60);
  }

  function submitModal(a, refresh) {
    const text = h('textarea', { class: 'textarea', placeholder: 'اكتب إجابتك أو ملاحظاتك هنا', value: a.submission ? a.submission.text : '' });
    text.value = a.submission ? a.submission.text : '';
    const file = h('input', { type: 'file', class: 'input', accept: '.pdf,.png,.jpg,.jpeg,.doc,.docx,.txt,.xlsx,.pptx' });
    const err = h('div', { class: 'err' });
    openModal({
      title: a.title,
      content: h('div', { class: 'col' },
        a.description ? h('p', null, a.description) : null,
        h('div', { class: 'row small muted' }, a.due_at ? `التسليم قبل: ${fmtDate(a.due_at, true)}` : 'بلا موعد نهائي', ` | الدرجة العظمى: ${a.max_score}`),
        h('div', { class: 'field' }, h('label', null, 'إجابتك'), text),
        h('div', { class: 'field' }, h('label', null, 'إرفاق ملف (اختياري، حتى 5 ميغابايت)'), file),
        a.submission && a.submission.file_name ? h('div', { class: 'small muted' }, `الملف الحالي: ${a.submission.file_name}`) : null, err),
      actions: [
        { label: 'إلغاء', kind: 'ghost' },
        { label: a.submission ? 'تحديث التسليم' : 'تسليم', kind: 'primary', close: false, onClick: async ({ close }) => {
          err.textContent = '';
          const form = new FormData();
          form.append('text', text.value);
          if (file.files && file.files[0]) form.append('file', file.files[0]);
          try {
            await api.upload(`/classrooms/assignments/${a.assignment_id}/submit`, form);
            close();
            toast('تم تسليم الواجب.', 'success');
            refresh();
          } catch (ex) {
            err.textContent = ex.message;
            return false;
          }
          return true;
        } },
      ],
    });
  }

  async function paintAssignments(box) {
    mount(box, skeleton(4, true));
    try {
      const rows = await api.get('/classrooms/assignments');
      if (!rows.length) {
        mount(box, h('div', { class: 'empty' }, ico('file'), h('p', null, 'لا واجبات حالياً.')));
        return;
      }
      mount(box, rows.map((a) => {
        const [label, color] = STATE[a.state];
        return h('div', { class: 'card lift' },
          h('div', { class: 'row between' }, h('div', { class: 'row' }, h('h3', { style: { margin: 0 } }, a.title), a.kind === 'remediation' ? h('span', { class: 'chip amber' }, ico('target'), 'تقوية') : null), h('span', { class: ['chip', color] }, label)),
          h('div', { class: 'small muted', style: { margin: '4px 0 10px' } }, `${a.classroom_name}${a.due_at ? ` | التسليم: ${fmtDate(a.due_at, true)}` : ''}`),
          a.description ? h('p', null, a.description) : null,
          a.submission && a.submission.graded_at
            ? h('div', { class: 'banner' }, ico('star'), h('div', null, h('b', null, `${a.submission.score} / ${a.max_score}`), a.submission.feedback ? ` - ${a.submission.feedback}` : ''))
            : h('div', { class: 'row' }, h('button', { class: 'btn btn-primary btn-sm', onclick: () => submitModal(a, () => paintAssignments(box)) }, ico('upload'), a.submission ? 'تعديل التسليم' : 'تسليم الواجب'),
              a.submission && a.submission.late ? h('span', { class: 'chip amber' }, 'تم التسليم متأخراً') : null));
      }));
    } catch (err) {
      mount(box, errorPanel(err, () => paintAssignments(box)));
    }
  }

  async function paintQuizzes(box) {
    if (!current) {
      mount(box, h('div', { class: 'empty' }, ico('flag'), h('p', null, 'انضم إلى صف أولاً.')));
      return;
    }
    mount(box, skeleton(3, true));
    try {
      const rows = await api.get(`/classrooms/${current.classroom_id}/quizzes`);
      if (!rows.length) {
        mount(box, h('div', { class: 'empty' }, ico('flag'), h('p', null, 'لا اختبارات في هذا الصف بعد.')));
        return;
      }
      mount(box, rows.map((q) => {
        const done = q.mine && q.mine.submitted;
        const started = q.mine && !q.mine.submitted;
        let action;
        if (done) action = h('span', { class: 'chip green' }, `نتيجتك: ${q.mine.score} نقطة`);
        else if (!q.is_open && !started) action = h('span', { class: 'chip' }, 'مغلق');
        else action = h('button', { class: 'btn btn-primary btn-sm', onclick: () => runQuiz(q, () => paintQuizzes(box)) }, ico('bolt'), started ? 'تابع الاختبار' : 'ابدأ الآن');
        return h('div', { class: 'card lift' },
          h('div', { class: 'row between' }, h('div', null, h('h3', { style: { margin: 0 } }, q.title), h('div', { class: 'small muted' }, `${q.question_count} أسئلة${q.time_limit_seconds ? ` | ${Math.round(q.time_limit_seconds / 60)} دقيقة` : ''}`)),
            h('div', { class: 'row' }, h('span', { class: ['chip', q.mode === 'race' ? 'lime' : ''] }, q.mode === 'race' ? 'سباق سرعة' : 'اختبار'), action,
              h('button', { class: 'btn btn-ghost btn-sm', onclick: () => showBoard(q) }, ico('trophy'), 'المتصدرون'))));
      }));
    } catch (err) {
      mount(box, errorPanel(err, () => paintQuizzes(box)));
    }
  }

  async function showBoard(q) {
    const holder = h('div', null, skeleton(3));
    openModal({ title: `متصدرو: ${q.title}`, content: holder });
    try {
      const res = await api.get(`/classrooms/quizzes/${q.quiz_id}/leaderboard`);
      mount(holder, leaderboardRows(res.rows, me.user_id));
    } catch (err) {
      mount(holder, errorPanel(err));
    }
  }

  async function paintBoard(box) {
    if (!current) {
      mount(box, h('div', { class: 'empty' }, ico('trophy'), h('p', null, 'انضم إلى صف أولاً.')));
      return;
    }
    mount(box, skeleton(4, true));
    try {
      const res = await api.get(`/classrooms/${current.classroom_id}/leaderboard`);
      mount(box, h('div', { class: 'card' }, h('div', { class: 'card-title' }, h('h3', null, `ترتيب ${current.name}`), h('span', { class: 'chip' }, `${res.quiz_count} اختبار`)), leaderboardRows(res.rows, me.user_id)));
    } catch (err) {
      mount(box, errorPanel(err, () => paintBoard(box)));
    }
  }

  function paintTab() {
    const box = h('div', { class: 'col' });
    mount(content, box);
    if (tab === 'assignments') paintAssignments(box);
    else if (tab === 'quizzes') paintQuizzes(box);
    else paintBoard(box);
  }

  const content = h('div');
  try {
    classes = await api.get('/classrooms');
  } catch (err) {
    mount(body, errorPanel(err, () => ctx.reload()));
    return;
  }
  current = classes[0] || null;

  const joinBtn = h('button', { class: 'btn btn-primary', onclick: join }, ico('plus'), 'الانضمام إلى صف');
  if (!classes.length) {
    mount(body, h('div', { class: 'card empty' }, ico('users'), h('h3', null, 'لم تنضم إلى أي صف بعد'),
      h('p', { class: 'muted' }, 'انضم بواسطة رمز معلمك لتحصل على الواجبات والاختبارات، ويتفعّل لك برو مجاناً طوال انضمامك للصف.'), joinBtn));
    return;
  }
  const picker = h('select', { class: 'select', style: { width: 'auto', minWidth: '220px' }, 'aria-label': 'الصف' }, classes.map((c) => h('option', { value: c.classroom_id }, c.name)));
  picker.addEventListener('change', () => {
    current = classes.find((c) => c.classroom_id === picker.value);
    paintTab();
  });
  const tabs = h('div', { class: 'tabs' });
  const paintTabs = () => {
    clear(tabs);
    [['assignments', 'الواجبات'], ['quizzes', 'الاختبارات'], ['board', 'لوحة الصدارة']].forEach(([id, label]) => {
      tabs.appendChild(h('button', { class: tab === id ? 'on' : '', onclick: () => { tab = id; paintTabs(); paintTab(); } }, label));
    });
  };
  paintTabs();
  mount(body, h('div', { class: 'row between' }, picker, joinBtn), tabs, content);
  paintTab();
}
