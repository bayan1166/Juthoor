import { h, ico, mount, clear, toast } from '../dom.js';
import { api } from '../api.js';
import { store, getTheme, setTheme } from '../store.js';
import { brandHtml } from '../icons.js';
import { renderTreeStage, demoTreeData } from '../tree.js';
import { withBusy } from './shared.js';

const DEMOS = [
  // Every account lands on its home (the tree for students); nothing jumps straight into practice.
  { label: 'طالب (عمر - برو)', email: 'student2@demo.jo', featured: true },
  { label: 'طالبة (ليان - برو)', email: 'student1@demo.jo' },
  { label: 'طالبة (مريم - مجانية)', email: 'student3@demo.jo' },
  { label: 'ولي أمر', email: 'parent@demo.jo' },
];

function strength(v) {
  let s = 0;
  if (v.length >= 6) s += 1;
  if (v.length >= 10) s += 1;
  if (/[A-Za-z\u0600-\u06FF]/.test(v) && /\d/.test(v)) s += 1;
  if (/[^A-Za-z0-9\u0600-\u06FF]/.test(v)) s += 1;
  return s;
}

function otpInput(onComplete) {
  const boxes = [];
  const wrap = h('div', { class: 'otp' });
  for (let i = 0; i < 6; i += 1) {
    const input = h('input', { type: 'text', inputmode: 'numeric', maxlength: '1', autocomplete: i === 0 ? 'one-time-code' : 'off', 'aria-label': `الخانة ${i + 1}` });
    boxes.push(input);
    wrap.appendChild(input);
  }
  const value = () => boxes.map((b) => b.value).join('');
  boxes.forEach((box, i) => {
    box.addEventListener('input', () => {
      box.value = box.value.replace(/\D/g, '').slice(-1);
      if (box.value && i < 5) boxes[i + 1].focus();
      if (value().length === 6) onComplete();
    });
    box.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && !box.value && i > 0) boxes[i - 1].focus();
    });
    box.addEventListener('paste', (e) => {
      const data = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '').slice(0, 6);
      if (!data) return;
      e.preventDefault();
      data.split('').forEach((d, j) => { boxes[j].value = d; });
      boxes[Math.min(data.length, 5)].focus();
      if (data.length === 6) onComplete();
    });
  });
  return {
    el: wrap,
    value,
    fill(code) { code.split('').forEach((d, j) => { boxes[j].value = d; }); },
    focus() { boxes[0].focus(); },
  };
}

function passwordField(label, autocomplete) {
  const input = h('input', { class: 'input', type: 'password', autocomplete, required: true, minlength: '6' });
  const toggle = h('button', { type: 'button', class: 'toggle', 'aria-label': 'إظهار كلمة المرور' }, ico('eye'));
  toggle.addEventListener('click', () => {
    const show = input.getAttribute('type') === 'password';
    input.setAttribute('type', show ? 'text' : 'password');
    clear(toggle);
    toggle.appendChild(ico(show ? 'eyeoff' : 'eye'));
  });
  const el = h('div', { class: 'field' }, h('label', null, label), h('div', { class: 'input-wrap' }, input, toggle));
  return { el, input };
}

