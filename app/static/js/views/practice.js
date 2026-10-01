import { h, ico, mount, clear, toast, skeleton } from '../dom.js';
import { api } from '../api.js';
import { store, loadBoot, addWallet, patchBoot } from '../store.js';
import { errorPanel, upsellCard, skillNames, handleError } from './shared.js';
import { renderTreeStage } from '../tree.js';

const LEVELS = ['', 'سهل', 'متوسط', 'متقدم'];

export async function practiceView(ctx) {
  const uid = store.me.user_id;
  const page = h('div', { class: 'page page-enter', style: { maxWidth: '860px' } });
  const quotaEl = h('div', { class: 'quota' });
  const area = h('div', { class: 'col' });
  page.appendChild(h('div', { class: 'page-head' },
    h('div', null, h('h1', null, 'التدريب'), h('p', { class: 'muted' }, 'أسئلة تتكيّف مع مستواك وتتتبّع جذر أي تعثّر.')), quotaEl));
  page.appendChild(area);
  ctx.root.appendChild(page);

  let q = null;
  let locked = false;
  let answered = false;
  let optEls = [];
  let nextAction = null;
  let names = {};
  let scanStage = null;
  let scanToken = 0;
  let chain = [];

  function destroyScan() {
    scanToken += 1;
    if (scanStage) {
      scanStage.destroy();
      scanStage = null;
    }
  }
  ctx.onDestroy(destroyScan);

  const onKey = (e) => {
    const tag = (e.target && e.target.tagName) || '';
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;
    if (answered && e.key === 'Enter' && nextAction) {
      nextAction();
      return;
    }
    if (!answered && !locked && /^[1-4]$/.test(e.key) && optEls[Number(e.key) - 1]) optEls[Number(e.key) - 1].el.click();
  };
  document.addEventListener('keydown', onKey);
  ctx.onDestroy(() => document.removeEventListener('keydown', onKey));

  function paintQuota() {
    clear(quotaEl);
    const plan = store.boot && store.boot.plan;
    if (!plan || plan.limits.questions_per_day === null || plan.remaining.questions === null) {
      quotaEl.appendChild(h('span', { class: 'chip green' }, ico('bolt'), 'تدريب غير محدود'));
      return;
    }
    const lim = plan.limits.questions_per_day;
    const rem = plan.remaining.questions;
    const fill = h('i');
    quotaEl.appendChild(h('span', null, `المتبقي اليوم: ${rem} من ${lim}`));
    quotaEl.appendChild(h('div', { class: ['bar', rem <= 3 ? 'red' : ''] }, fill));
    setTimeout(() => { fill.style.width = `${Math.round(((lim - rem) / lim) * 100)}%`; }, 30);
  }

  function showLimit() {
    mount(area, upsellCard({
      title: 'انتهت أسئلة اليوم',
      text: 'استخدمت أسئلتك اليومية في الباقة الأساسية. يتجدد رصيدك عند منتصف الليل، أو تابع الآن بلا حد مع باقة برو واكشف جذر تعثّرك كاملاً.',
      cta: 'افتح التدريب غير المحدود',
      secondary: { label: 'العودة إلى الشجرة', href: '#/' },
    }));
  }

  async function loadQuestion() {
    destroyScan();
    locked = false;
    answered = false;
    nextAction = null;
    mount(area, skeleton(4, true));
    try {
      q = await api.get(`/students/${uid}/adaptive/question`);
    } catch (err) {
      if (err.upsell && err.upsell.type === 'quota') {
        showLimit();
        return;
      }
      mount(area, errorPanel(err, loadQuestion));
      return;
    }
    paintQuestion();
  }

  function paintQuestion() {
    optEls = [];
    const card = h('div', { class: 'q-card' });
    if (q.banner) card.appendChild(h('div', { class: 'banner' }, ico('info'), h('div', null, q.banner)));
    card.appendChild(h('div', { class: 'row' },
      h('span', { class: 'chip green' }, q.skill_name || names[q.skill] || ''),
      h('span', { class: 'chip' }, LEVELS[q.difficulty] || ''),
      q.remedial ? h('span', { class: 'chip amber' }, 'سؤال تثبيت') : null));
    card.appendChild(h('div', { class: 'q-text' }, q.question));
    const hint = h('div', { class: 'small muted', hidden: true, style: { marginBottom: '14px' } }, q.hint || '');
    if (q.hint) {
      card.appendChild(h('button', { class: 'btn btn-ghost btn-sm', style: { marginBottom: '12px' }, onclick: () => {
        const show = hint.hasAttribute('hidden');
        if (show) hint.removeAttribute('hidden');
        else hint.setAttribute('hidden', '');
        hint.hidden = !show;
      } }, ico('info'), 'تلميح'));
      card.appendChild(hint);
    }
    const opts = h('div', { class: 'opts' });
    if (q.type === 'input') {
      const input = h('input', { class: 'input', style: { fontSize: '1.2rem' }, dir: 'ltr', autocomplete: 'off', placeholder: 'اكتب إجابتك', 'aria-label': 'إجابتك' });
      const send = h('button', { class: 'btn btn-primary', type: 'button' }, 'تأكيد الإجابة');
      const minus = h('button', { class: 'btn btn-ghost', type: 'button', title: 'إشارة السالب', onclick: () => { input.value += '\u2212'; input.focus(); } }, '\u2212');
      const go = () => {
        if (!input.value.trim()) {
          toast('اكتب إجابتك أولاً.', 'error');
          return;
        }
        submit(input.value.trim(), null);
      };
      send.addEventListener('click', go);
      input.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
      card.appendChild(h('div', { class: 'row nowrap' }, h('div', { class: 'grow' }, input), minus, send));
      setTimeout(() => input.focus(), 60);
    } else {
      q.options.forEach((text, i) => {
        const el = h('button', { class: 'opt', type: 'button' }, h('span', { class: 'k' }, String(i + 1)), h('span', { class: 'grow' }, text));
        const entry = { el, text };
        optEls.push(entry);
        el.addEventListener('click', () => submit(text, entry));
        opts.appendChild(el);
      });
      card.appendChild(opts);
    }
    const feedback = h('div', { class: 'col' });
    mount(area, card, feedback);
    area.feedback = feedback;
    area.opts = opts;
  }

  async function submit(value, picked) {
    if (locked) return;
    locked = true;
    if (area.opts) area.opts.setAttribute('data-locked', '1');
    const analyzing = h('div', { class: 'analyzing', role: 'status', 'aria-live': 'polite' }, h('div', { class: 'spin' }), h('b', null, 'المعلم الذكي يقوم بتحليل إجابتك...'));
    if (area.feedback) area.feedback.appendChild(analyzing);
    let d;
    try {
      d = await api.post(`/students/${uid}/adaptive/answer`, { selected_answer: String(value), is_remedial: !!q.remedial });
      analyzing.remove();
    } catch (err) {
      analyzing.remove();
      locked = false;
      if (area.opts) area.opts.removeAttribute('data-locked');
      if (err.code === 'no_active_question') {
        toast(err.message, 'info');
        loadQuestion();
        return;
      }
      handleError(err);
      return;
    }
    answered = true;
    trackChain(d);
    store.treeStale = true;
    addWallet(d.coins_awarded, d.gems_awarded);
    if (store.boot && d.remaining_questions !== null && d.remaining_questions !== undefined) {
      patchBoot({ plan: { ...store.boot.plan, remaining: { ...store.boot.plan.remaining, questions: d.remaining_questions } } });
      paintQuota();
    }
    const good = optEls.find((o) => o.text === d.correct_answer);
    if (good) good.el.classList.add('good');
    if (picked && !d.is_correct) picked.el.classList.add('bad');
    paintFeedback(d);
  }

  function trackChain(d) {
    const moved = !!d.next_skill && d.next_skill !== q.skill;
    if (d.is_correct) {
      chain = [];
      return;
    }
    if (!chain.length || chain[chain.length - 1] !== q.skill) chain = [q.skill];
    if (moved && chain[chain.length - 1] !== d.next_skill) chain.push(d.next_skill);
  }

  function scanPlan(treeData, d) {
    const order = [];
    for (const u of treeData.units) for (const l of u.lessons) if (l.skill) order.push(l.skill);
    const hasGaps = !!(d.new_gaps && d.new_gaps.length);
    const path = chain.filter((id, i) => order.includes(id) && chain.indexOf(id) === i);
    if (hasGaps) for (const id of d.new_gaps) if (order.includes(id) && !path.includes(id)) path.push(id);
    if (path.length < 2 && d.gap_locked) {
      const from = order.indexOf(q.skill);
      if (from < 1) return null;
      return { path: order.slice(Math.max(0, from - 3), from + 1).reverse(), locked: true, found: false };
    }
    if (path.length < 2) return null;
    return { path, locked: !!d.gap_locked && !hasGaps, found: hasGaps };
  }

  function paintScan(box, d) {
    if (d.is_correct) return;
    const moves = (d.new_gaps && d.new_gaps.length) || d.gap_locked || (d.next_skill && d.next_skill !== q.skill);
    if (!moves) return;
    const caption = h('div', { class: 'scan-cap', 'aria-live': 'polite' }, 'نتتبّع مصدر الخطأ في شجرة المنهج…');
    const holder = h('div', { class: 'scan-stage' });
    const card = h('div', { class: 'card scan-card' }, h('div', { class: 'row' }, ico('target'), h('b', null, 'مسح الجذر')), caption, holder);
    box.appendChild(card);
    const token = scanToken;
    api.get(`/students/${uid}/adaptive/tree`).then((treeData) => {
      if (token !== scanToken) return;
      const plan = scanPlan(treeData, d);
      if (!plan) {
        card.remove();
        return;
      }
      scanStage = renderTreeStage(holder, treeData, { embedded: true, bare: true, interactive: false, compact: true });
      setTimeout(() => {
        if (token !== scanToken || !scanStage) return;
        scanStage.scan(plan.path, {
          lockedTail: plan.locked,
          onStep: (i, lesson, last) => {
            if (i === 0) caption.textContent = `الخطأ ظهر في «${lesson.title}»، نرجع خطوة خطوة…`;
            else if (!last) caption.textContent = `نفحص «${lesson.title}»…`;
            else if (plan.locked) caption.textContent = 'وصلنا إلى جذر مخفي في الباقة الأساسية. افتح باقة برو لتعرف الدرس بالضبط.';
            else if (plan.found) caption.textContent = `وجدنا الجذر: «${lesson.title}». سنعالجه الآن.`;
            else caption.textContent = `ننزل إلى «${lesson.title}» لنفحص إن كان هو الأساس.`;
          },
        }).then(() => {
          if (plan.locked && token === scanToken) card.appendChild(h('div', { class: 'row end' }, h('a', { class: 'btn btn-primary btn-sm', href: '#/plans' }, 'اكشف الجذر')));
        });
      }, 450);
    }).catch(() => card.remove());
  }

  function paintFeedback(d) {
    const box = area.feedback;
    const verdict = d.is_correct
      ? h('div', { class: 'verdict good' },
        h('svg', { class: 'check-draw', viewBox: '0 0 34 34' }, h('path', { d: 'M7 18l7 7 13-14', fill: 'none', stroke: 'currentColor', 'stroke-width': '4', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })),
        h('div', { class: 'grow' }, 'إجابة صحيحة، أحسنت.'),
        d.coins_awarded ? h('span', { class: 'chip lime' }, ico('coin'), `+${d.coins_awarded}`) : null,
        d.gems_awarded ? h('span', { class: 'chip lime' }, ico('gem'), `+${d.gems_awarded}`) : null)
      : h('div', { class: 'verdict bad' }, ico('x'), h('div', { class: 'grow' }, 'إجابة غير صحيحة. الصواب: ', h('bdi', { class: 'm' }, d.correct_answer)));
    box.appendChild(verdict);

    if (!d.is_correct && d.mistake_card) {
      const card = d.mistake_card;
      const content = h('div', { class: 'explain', hidden: true },
        h('h4', null, card.title),
        card.why ? h('div', { class: 'sec' }, h('b', null, 'سبب الخطأ المحتمل'), card.why) : null,
        card.rule ? h('div', { class: 'sec' }, h('b', null, 'القاعدة'), card.rule) : null,
        card.example ? h('div', { class: 'sec' }, h('b', null, 'مثال'), card.example) : null,
        card.solution ? h('div', { class: 'sec' }, h('b', null, 'الحل'), card.solution) : null);
      const toggle = h('button', { class: 'btn btn-ghost', type: 'button' }, ico('book'), 'اعرض الشرح');
      toggle.addEventListener('click', () => {
        const hidden = content.hasAttribute('hidden');
        if (hidden) {
          content.removeAttribute('hidden');
          content.hidden = false;
        } else {
          content.setAttribute('hidden', '');
          content.hidden = true;
        }
        clear(toggle);
        toggle.appendChild(ico('book'));
        toggle.appendChild(document.createTextNode(hidden ? 'أخفِ الشرح' : 'اعرض الشرح'));
      });
      box.appendChild(h('div', null, toggle));
      box.appendChild(content);
    }
    paintScan(box, d);
    if (d.breadcrumb) box.appendChild(h('div', { class: 'banner' }, ico('flag'), h('div', null, d.breadcrumb)));
    if (d.new_gaps && d.new_gaps.length) {
      const labels = d.new_gaps.map((id) => names[id] || id).join('، ');
      box.appendChild(h('div', { class: 'gap-banner' }, ico('target'), h('div', null, h('b', null, 'رصدنا جذر التعثّر: '), labels, '. سنعالجه الآن قبل العودة إلى الدرس.')));
    }
    if (d.gap_locked) {
      box.appendChild(upsellCard({
        title: 'رصدنا فجوة جذرية في مسارك',
        text: 'نعرف الآن أن التعثّر يبدأ في درس سابق. افتح سلسلة الجذر كاملة وتقرير الفجوة مع باقة برو.',
        cta: 'اكشف الجذر',
      }));
    }
    if (d.round_over) {
      box.appendChild(h('div', { class: 'card center' }, h('h3', null, 'أنهيت الجولة'), h('p', { class: 'muted' }, 'عمل رائع. ابدأ جولة جديدة لتواصل تعزيز شجرتك.'),
        h('div', { class: 'row', style: { justifyContent: 'center' } },
          h('button', { class: 'btn btn-primary', onclick: newRound }, ico('refresh'), 'جولة جديدة'),
          h('a', { class: 'btn btn-ghost', href: '#/' }, 'العودة إلى الشجرة'))));
      nextAction = newRound;
      return;
    }
    const next = h('button', { class: 'btn btn-primary btn-lg', type: 'button' }, 'السؤال التالي', ico('chevl'));
    next.addEventListener('click', loadQuestion);
    nextAction = loadQuestion;
    box.appendChild(h('div', { class: 'row end' }, next));
    setTimeout(() => next.focus(), 80);
  }

  async function newRound() {
    chain = [];
    mount(area, skeleton(3, true));
    try {
      await api.post(`/students/${uid}/adaptive/round`, {});
    } catch (err) {
      mount(area, errorPanel(err, newRound));
      return;
    }
    loadQuestion();
  }

  try {
    names = await skillNames();
  } catch (e) {
    names = {};
  }
  loadBoot().then(paintQuota).catch(() => null);
  paintQuota();
  await loadQuestion();
}
