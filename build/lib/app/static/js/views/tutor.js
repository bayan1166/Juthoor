import { h, ico, mount, clear, toast } from '../dom.js';
import { api } from '../api.js';
import { store, loadBoot, patchBoot } from '../store.js';
import { leafAvatarSvg } from '../icons.js';
import { skillList, upsellCard, handleError } from './shared.js';

const SOURCES = {
  solver: ['check', 'حل محسوب آلياً ومتحقَّق منه'],
  llm_rag: ['book', 'نموذج لغوي مدعوم بمقاطع من المنهج'],
  llm: ['spark', 'نموذج لغوي'],
  guardrail: ['shield', 'خارج المنهج: لم يُرسل لأي نموذج'],
  tutor: ['book', 'معلم المنهج المحلي'],
};

const JUDGE_QUICK = [
  ['جرّب: 1/2 + 1/3', '1/2 + 1/3'],
  ['جرّب سؤالاً خارج المنهج', 'ما هي عاصمة فرنسا'],
];

const QUICK = [
  ['اشرح لي الدرس', 'اشرح لي هذا الدرس'],
  ['حلّ مسألة معي', 'اعطني مسألة لأحلها'],
  ['لم أفهم', 'مش فاهم'],
  ['اختبرني', 'اختبرني بتمرين'],
];

