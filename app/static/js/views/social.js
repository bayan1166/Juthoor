import { h, ico, mount, clear, toast, avatarEl, fmtTime, dayLabel, openModal, confirmDialog, copyText } from '../dom.js';
import { api } from '../api.js';
import { store, refreshSummary } from '../store.js';
import { handleError, errorPanel } from './shared.js';

export async function communityView(ctx) {
  const me = store.me;
  const page = h('div', { class: 'page page-enter wide' });
  const shell = h('div', { class: 'chat-shell' });
  const side = h('div', { class: 'chat-side' });
  const main = h('div', { class: 'chat-main' });
  shell.appendChild(side);
  shell.appendChild(main);
  page.appendChild(shell);
  ctx.root.appendChild(page);

  let convs = [];
  let requests = [];
  let active = null;
  let byId = new Map();
  let lastAt = null;
  let lastDay = '';
  let pollTimer = null;
  let listTimer = null;
  let polling = false;
  let tempCount = 0;
  const msgsEl = h('div', { class: 'msgs' });
  const pill = h('button', { class: 'new-pill', hidden: true }, 'رسائل جديدة');
  const convListEl = h('div', { class: 'conv-list' });
  const sideTop = h('div', { class: 'top' });
  const requestsEl = h('div');
  side.appendChild(sideTop);
  side.appendChild(requestsEl);
  side.appendChild(convListEl);

  ctx.onDestroy(() => {
    clearInterval(pollTimer);
    clearInterval(listTimer);
  });

  function nearBottom() {
    return msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight < 140;
  }

  function toBottom() {
    msgsEl.scrollTop = msgsEl.scrollHeight;
    pill.setAttribute('hidden', '');
    pill.hidden = true;
  }

  function paintTop() {
    clear(sideTop);
    sideTop.appendChild(h('div', { class: 'row between' },
      h('h3', { style: { margin: 0 } }, 'المحادثات'),
      h('div', { class: 'row' },
        h('button', { class: 'btn btn-ghost btn-sm', type: 'button', onclick: openBlocked, title: 'المحظورون' }, ico('shield'), 'المحظورون'),
        h('button', { class: 'btn btn-primary btn-sm', onclick: openAdd }, ico('plus'), 'إضافة صديق'))));
    sideTop.appendChild(h('div', { class: 'row small muted', style: { marginTop: '10px' } },
      h('span', null, 'معرّفك: '), h('b', { class: 'ltr' }, `#${me.handle || ''}`),
      h('button', { class: 'icon-btn', style: { width: '30px', height: '30px' }, 'aria-label': 'نسخ المعرّف', onclick: async () => { toast((await copyText(me.handle || '')) ? 'تم نسخ المعرّف.' : 'تعذّر النسخ.', 'info'); } }, ico('copy'))));
  }

  function paintRequests() {
    clear(requestsEl);
    if (!requests.length) return;
    const box = h('div', { style: { padding: '12px 16px', background: 'var(--g-50)', borderBottom: '1px solid var(--line)' } },
      h('div', { class: 'small', style: { fontWeight: 800, marginBottom: '8px' } }, `طلبات الصداقة (${requests.length})`));
    for (const r of requests) {
      box.appendChild(h('div', { class: 'row nowrap', style: { marginBottom: '8px' } },
        avatarEl(r.friend, 'sm'),
        h('div', { class: 'grow' }, h('div', { style: { fontWeight: 800 } }, r.friend.full_name), h('div', { class: 'small muted ltr' }, `#${r.friend.handle || ''}`)),
        h('button', { class: 'btn btn-primary btn-sm', onclick: () => answer(r, true) }, 'قبول'),
        h('button', { class: 'btn btn-ghost btn-sm', 'aria-label': 'رفض', onclick: () => answer(r, false) }, ico('x'))));
    }
    requestsEl.appendChild(box);
  }

  async function answer(r, accept) {
    try {
      await api.post(`/community/${accept ? 'accept' : 'reject'}/${r.friendship_id}`, {});
      toast(accept ? 'أصبحتم أصدقاء.' : 'تم رفض الطلب.', accept ? 'success' : 'info');
      await loadLists();
      refreshSummary();
    } catch (err) {
      handleError(err);
    }
  }

  function preview(c) {
    if (!c.last_message) return 'ابدأ المحادثة';
    const mine = c.last_message.sender_id === me.user_id;
    return `${mine ? 'أنت: ' : ''}${c.last_message.body}`;
  }

  function paintConvs() {
    clear(convListEl);
    if (!convs.length) {
      convListEl.appendChild(h('div', { class: 'empty' }, ico('users'), h('b', null, 'لا أصدقاء بعد'), h('p', { class: 'small' }, 'أضف صديقاً باستخدام معرّفه أو بريده الإلكتروني لتبدأ المحادثة.'),
        h('button', { class: 'btn btn-primary', onclick: openAdd }, ico('plus'), 'إضافة صديق')));
      return;
    }
    for (const c of convs) {
      const isOn = active && active.friend.user_id === c.friend.user_id;
      const row = h('div', { class: ['conv', isOn ? 'on' : ''], role: 'button', tabindex: '0' },
        avatarEl(c.friend),
        h('div', { class: 'meta' }, h('div', { class: 'name' }, c.friend.full_name), h('div', { class: 'last' }, preview(c))),
        h('div', { class: 'col', style: { alignItems: 'flex-end', gap: '4px' } },
          c.last_message ? h('span', { class: 'time' }, dayLabel(c.last_message.created_at) === 'اليوم' ? fmtTime(c.last_message.created_at) : dayLabel(c.last_message.created_at)) : null,
          c.unread ? h('span', { class: 'badge' }, String(c.unread)) : null));
      row.addEventListener('click', () => openThread(c));
      row.addEventListener('keydown', (e) => { if (e.key === 'Enter') openThread(c); });
      convListEl.appendChild(row);
    }
  }

  async function loadLists() {
    try {
      const [c, r] = await Promise.all([api.get('/community/conversations'), api.get('/community/requests')]);
      convs = c;
      requests = r;
      if (active) {
        const fresh = convs.find((x) => x.friend.user_id === active.friend.user_id);
        if (fresh) active = fresh;
      }
      paintRequests();
      paintConvs();
    } catch (err) {
      if (!convs.length) mount(convListEl, errorPanel(err, loadLists));
    }
  }

  function tick(m) {
    if (m.sender_id !== me.user_id) return null;
    return h('span', { class: 'ico', title: m.read_at ? 'تمت القراءة' : 'تم الإرسال', style: { color: m.read_at ? '#C6F36B' : 'inherit' } }, ico(m._state === 'sending' ? 'clock' : m.read_at ? 'checks' : 'check'));
  }

  function bubbleEl(m) {
    const mine = m.sender_id === me.user_id;
    const meta = h('div', { class: 'meta' }, h('span', null, fmtTime(m.created_at)), tick(m));
    const el = h('div', { class: ['bubble', mine ? 'mine' : 'theirs', m._state === 'sending' ? 'sending' : '', m._state === 'failed' ? 'failed' : ''] }, h('div', null, m.body), meta);
    if (!mine && m.message_id && !m._state) {
      meta.appendChild(h('button', { class: 'bubble-flag', type: 'button', 'aria-label': 'إبلاغ عن الرسالة', title: 'إبلاغ عن الرسالة', onclick: () => reportDialog(m) }, ico('flag')));
    }
    if (m._state === 'failed') {
      meta.appendChild(h('button', { class: 'btn btn-sm', style: { minHeight: '22px', padding: '0 8px' }, onclick: () => retry(m) }, 'إعادة المحاولة'));
    }
    return el;
  }

  function addToThread(m) {
    const first = msgsEl.firstChild;
    if (first && first.classList && first.classList.contains('empty')) msgsEl.removeChild(first);
    const label = dayLabel(m.created_at);
    if (label && label !== lastDay) {
      msgsEl.appendChild(h('div', { class: 'day' }, label));
      lastDay = label;
    }
    const el = bubbleEl(m);
    msgsEl.appendChild(el);
    byId.set(m.message_id, { data: m, el });
  }

  function refreshBubble(id, data) {
    const entry = byId.get(id);
    if (!entry) return;
    const fresh = bubbleEl(data);
    entry.el.replaceWith(fresh);
    byId.delete(id);
    byId.set(data.message_id, { data, el: fresh });
  }

  function earliestUnreadMine() {
    let best = null;
    for (const { data } of byId.values()) {
      if (data.sender_id === me.user_id && !data.read_at && data._state !== 'sending' && data._state !== 'failed') {
        if (!best || data.created_at < best) best = data.created_at;
      }
    }
    return best;
  }

  async function markRead() {
    if (!active) return;
    try {
      await api.post(`/community/messages/${active.friend.user_id}/read`, {});
      active.unread = 0;
      paintConvs();
      refreshSummary();
    } catch (e) {
      return;
    }
  }

  function merge(rows) {
    let incoming = false;
    const stick = nearBottom();
    let added = false;
    for (const m of rows) {
      const known = byId.get(m.message_id);
      if (known) {
        if (known.data.read_at !== m.read_at) refreshBubble(m.message_id, m);
        continue;
      }
      const dupTemp = Array.from(byId.entries()).find(([id, v]) => String(id).startsWith('tmp-') && v.data._state === 'sending' && v.data.body === m.body && m.sender_id === me.user_id);
      if (dupTemp) {
        refreshBubble(dupTemp[0], m);
      } else {
        addToThread(m);
        added = true;
        if (m.sender_id !== me.user_id) incoming = true;
      }
      if (!lastAt || m.created_at > lastAt) lastAt = m.created_at;
    }
    if (added) {
      if (stick || rows.every((m) => m.sender_id === me.user_id)) toBottom();
      else {
        pill.removeAttribute('hidden');
        pill.hidden = false;
      }
    }
    if (incoming && !document.hidden) markRead();
  }

  async function poll() {
    if (!active || polling || document.hidden) return;
    polling = true;
    const from = earliestUnreadMine() || lastAt;
    const id = active.friend.user_id;
    try {
      const rows = await api.get(`/community/messages/${id}`, { params: from ? { after: from } : {} });
      if (active && active.friend.user_id === id) merge(rows);
    } catch (e) {
      polling = false;
      return;
    }
    polling = false;
  }

  async function send(input, text) {
    const body = (text || '').trim();
    if (!body || !active) return;
    input.value = '';
    input.style.height = 'auto';
    tempCount += 1;
    const temp = { message_id: `tmp-${tempCount}`, sender_id: me.user_id, recipient_id: active.friend.user_id, body, created_at: new Date().toISOString(), read_at: null, _state: 'sending' };
    addToThread(temp);
    toBottom();
    await transmit(temp);
  }

  async function transmit(temp) {
    const to = active.friend.user_id;
    try {
      const real = await api.post(`/community/messages/${to}`, { body: temp.body });
      if (active && active.friend.user_id === to) {
        refreshBubble(temp.message_id, real);
        if (!lastAt || real.created_at > lastAt) lastAt = real.created_at;
      }
      loadLists();
    } catch (err) {
      refreshBubble(temp.message_id, { ...temp, _state: 'failed' });
      toast(err.message, 'error');
    }
  }

  async function retry(m) {
    const next = { ...m, _state: 'sending' };
    refreshBubble(m.message_id, next);
    await transmit(next);
  }

  function paintThread() {
    byId = new Map();
    lastAt = null;
    lastDay = '';
    clear(msgsEl);
    const c = active;
    const input = h('textarea', { rows: '1', placeholder: 'اكتب رسالة...', 'aria-label': 'رسالتك' });
    const sendBtn = h('button', { class: 'send', type: 'button', 'aria-label': 'إرسال' }, ico('send'));
    sendBtn.addEventListener('click', () => send(input, input.value));
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        send(input, input.value);
      }
    });
    input.addEventListener('input', () => {
      input.style.height = 'auto';
      input.style.height = `${Math.min(140, input.scrollHeight)}px`;
    });
    pill.addEventListener('click', toBottom);
    mount(main,
      h('div', { class: 'chat-head' },
        h('button', { class: 'icon-btn', 'aria-label': 'رجوع', onclick: closeThread }, ico('chevr')),
        avatarEl(c.friend),
        h('div', { class: 'grow' }, h('b', null, c.friend.full_name), h('div', { class: 'small muted ltr' }, `#${c.friend.handle || ''}`)),
        h('button', { class: 'icon-btn', 'aria-label': 'إبلاغ', title: 'إبلاغ', onclick: () => reportDialog(null) }, ico('flag')),
        h('button', { class: 'icon-btn', 'aria-label': 'حظر', title: 'حظر', onclick: blockActive }, ico('shield')),
        h('button', { class: 'icon-btn', 'aria-label': 'حذف الصديق', title: 'حذف الصديق', onclick: removeFriend }, ico('trash'))),
      h('div', { style: { position: 'relative', flex: '1', minHeight: 0, display: 'flex', flexDirection: 'column' } }, msgsEl, pill),
      h('div', { class: 'safety-note small muted' }, ico('shield'), 'لا تشارك أرقام هاتف أو روابط أو معلومات شخصية. يمكنك حظر أي مستخدم أو الإبلاغ عنه في أي وقت.'),
      h('div', { class: 'composer' }, input, sendBtn));
    setTimeout(() => input.focus(), 60);
  }

  async function openThread(c) {
    active = c;
    shell.classList.add('thread-open');
    paintConvs();
    paintThread();
    msgsEl.appendChild(h('div', { class: 'empty' }, h('div', { class: 'spin' })));
    try {
      const rows = await api.get(`/community/messages/${c.friend.user_id}`);
      if (!active || active.friend.user_id !== c.friend.user_id) return;
      clear(msgsEl);
      if (!rows.length) msgsEl.appendChild(h('div', { class: 'empty' }, ico('chat'), h('p', null, 'لا رسائل بعد. ابدأ المحادثة بتحية.')));
      else {
        clear(msgsEl);
        merge(rows);
        toBottom();
      }
    } catch (err) {
      mount(msgsEl, errorPanel(err, () => openThread(c)));
      return;
    }
    if (ctx.destroyed) return;
    if (c.unread) markRead();
    clearInterval(pollTimer);
    pollTimer = setInterval(poll, 2500);
  }

  function closeThread() {
    active = null;
    clearInterval(pollTimer);
    shell.classList.remove('thread-open');
    paintEmptyMain();
    paintConvs();
  }

  async function removeFriend() {
    if (!active) return;
    const ok = await confirmDialog(`هل تريد حذف ${active.friend.full_name} من أصدقائك؟`, { title: 'حذف صديق', confirmLabel: 'حذف', danger: true });
    if (!ok) return;
    try {
      await api.del(`/community/friend/${active.friendship_id}`);
      closeThread();
      await loadLists();
      toast('تم حذف الصديق.', 'info');
    } catch (err) {
      handleError(err);
    }
  }

  const REPORT_REASONS = [['bullying', 'تنمّر أو إساءة'], ['inappropriate', 'محتوى غير لائق'], ['contact_info', 'طلب معلومات شخصية أو أرقام'], ['spam', 'إزعاج أو رسائل متكررة'], ['other', 'سبب آخر']];

  async function afterBlock() {
    closeThread();
    await loadLists();
  }

  async function blockActive() {
    if (!active) return;
    const name = active.friend.full_name;
    const ok = await confirmDialog(`هل تريد حظر ${name}؟ لن يستطيع مراسلتك أو العثور عليك، ويمكنك إلغاء الحظر لاحقاً من قائمة المحظورين.`, { title: 'حظر مستخدم', confirmLabel: 'حظر', danger: true });
    if (!ok) return;
    try {
      await api.post(`/community/block/${active.friend.user_id}`, {});
      toast(`تم حظر ${name}.`, 'success');
      await afterBlock();
    } catch (err) {
      handleError(err);
    }
  }

  function reportDialog(message) {
    if (!active) return;
    const friend = active.friend;
    const reason = h('select', { class: 'select', 'aria-label': 'سبب البلاغ' }, REPORT_REASONS.map(([v, l]) => h('option', { value: v }, l)));
    const details = h('textarea', { class: 'textarea', maxlength: '1000', placeholder: 'اشرح ما حدث (اختياري)' });
    const alsoBlock = h('input', { type: 'checkbox' });
    openModal({
      title: message ? 'الإبلاغ عن رسالة' : `الإبلاغ عن ${friend.full_name}`,
      content: h('div', { class: 'col' },
        h('p', { class: 'muted' }, 'سيراجع البلاغ فريق الإشراف في جذور، ولن يعرف الطرف الآخر أنك أبلغت.'),
        h('div', { class: 'field' }, h('label', null, 'السبب'), reason),
        h('div', { class: 'field' }, h('label', null, 'تفاصيل'), details),
        h('label', { class: 'row nowrap' }, alsoBlock, h('span', null, 'احظر هذا المستخدم أيضاً'))),
      actions: [
        { label: 'إلغاء', kind: 'ghost' },
        { label: 'إرسال البلاغ', kind: 'primary', onClick: async () => {
          const block = !!alsoBlock.checked;
          try {
            await api.post('/community/report', { user_id: friend.user_id, message_id: message ? message.message_id : null, reason: reason.value, details: details.value.trim(), also_block: block });
            toast('وصل بلاغك، شكراً لحرصك على سلامة الجميع.', 'success');
            if (block) await afterBlock();
          } catch (err) {
            handleError(err);
          }
        } },
      ],
    });
  }

  async function openBlocked() {
    const holder = h('div', { class: 'col' }, h('div', { class: 'spin' }));
    openModal({ title: 'المستخدمون المحظورون', content: holder, actions: [{ label: 'إغلاق', kind: 'ghost' }] });
    async function paint() {
      try {
        const rows = await api.get('/community/blocked');
        mount(holder, rows.length
          ? rows.map((u) => h('div', { class: 'row nowrap', style: { padding: '8px 0', borderBottom: '1px dashed var(--line)' } },
            avatarEl(u, 'sm'), h('div', { class: 'grow' }, h('b', null, u.full_name), h('div', { class: 'small muted ltr' }, `#${u.handle || ''}`)),
            h('button', { class: 'btn btn-ghost btn-sm', type: 'button', onclick: async () => {
              try {
                await api.del(`/community/block/${u.user_id}`);
                toast('تم إلغاء الحظر.', 'info');
                await paint();
              } catch (err) {
                handleError(err);
              }
            } }, 'إلغاء الحظر')))
          : h('p', { class: 'muted' }, 'لا يوجد مستخدمون محظورون.'));
      } catch (err) {
        mount(holder, errorPanel(err, paint));
      }
    }
    await paint();
  }

  function openAdd() {
    const input = h('input', { class: 'input', placeholder: 'معرّف الصديق (أرقام) أو بريده الإلكتروني', dir: 'ltr', autocomplete: 'off' });
    const results = h('div', { class: 'col', style: { marginTop: '14px' } });
    const run = async () => {
      const q = input.value.trim();
      if (q.length < 2) return;
      mount(results, h('div', { class: 'spin' }));
      try {
        const rows = await api.get('/community/search', { params: { q } });
        if (!rows.length) {
          mount(results, h('div', { class: 'muted center' }, 'لا يوجد مستخدم بهذا المعرّف. تأكد منه واطلب من صديقك نسخه من صفحة المجتمع.'));
          return;
        }
        mount(results, rows.map((u) => {
          let action;
          if (!u.friendship_status) {
            action = h('button', { class: 'btn btn-primary btn-sm' }, 'إضافة');
            action.addEventListener('click', async () => {
              try {
                await api.post(`/community/request/${u.user_id}`, {});
                toast('تم إرسال طلب الصداقة.', 'success');
                action.replaceWith(h('span', { class: 'chip' }, 'بانتظار القبول'));
                loadLists();
              } catch (err) {
                handleError(err);
              }
            });
          } else {
            const label = { accepted: 'صديق بالفعل', pending_outgoing: 'بانتظار القبول', pending_incoming: 'أرسل لك طلباً، راجع الطلبات', blocked: 'غير متاح' }[u.friendship_status];
            action = h('span', { class: 'chip' }, label);
          }
          return h('div', { class: 'row nowrap' }, avatarEl(u), h('div', { class: 'grow' }, h('b', null, u.full_name), h('div', { class: 'small muted ltr' }, `#${u.handle || ''}`)), action);
        }));
      } catch (err) {
        mount(results, h('div', { class: 'err' }, err.message));
      }
    };
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') run(); });
    openModal({
      title: 'إضافة صديق',
      content: h('div', null, h('div', { class: 'row nowrap' }, h('div', { class: 'grow' }, input), h('button', { class: 'btn btn-primary', onclick: run }, ico('search'), 'بحث')), results),
    });
    setTimeout(() => input.focus(), 60);
  }

  function paintEmptyMain() {
    mount(main, h('div', { class: 'empty', style: { flex: '1' } }, ico('chat'), h('h3', null, 'اختر محادثة'), h('p', { class: 'small' }, 'اختر صديقاً من القائمة لتبدأ الدردشة، أو أضف صديقاً جديداً.')));
  }

  paintTop();
  paintEmptyMain();
  mount(convListEl, h('div', { class: 'col', style: { padding: '16px' } }, h('div', { class: 'skeleton', style: { height: '60px' } }), h('div', { class: 'skeleton', style: { height: '60px' } })));
  await loadLists();
  if (ctx.destroyed) return;
  listTimer = setInterval(loadLists, 8000);
  if (ctx.query.with) {
    const target = convs.find((c) => c.friend.user_id === ctx.query.with);
    if (target) openThread(target);
  }
}