export async function authView(ctx) {
  let screen = ctx.params.mode === 'register' ? 'register' : 'login';
  let resetEmail = '';
  let resetCode = '';
  let resetToken = '';
  let demoCode = '';
  let role = 'student';
  let gender = 'ولد';
  let timer = null;
  const page = h('div', { class: 'auth page-enter' });
  const side = h('div', { class: 'auth-side' });
  const card = h('div', { class: 'auth-card' });
  // Light/dark switch is available before sign-in too (the app header only exists after login).
  const themeBtn = h('button', { class: 'icon-btn auth-theme', type: 'button', 'aria-label': 'تبديل المظهر', title: 'الوضع الفاتح / الداكن' }, ico(getTheme() === 'dark' ? 'sun' : 'moon'));
  themeBtn.addEventListener('click', () => {
    const next = getTheme() === 'dark' ? 'light' : 'dark';
    setTheme(next);
    clear(themeBtn);
    themeBtn.appendChild(ico(next === 'dark' ? 'sun' : 'moon'));
  });
  const main = h('div', { class: 'auth-main' }, themeBtn, card);
  side.appendChild(h('div', { class: 'top' }, h('a', { class: 'brand', href: '#/login', html: brandHtml() })));
  const courseNote = h('div', { class: 'course-note', hidden: true });
  side.appendChild(h('div', { class: 'copy' },
    h('h1', null, 'اعرف أين بدأت الفجوة، لا أين ظهرت'),
    h('p', null, 'قد يعرف الطالب أن السؤال صعب، دون أن يعرف أي فكرة سابقة تسبّب الصعوبة. جذور يجمع الأدلة من إجاباته، ويفحص المتطلبات السابقة، ويعيده إلى الجذر الأرجح حتى يتقنه، ثم يرجع به إلى درسه.'),
    h('ul', null,
      h('li', null, ico('target'), 'تشخيص مبني على الأدلة، بثقة معلنة بصدق، أو «الأدلة غير كافية بعد»'),
      h('li', null, ico('tree'), 'علاج موجّه للمتطلب الناقص، ثم عودة إلى الدرس الأصلي وتحديث الإتقان'),
      h('li', null, ico('file'), 'تقرير واضح لولي الأمر: أين بدأت الفجوة، وما الخطوة التالية')),
    courseNote));
  page.appendChild(side);
  page.appendChild(main);
  ctx.root.appendChild(page);

  let backdrop = null;
  api.get('/curriculum/map', { ttl: 3600000 }).then((map) => {
    if (ctx.destroyed) return;
    if (map.course) {
      courseNote.textContent = `المحتوى المتاح حالياً للتجربة: ${map.course.subject_ar} · ${map.course.grade_ar}`;
      courseNote.hidden = false;
      courseNote.removeAttribute('hidden');
    }
    backdrop = renderTreeStage(side, demoTreeData(map), { fill: true, bare: true, interactive: false });
  }).catch(() => null);

  ctx.onDestroy(() => {
    clearInterval(timer);
    if (backdrop) backdrop.destroy();
  });

  function errBox() {
    return h('div', { class: 'err', role: 'alert', style: { minHeight: '1.4em' } });
  }

  function paint() {
    clearInterval(timer);
    if (screen === 'login') paintLogin();
    else if (screen === 'register') paintRegister();
    else if (screen === 'forgot1') paintForgotEmail();
    else if (screen === 'forgot2') paintForgotCode();
    else paintForgotNew();
  }

  function shell(title, subtitle, ...children) {
    mount(card, h('div', { class: 'card', style: { padding: '28px' } },
      h('div', { class: 'brand', style: { marginBottom: '14px', display: 'flex' }, html: brandHtml() }),
      h('h2', { style: { marginBottom: '4px' } }, title),
      subtitle ? h('p', { class: 'muted' }, subtitle) : null,
      children));
  }

  async function finish(token, landing) {
    await ctx.login(token, landing);
  }

  function demoRow() {
    if (!store.health.demo) return null;
    return h('div', { class: 'col', style: { marginTop: '16px', gap: '8px' } },
      h('div', { class: 'small muted center' }, 'وضع العرض: ابدأ بحساب عمر، ثم «تابع التدريب» من شجرته'),
      h('div', { class: 'row', style: { justifyContent: 'center', gap: '8px' } }, DEMOS.map((d) => h('button', {
        class: d.featured ? 'chip green' : 'chip', type: 'button', onclick: async (e) => {
          const btn = e.currentTarget;
          await withBusy(btn, async () => {
            try {
              const res = await api.post('/auth/login', { email: d.email, password: 'demo1234' });
              await finish(res.access_token);
            } catch (err) {
              toast(err.message, 'error');
            }
          });
        },
      }, d.label))));
  }

  function paintLogin() {
    const email = h('input', { class: 'input', type: 'email', autocomplete: 'username', required: true, placeholder: 'name@example.com', dir: 'ltr' });
    const pw = passwordField('كلمة المرور', 'current-password');
    const err = errBox();
    const submit = h('button', { class: 'btn btn-primary btn-lg btn-block', type: 'submit' }, 'تسجيل الدخول');
    const form = h('form', { class: 'col', novalidate: true, onsubmit: async (e) => {
      e.preventDefault();
      err.textContent = '';
      if (!email.value.trim() || !pw.input.value) {
        err.textContent = 'أدخل البريد الإلكتروني وكلمة المرور.';
        return;
      }
      await withBusy(submit, async () => {
        try {
          const res = await api.post('/auth/login', { email: email.value.trim(), password: pw.input.value });
          await finish(res.access_token);
        } catch (ex) {
          err.textContent = ex.message;
        }
      });
    } },
      h('div', { class: 'field' }, h('label', null, 'البريد الإلكتروني'), email),
      pw.el,
      h('div', null, h('button', { class: 'btn btn-ghost btn-sm', type: 'button', style: { border: 'none', padding: 0, minHeight: 0, color: 'var(--g-600)' }, onclick: () => { screen = 'forgot1'; paint(); } }, 'نسيت كلمة المرور؟')),
      err, submit);
    shell('أهلاً بعودتك', 'سجّل الدخول لمتابعة شجرتك.', form,
      h('div', { class: 'center small', style: { marginTop: '16px' } }, 'ليس لديك حساب؟ ', h('a', { href: '#/register', onclick: (e) => { e.preventDefault(); screen = 'register'; paint(); } }, 'أنشئ حساباً')),
      demoRow());
  }

  function paintRegister() {
    const name = h('input', { class: 'input', required: true, autocomplete: 'name' });
    const email = h('input', { class: 'input', type: 'email', required: true, autocomplete: 'username', dir: 'ltr' });
    const pw = passwordField('كلمة المرور (6 أحرف على الأقل)', 'new-password');
    const meterFill = h('i');
    const guardian = h('input', { class: 'input', type: 'email', placeholder: 'اختياري', dir: 'ltr' });
    const err = errBox();
    const extra = h('div', { class: 'col' });
    pw.input.addEventListener('input', () => {
      const s = strength(pw.input.value);
      meterFill.style.width = `${s * 25}%`;
      meterFill.style.background = s <= 1 ? 'var(--danger)' : s === 2 ? 'var(--amber)' : 'var(--g-500)';
    });
    const roleSeg = h('div', { class: 'seg' });
    const genderRow = h('div', { class: 'field' });
    const buttons = {};
    const labels = { student: 'طالب', parent: 'ولي أمر' };
    function paintRole() {
      for (const k of Object.keys(buttons)) buttons[k].classList.toggle('on', k === role);
      clear(extra);
      clear(genderRow);
      if (role === 'student') {
        genderRow.appendChild(h('label', null, 'اختر الشخصية'));
        const row = h('div', { class: 'grid g2' });
        for (const g of ['ولد', 'بنت']) {
          const b = h('button', { type: 'button', class: ['opt-card', g === gender ? 'on' : ''], onclick: () => { gender = g; paintRole(); } }, g);
          row.appendChild(b);
        }
        genderRow.appendChild(row);
        extra.appendChild(h('div', { class: 'field' }, h('label', null, 'بريد ولي الأمر (ليتابع تقريرك ويشترك لك في برو)'), guardian));
      }
    }
    for (const k of Object.keys(labels)) {
      buttons[k] = h('button', { type: 'button', onclick: () => { role = k; paintRole(); } }, labels[k]);
      roleSeg.appendChild(buttons[k]);
    }
    const submit = h('button', { class: 'btn btn-primary btn-lg btn-block', type: 'submit' }, 'إنشاء الحساب');
    const form = h('form', { class: 'col', novalidate: true, onsubmit: async (e) => {
      e.preventDefault();
      err.textContent = '';
      if (!name.value.trim() || !email.value.trim()) {
        err.textContent = 'أكمل الاسم والبريد الإلكتروني.';
        return;
      }
      if (pw.input.value.length < 6) {
        err.textContent = 'كلمة المرور يجب ألا تقل عن 6 أحرف.';
        return;
      }
      const body = { full_name: name.value.trim(), email: email.value.trim(), password: pw.input.value, role };
      if (role === 'student') {
        body.gender = gender;
        if (guardian.value.trim()) body.guardian_email = guardian.value.trim();
      }
      await withBusy(submit, async () => {
        try {
          const res = await api.post('/auth/register', body);
          await finish(res.access_token);
        } catch (ex) {
          err.textContent = ex.message;
        }
      });
    } },
      h('div', { class: 'field' }, h('label', null, 'نوع الحساب'), roleSeg),
      h('div', { class: 'field' }, h('label', null, 'الاسم الكامل'), name),
      h('div', { class: 'field' }, h('label', null, 'البريد الإلكتروني'), email),
      h('div', { class: 'col', style: { gap: '6px' } }, pw.el, h('div', { class: 'meter' }, meterFill)),
      genderRow, extra, err, submit);
    paintRole();
    shell('أنشئ حسابك', 'دقيقة واحدة وتبدأ رحلتك.', form,
      h('div', { class: 'center small', style: { marginTop: '16px' } }, 'لديك حساب؟ ', h('a', { href: '#/login', onclick: (e) => { e.preventDefault(); screen = 'login'; paint(); } }, 'سجّل الدخول')));
  }

  function stepsBar(n) {
    return h('div', { class: 'steps' }, [1, 2, 3].map((i) => h('i', { class: i <= n ? 'on' : '' })));
  }

  function paintForgotEmail() {
    const email = h('input', { class: 'input', type: 'email', required: true, autocomplete: 'username', dir: 'ltr', value: resetEmail, placeholder: 'name@example.com' });
    const err = errBox();
    const submit = h('button', { class: 'btn btn-primary btn-lg btn-block', type: 'submit' }, 'إرسال الرمز');
    const form = h('form', { class: 'col', novalidate: true, onsubmit: async (e) => {
      e.preventDefault();
      err.textContent = '';
      if (!email.value.trim() || !email.value.includes('@')) {
        err.textContent = 'أدخل بريداً إلكترونياً صحيحاً.';
        return;
      }
      await withBusy(submit, async () => {
        try {
          const res = await api.post('/auth/forgot-password', { email: email.value.trim() });
          resetEmail = email.value.trim().toLowerCase();
          demoCode = res.demo_code || '';
          screen = 'forgot2';
          paint();
        } catch (ex) {
          err.textContent = ex.message;
        }
      });
    } },
      h('div', { class: 'field' }, h('label', null, 'البريد الإلكتروني المسجّل'), email), err, submit,
      h('button', { class: 'btn btn-ghost btn-block', type: 'button', onclick: () => { screen = 'login'; paint(); } }, 'العودة لتسجيل الدخول'));
    shell('استعادة كلمة المرور', 'أدخل بريدك الإلكتروني وسنرسل لك رمز تحقق من 6 أرقام.', stepsBar(1), form);
  }

  function paintForgotCode() {
    const err = errBox();
    const submit = h('button', { class: 'btn btn-primary btn-lg btn-block', type: 'button' }, 'تحقّق من الرمز');
    const otp = otpInput(() => submit.click());
    const resend = h('button', { class: 'btn btn-ghost btn-sm', type: 'button', disabled: true }, 'إعادة الإرسال');
    let left = 30;
    const tick = () => {
      resend.textContent = left > 0 ? `إعادة الإرسال بعد ${left} ثانية` : 'إعادة إرسال الرمز';
      if (left <= 0) {
        resend.disabled = false;
        resend.removeAttribute('disabled');
        clearInterval(timer);
      }
      left -= 1;
    };
    tick();
    timer = setInterval(tick, 1000);
    resend.addEventListener('click', async () => {
      try {
        const res = await api.post('/auth/forgot-password', { email: resetEmail });
        demoCode = res.demo_code || '';
        toast('أرسلنا رمزاً جديداً.', 'success');
        paint();
      } catch (ex) {
        err.textContent = ex.message;
      }
    });
    submit.addEventListener('click', async () => {
      err.textContent = '';
      const code = otp.value();
      if (code.length !== 6) {
        err.textContent = 'أدخل الرمز المكوّن من 6 أرقام.';
        return;
      }
      await withBusy(submit, async () => {
        try {
          const res = await api.post('/auth/verify-reset-code', { email: resetEmail, code });
          resetToken = res.reset_token;
          resetCode = code;
          screen = 'forgot3';
          paint();
        } catch (ex) {
          err.textContent = ex.message;
        }
      });
    });
    const demo = demoCode ? h('div', { class: 'banner' }, ico('info'), h('div', null, 'وضع العرض: رمزك هو ', h('b', { class: 'ltr' }, demoCode), ' ', h('button', { class: 'btn btn-sm', type: 'button', onclick: () => otp.fill(demoCode) }, 'تعبئة تلقائية'))) : null;
    shell('أدخل رمز التحقق', `أرسلنا رمزاً إلى ${resetEmail}. تحقق من بريدك وأدخله هنا.`, stepsBar(2), demo, otp.el, err, submit,
      h('div', { class: 'row between' }, resend, h('button', { class: 'btn btn-ghost btn-sm', type: 'button', onclick: () => { screen = 'forgot1'; paint(); } }, 'تغيير البريد')));
    setTimeout(() => otp.focus(), 50);
  }

  function paintForgotNew() {
    const a = passwordField('كلمة المرور الجديدة', 'new-password');
    const b = passwordField('تأكيد كلمة المرور', 'new-password');
    const err = errBox();
    const submit = h('button', { class: 'btn btn-primary btn-lg btn-block', type: 'submit' }, 'حفظ كلمة المرور');
    const form = h('form', { class: 'col', novalidate: true, onsubmit: async (e) => {
      e.preventDefault();
      err.textContent = '';
      if (a.input.value.length < 6) {
        err.textContent = 'كلمة المرور يجب ألا تقل عن 6 أحرف.';
        return;
      }
      if (a.input.value !== b.input.value) {
        err.textContent = 'كلمتا المرور غير متطابقتين.';
        return;
      }
      await withBusy(submit, async () => {
        try {
          const res = await api.post('/auth/reset-password', { reset_token: resetToken, new_password: a.input.value });
          toast('تم تحديث كلمة المرور.', 'success');
          await finish(res.access_token);
        } catch (ex) {
          err.textContent = ex.message;
          if (ex.code === 'invalid_or_expired_code') {
            screen = 'forgot1';
            setTimeout(paint, 1800);
          }
        }
      });
    } }, a.el, b.el, err, submit);
    shell('كلمة مرور جديدة', 'تم التحقق من الرمز. اختر كلمة مرور جديدة وأكّدها.', stepsBar(3), form);
  }

  paint();
}