export async function tutorView(ctx) {
  const uid = store.me.user_id;
  const page = h('div', { class: 'page page-enter', style: { maxWidth: '900px' } });
  const quotaEl = h('span', { class: 'chip green' });
  const select = h('select', { class: 'select', style: { width: 'auto', minWidth: '240px' }, 'aria-label': 'الدرس' });
  const msgs = h('div', { class: 'msgs' });
  const input = h('textarea', { rows: '1', placeholder: 'اكتب سؤالك أو مسألتك هنا...', 'aria-label': 'رسالتك' });
  const sendBtn = h('button', { class: 'send', type: 'button', 'aria-label': 'إرسال' }, ico('send'));
  const composer = h('div', { class: 'composer' }, input, sendBtn);
  const chipsRow = h('div', { class: 'chips-row' });
  const bottom = h('div', null, chipsRow, composer);
  const shell = h('div', { class: 'tutor-shell' },
    h('div', { class: 'chat-head' }, h('span', { class: 'avatar', html: leafAvatarSvg() }), h('div', { class: 'grow' }, h('b', null, 'المعلم الذكي'), h('div', { class: 'small muted' }, 'يشرح ويحلّ خطوة بخطوة ويتتبّع جذر التعثّر')), select, quotaEl),
    msgs, bottom);
  page.appendChild(shell);
  ctx.root.appendChild(page);

  let sessionId = null;
  let skill = '';
  let busy = false;
  let blocked = false;

  function paintQuota() {
    const plan = store.boot && store.boot.plan;
    const rem = plan && plan.remaining.tutor;
    quotaEl.textContent = rem === null || rem === undefined ? 'رسائل غير محدودة' : `المتبقي اليوم: ${rem}`;
    quotaEl.setAttribute('class', rem === 0 ? 'chip red' : 'chip green');
  }

  function scrollDown() {
    msgs.scrollTop = msgs.scrollHeight;
  }

  function bubble(role, text, source) {
    const mine = role === 'student';
    const body = h('div', { class: ['bubble', mine ? 'mine' : 'theirs'] }, text);
    if (!mine && source && SOURCES[source]) body.appendChild(h('div', { class: 'src-badge', 'data-source': source }, ico(SOURCES[source][0]), SOURCES[source][1]));
    const row = h('div', { class: ['row-msg', mine ? 'mine' : ''] });
    if (mine) {
      const av = h('span', { class: 'avatar sm' });
      if (store.boot && store.boot.avatar_svg) av.innerHTML = store.boot.avatar_svg;
      row.appendChild(av);
    } else {
      row.appendChild(h('span', { class: 'avatar sm', html: leafAvatarSvg() }));
    }
    row.appendChild(body);
    msgs.appendChild(row);
    scrollDown();
    return row;
  }

  function note(text, action) {
    msgs.appendChild(h('div', { class: 'banner', style: { alignSelf: 'center', maxWidth: '90%' } }, ico('target'), h('div', null, text),
      action ? h('a', { class: 'btn btn-sm btn-primary', href: '#/practice' }, 'اذهب للتدريب') : null));
    scrollDown();
  }

  function typing() {
    const row = h('div', { class: 'row-msg' }, h('span', { class: 'avatar sm', html: leafAvatarSvg() }), h('div', { class: 'bubble theirs' }, h('span', { class: 'typing' }, h('i'), h('i'), h('i')), h('span', { class: 'small muted', style: { marginInlineStart: '8px' } }, 'المعلم الذكي يقوم بتحليل إجابتك...')));
    msgs.appendChild(row);
    scrollDown();
    return row;
  }

  function showBlocked() {
    blocked = true;
    mount(bottom, h('div', { style: { padding: '14px' } }, upsellCard({
      title: 'انتهت رسائل اليوم',
      text: 'الباقة الأساسية تتيح 5 رسائل يومياً مع المعلم الذكي. تابع الآن بلا حد مع باقة برو.',
      cta: 'افتح المعلم الذكي بلا حد',
    })));
  }

  async function openSession() {
    clear(msgs);
    const key = `juthoor.chat.${uid}.${skill}`;
    let saved = null;
    try {
      saved = sessionStorage.getItem(key);
    } catch (e) {
      saved = null;
    }
    if (saved) {
      try {
        const rows = await api.get(`/students/${uid}/chat/sessions/${saved}/messages`);
        sessionId = saved;
        rows.forEach((m) => bubble(m.role === 'student' ? 'student' : 'tutor', m.content));
        return;
      } catch (e) {
        sessionId = null;
      }
    }
    try {
      const res = await api.post(`/students/${uid}/chat/start`, { skill_context: skill });
      sessionId = res.session_id;
      try {
        sessionStorage.setItem(key, sessionId);
      } catch (e) {
        sessionId = res.session_id;
      }
      bubble('tutor', res.opening_message);
    } catch (err) {
      msgs.appendChild(h('div', { class: 'empty' }, ico('alert'), h('p', null, err.message), h('button', { class: 'btn btn-primary', onclick: openSession }, 'إعادة المحاولة')));
    }
  }

  async function send(text) {
    const value = (text || '').trim();
    if (!value || busy || blocked || !sessionId) return;
    busy = true;
    input.value = '';
    input.style.height = 'auto';
    bubble('student', value);
    const wait = typing();
    try {
      const res = await api.post(`/students/${uid}/chat/message`, { session_id: sessionId, message: value });
      wait.remove();
      bubble('tutor', res.reply, res.source);
      if (res.drill_down_triggered) note(`أضفنا لك أسئلة تأسيسية في صفحة التدريب${res.breadcrumb ? `: ${res.breadcrumb}` : '.'}`, true);
      if (store.boot && res.remaining_today !== null && res.remaining_today !== undefined) {
        patchBoot({ plan: { ...store.boot.plan, remaining: { ...store.boot.plan.remaining, tutor: res.remaining_today } } });
        paintQuota();
      }
      store.treeStale = true;
    } catch (err) {
      wait.remove();
      if (err.upsell && err.upsell.type === 'quota') {
        showBlocked();
      } else {
        toast(err.message, 'error');
      }
    } finally {
      busy = false;
    }
  }

  (store.health && store.health.judge ? [...QUICK, ...JUDGE_QUICK] : QUICK).forEach(([label, text]) => chipsRow.appendChild(h('button', { type: 'button', onclick: () => send(text) }, label)));
  sendBtn.addEventListener('click', () => send(input.value));
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send(input.value);
    }
  });
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = `${Math.min(140, input.scrollHeight)}px`;
  });

  let list = [];
  try {
    list = await skillList();
  } catch (err) {
    mount(page, h('div', { class: 'empty' }, ico('alert'), h('p', null, err.message)));
    return;
  }
  list.forEach((s) => select.appendChild(h('option', { value: s.skill_id }, s.name_ar)));
  try {
    await loadBoot();
  } catch (e) {
    toast('تعذّر تحميل بياناتك.', 'error');
  }
  skill = (store.boot && store.boot.state.current_skill) || (list[0] && list[0].skill_id) || '';
  select.value = skill;
  select.addEventListener('change', async () => {
    skill = select.value;
    await openSession();
  });
  paintQuota();
  const plan = store.boot && store.boot.plan;
  if (plan && plan.remaining.tutor === 0) showBlocked();
  await openSession();
  if (!blocked) setTimeout(() => input.focus(), 80);
}
