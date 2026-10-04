import { h, ico, mount, clear, toast, jod, fmtDate } from '../dom.js';
import { api } from '../api.js';
import { store, loadMe, isInternal, isParent } from '../store.js';
import { errorPanel, handleError, withBusy } from './shared.js';

export function luhn(value) {
  const digits = String(value).replace(/\D/g, '');
  if (digits.length < 12 || digits.length > 19) return false;
  let sum = 0;
  let alt = false;
  for (let i = digits.length - 1; i >= 0; i -= 1) {
    let n = Number(digits[i]);
    if (alt) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    sum += n;
    alt = !alt;
  }
  return sum % 10 === 0;
}

export function cardBrand(value) {
  const d = String(value).replace(/\D/g, '');
  if (/^4/.test(d)) return 'Visa';
  if (/^(5[1-5]|2[2-7])/.test(d)) return 'Mastercard';
  if (/^3[47]/.test(d)) return 'Amex';
  return '';
}

export function expiryOk(value, now = new Date()) {
  const m = /^(\d{2})\s*\/\s*(\d{2})$/.exec(value.trim());
  if (!m) return false;
  const month = Number(m[1]);
  const year = 2000 + Number(m[2]);
  if (month < 1 || month > 12) return false;
  return year > now.getFullYear() || (year === now.getFullYear() && month >= now.getMonth() + 1);
}

function limitCell(value) {
  if (value === null) return 'غير محدود';
  if (value === true) return ico('check');
  if (value === false) return ico('x');
  return String(value);
}

function uspBlock(usp) {
  const chain = h('div', { class: 'chain', style: { marginTop: '8px' } },
    h('span', { class: 'node' }, 'الدرس الحالي'), h('span', { class: 'arrow' }, ico('chevl')),
    h('span', { class: 'node' }, 'متطلب سابق'), h('span', { class: 'arrow' }, ico('chevl')),
    h('span', { class: 'node blur-lock' }, 'درس مخفي'), h('span', { class: 'arrow' }, ico('chevl')),
    h('span', { class: 'node blur-lock root' }, 'الجذر'));
  return h('div', { class: 'usp' },
    h('div', null, h('span', { class: 'chip lime' }, ico('target'), usp.name), h('h2', { style: { color: '#fff', marginTop: '10px' } }, usp.headline), h('p', null, usp.body),
      h('ul', null, usp.points.map((t) => h('li', null, ico('check'), t)))),
    h('div', { class: 'demo' }, h('div', { class: 'small', style: { opacity: 0.85 } }, 'هكذا يرى الطالب في الباقة المجانية سلسلة تعثّره'), chain,
      h('div', { class: 'row', style: { marginTop: '12px' } }, ico('lock'), h('span', null, 'باقة برو تكشف الجذر والخطة المقترحة لسدّه'))));
}

const PERIOD_LABEL = { monthly: 'شهري', yearly: 'السنة الدراسية' };
const PERIOD_UNIT = { monthly: 'دينار / شهر', yearly: 'دينار / السنة الدراسية' };

export async function plansView(ctx) {
  const me = store.me;
  const page = h('div', { class: 'page page-enter wide' });
  ctx.root.appendChild(page);
  mount(page, h('div', { class: 'skeleton', style: { height: '320px' } }));

  const banners = [];
  if (ctx.query.paid) {
    let sid = null;
    try {
      sid = sessionStorage.getItem('juthoor.stripe');
    } catch (e) {
      sid = null;
    }
    if (sid) {
      try {
        await api.post('/payments/confirm-stripe', { session_id: sid });
        sessionStorage.removeItem('juthoor.stripe');
        await loadMe();
        store.boot = null;
        ctx.refreshShell();
        toast('تم تفعيل اشتراكك.', 'success');
      } catch (err) {
        banners.push(h('div', { class: 'banner warn', role: 'alert' }, ico('alert'), h('div', null, `لم يتأكد الدفع بعد: ${err.message} لم يُفعَّل برو، ويمكنك المحاولة مجدداً من الأسفل.`)));
      }
    }
  }
  if (ctx.query.canceled) banners.push(h('div', { class: 'banner', role: 'status' }, ico('info'), h('div', null, 'لم يكتمل الدفع ولم يُخصم أي مبلغ. يمكنك المحاولة مجدداً متى شئت.')));

  let data;
  try {
    data = await api.get('/payments/plans', { ttl: 300000 });
  } catch (err) {
    mount(page, errorPanel(err, () => ctx.reload()));
    return;
  }
  const current = me.plan;
  const pro = data.plans.find((p) => p.id === 'pro');
  const basic = data.plans.find((p) => p.id === 'basic');
  const unavailable = data.provider === 'none';

  function proCta(period) {
    const href = `#/checkout/pro?period=${period}`;
    if (isInternal()) return h('button', { class: 'btn btn-block', disabled: true }, 'الاشتراك للطلاب وأولياء الأمور');
    if (unavailable) return h('button', { class: 'btn btn-block', disabled: true }, 'الدفع غير مفعّل بعد');
    const label = isParent() ? 'فعّل برو لابنك' : current === 'pro' ? `تجديد (حتى ${fmtDate(me.plan_expires_at)})` : 'ترقية إلى برو';
    return h('a', { class: ['btn btn-block', period === 'yearly' ? 'btn-primary' : 'btn-ghost'], href, 'data-testid': `buy-pro-${period}` }, ico('bolt'), label);
  }

  function features(list) {
    return h('ul', null, list.map((f) => h('li', { class: f.included ? '' : 'off' }, ico(f.included ? 'check' : 'x'), h('span', null, f.text))));
  }

  function proCard(period) {
    const amount = period === 'yearly' ? pro.price_year : pro.price_month;
    const rec = period === 'yearly';
    return h('div', { class: ['plan', rec ? 'hl' : ''], 'data-plan': `pro-${period}` },
      rec ? h('span', { class: 'ribbon' }, 'الخيار الموصى به') : null,
      h('div', null, h('h3', null, `برو · ${PERIOD_LABEL[period]}`), h('span', { class: 'chip' }, pro.audience)),
      h('p', { class: 'tag' }, rec ? 'اشتراك واحد يغطي السنة الدراسية كاملة، دون تجديد شهري.' : pro.tagline),
      h('div', null, h('div', { class: 'price' }, h('b', null, jod(amount)), h('span', null, PERIOD_UNIT[period])), h('div', { class: 'small muted' }, ' ')),
      features(pro.features),
      proCta(period));
  }

  const freeCard = h('div', { class: 'plan', 'data-plan': 'free' },
    h('div', null, h('h3', null, 'مجاني'), h('span', { class: 'chip' }, basic.audience)),
    h('p', { class: 'tag' }, basic.tagline),
    h('div', null, h('div', { class: 'price' }, h('b', null, 'مجاني')), h('div', { class: 'small muted' }, ' ')),
    features(basic.features),
    h('button', { class: 'btn btn-block', disabled: true }, current === 'basic' ? 'خطتك الحالية' : 'متاحة دائماً'));

  const rows = [
    ['الأسئلة اليومية', 'questions_per_day'],
    ['رسائل المساعد الذكي يومياً', 'tutor_per_day'],
    ['كشف سلسلة الجذر وتقرير الفجوة', 'full_gap_report'],
    ['عدد الأصدقاء', 'max_friends'],
    ['سجل التعلّم (أيام)', 'history_days'],
  ];
  const table = h('div', { class: 'table-wrap' }, h('table', { class: 't cmp' },
    h('thead', null, h('tr', null, h('th', null, 'الميزة'), data.plans.map((p) => h('th', null, p.id === 'basic' ? 'مجاني' : p.name_ar)))),
    h('tbody', null, rows.map(([label, key]) => h('tr', null, h('td', null, label), data.plans.map((p) => h('td', null, limitCell(p.limits[key]))))))));

  if (data.provider === 'mock') banners.push(h('div', { class: 'banner', role: 'status' }, ico('info'), h('div', null, 'وضع العرض: بوابة الدفع الحقيقية غير موصولة، ولن يُحصَّل أي مبلغ فعلي.')));
  if (unavailable) banners.push(h('div', { class: 'banner warn', role: 'status' }, ico('alert'), h('div', null, 'الدفع الإلكتروني غير مفعّل بعد على هذا الخادم. الباقة المجانية متاحة بالكامل.')));

  mount(page,
    h('div', { class: 'page-head' }, h('div', null, h('h1', null, 'جذور برو'), h('p', { class: 'muted' }, 'ابدأ مجاناً. يشتري ولي الأمر برو حين يريد كشف جذر الفجوة كاملاً وخطة علاجها.'))),
    banners, uspBlock(data.usp),
    h('div', { class: 'plans plans-3' }, freeCard, proCard('monthly'), proCard('yearly')),
    h('h2', { style: { margin: '36px 0 14px' } }, 'قارن بين المجاني وبرو'), table,
    h('p', { class: 'small muted', style: { marginTop: '14px' } }, 'الأسعار بالدينار الأردني. لا يُجدَّد الاشتراك تلقائياً. يشتري ولي الأمر الاشتراك ويستخدمه الطالب.'));
}

export async function checkoutView(ctx) {
  const planId = ctx.params.plan;
  const period = ctx.query.period === 'yearly' ? 'yearly' : 'monthly';
  const page = h('div', { class: 'page page-enter', style: { maxWidth: '980px' } });
  ctx.root.appendChild(page);
  mount(page, h('div', { class: 'skeleton', style: { height: '320px' } }));
  let data;
  let kids = [];
  try {
    data = await api.get('/payments/plans', { ttl: 300000 });
    if (isParent()) kids = await api.get('/me/students');
  } catch (err) {
    mount(page, errorPanel(err, () => ctx.reload()));
    return;
  }
  const plan = data.plans.find((p) => p.id === planId && p.id !== 'basic');
  if (!plan) {
    mount(page, h('div', { class: 'empty' }, ico('alert'), h('h3', null, 'الباقة غير موجودة'), h('a', { class: 'btn btn-primary', href: '#/plans' }, 'العودة إلى الباقات')));
    return;
  }
  if (isParent() && !kids.length) {
    mount(page, h('div', { class: 'empty' }, ico('users'), h('h3', null, 'لا يوجد أبناء مرتبطون بحسابك'), h('p', { class: 'muted' }, 'اطلب من ابنك إدخال بريدك كولي أمر عند إنشاء حسابه.'), h('a', { class: 'btn btn-primary', href: '#/plans' }, 'رجوع')));
    return;
  }
  if (data.provider === 'none') {
    mount(page, h('div', { class: 'empty' }, ico('alert'), h('h3', null, 'الدفع الإلكتروني غير مفعّل بعد'), h('p', { class: 'muted' }, 'لم يُخصم أي مبلغ. الباقة المجانية متاحة بالكامل.'), h('a', { class: 'btn btn-primary', href: '#/plans' }, 'رجوع')));
    return;
  }
  const isMock = data.provider === 'mock';
  const amount = period === 'yearly' ? plan.price_year : plan.price_month;
  let childId = ctx.query.for || (kids[0] && kids[0].student_id) || '';

  const holder = h('input', { class: 'input', autocomplete: 'cc-name', placeholder: 'الاسم كما على البطاقة', dir: 'ltr' });
  const number = h('input', { class: 'input', inputmode: 'numeric', autocomplete: 'cc-number', placeholder: '0000 0000 0000 0000', dir: 'ltr' });
  const expiry = h('input', { class: 'input', inputmode: 'numeric', autocomplete: 'cc-exp', placeholder: 'MM/YY', maxlength: '5', dir: 'ltr' });
  const cvv = h('input', { class: 'input', inputmode: 'numeric', autocomplete: 'cc-csc', placeholder: 'CVV', maxlength: '4', type: 'password', dir: 'ltr' });
  const errs = h('div', { class: 'err', role: 'alert', style: { minHeight: '1.4em' } });
  const previewNum = h('div', { class: 'num' }, '\u2022\u2022\u2022\u2022 \u2022\u2022\u2022\u2022 \u2022\u2022\u2022\u2022 \u2022\u2022\u2022\u2022');
  const previewName = h('span', { class: 'nm' }, 'CARDHOLDER');
  const previewExp = h('span', null, 'MM/YY');
  const previewBrand = h('b', null, '');
  const preview = h('div', { class: 'cc' }, h('div', { class: 'rowc' }, h('span', null, 'JUTHOOR'), previewBrand), previewNum, h('div', { class: 'rowc' }, previewName, previewExp));

  number.addEventListener('input', () => {
    const digits = number.value.replace(/\D/g, '').slice(0, 19);
    number.value = digits.replace(/(.{4})/g, '$1 ').trim();
    previewNum.textContent = (digits.padEnd(16, '\u2022').replace(/(.{4})/g, '$1 ').trim());
    previewBrand.textContent = cardBrand(digits);
  });
  expiry.addEventListener('input', () => {
    let v = expiry.value.replace(/\D/g, '').slice(0, 4);
    if (v.length > 2) v = `${v.slice(0, 2)}/${v.slice(2)}`;
    expiry.value = v;
    previewExp.textContent = v || 'MM/YY';
  });
  holder.addEventListener('input', () => { previewName.textContent = holder.value.toUpperCase() || 'CARDHOLDER'; });

  const kidSelect = kids.length ? h('select', { class: 'select', 'aria-label': 'الابن' }, kids.map((k) => h('option', { value: k.student_id }, k.full_name))) : null;
  if (kidSelect) {
    kidSelect.value = childId;
    kidSelect.addEventListener('change', () => { childId = kidSelect.value; });
  }
  const pay = h('button', { class: 'btn btn-primary btn-lg btn-block', type: 'submit' }, ico('lock'), isMock ? `تفعيل برو (وضع العرض) · ${jod(amount)} دينار` : `المتابعة إلى الدفع الآمن · ${jod(amount)} دينار`);

  async function success(res, forName) {
    await loadMe();
    store.boot = null;
    ctx.refreshShell();
    mount(page, h('div', { class: 'card center', style: { maxWidth: '520px', margin: '40px auto', padding: '36px' } },
      h('svg', { class: 'check-draw', viewBox: '0 0 34 34', style: { width: '72px', height: '72px', color: 'var(--g-500)' } }, h('path', { d: 'M7 18l7 7 13-14', fill: 'none', stroke: 'currentColor', 'stroke-width': '3', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })),
      h('h2', null, isMock ? 'تم تفعيل برو (وضع العرض)' : 'تم الاشتراك بنجاح'),
      h('p', { class: 'muted' }, forName ? `تم تفعيل باقة ${plan.name_ar} لـ ${forName}.` : `تم تفعيل باقة ${plan.name_ar} على حسابك.`),
      isMock ? h('div', { class: 'banner' }, ico('info'), h('div', null, 'هذا تفعيل تجريبي: لم تُنفَّذ عملية دفع حقيقية ولم يُحصَّل أي مبلغ.')) : null,
      h('div', { class: 'summary-line' }, h('span', null, 'رقم العملية'), h('b', { class: 'ltr' }, String(res.session_id).slice(0, 8).toUpperCase())),
      h('div', { class: 'summary-line' }, h('span', null, 'المبلغ'), h('b', null, `${jod(res.amount_minor)} دينار`)),
      h('div', { class: 'row', style: { justifyContent: 'center', marginTop: '16px' } }, h('a', { class: 'btn btn-primary', href: '#/' }, 'ابدأ الآن'), h('a', { class: 'btn btn-ghost', href: '#/plans' }, 'الباقات'))));
  }

  const form = h('form', { class: 'col', novalidate: true, onsubmit: async (e) => {
    e.preventDefault();
    errs.textContent = '';
    const digits = number.value.replace(/\D/g, '');
    if (isMock) {
      if (!holder.value.trim()) { errs.textContent = 'أدخل اسم حامل البطاقة.'; return; }
      if (!luhn(digits)) { errs.textContent = 'رقم البطاقة غير صحيح.'; return; }
      if (!expiryOk(expiry.value)) { errs.textContent = 'تاريخ الانتهاء غير صحيح أو منتهي.'; return; }
      if (!/^\d{3,4}$/.test(cvv.value)) { errs.textContent = 'رمز CVV غير صحيح.'; return; }
    }
    await withBusy(pay, async () => {
      try {
        const body = { plan: plan.id, period };
        if (isParent()) body.for_student_id = childId;
        const started = await api.post('/payments/checkout', body);
        if (started.stripe_url) {
          try {
            sessionStorage.setItem('juthoor.stripe', started.session_id);
          } catch (ex) {
            toast('سيتم تحويلك إلى بوابة الدفع.', 'info');
          }
          location.href = started.stripe_url;
          return;
        }
        const done = await api.post('/payments/confirm', { session_id: started.session_id, card_last4: digits.slice(-4), card_holder: holder.value.trim() });
        const kid = kids.find((k) => k.student_id === childId);
        await success({ ...done, session_id: started.session_id }, isParent() && kid ? kid.full_name : '');
      } catch (err) {
        if (err.upsell) handleError(err);
        else errs.textContent = err.message;
      }
    });
  } },
    kidSelect ? h('div', { class: 'field' }, h('label', null, 'تفعيل الباقة لـ'), kidSelect) : null,
    isMock ? [
      h('div', { class: 'field' }, h('label', null, 'اسم حامل البطاقة'), holder),
      h('div', { class: 'field' }, h('label', null, 'رقم البطاقة'), number),
      h('div', { class: 'grid g2' }, h('div', { class: 'field' }, h('label', null, 'تاريخ الانتهاء'), expiry), h('div', { class: 'field' }, h('label', null, 'رمز الأمان'), cvv)),
    ] : h('p', { class: 'muted' }, 'ستُحوَّل إلى صفحة الدفع الآمنة لإتمام العملية. لا تُدخل بيانات البطاقة في جذور.'),
    errs, pay,
    h('div', { class: 'small muted center' }, ico('shield'), isMock ? ' وضع العرض: لا تُحفظ بيانات البطاقة ولا يُحصَّل أي مبلغ.' : ' تتم معالجة الدفع لدى مزوّد الدفع، ولا تصل بيانات بطاقتك إلى خوادمنا.'),
    h('a', { class: 'small center', href: '#/plans' }, 'العودة إلى الباقات'));

  mount(page,
    h('div', { class: 'page-head' }, h('div', null, h('h1', null, 'إتمام الاشتراك'), h('p', { class: 'muted' }, 'اشتراك برو للطالب، يشتريه ولي الأمر.'))),
    h('div', { class: 'checkout' },
      h('div', { class: 'card' },
        isMock ? h('div', { class: 'banner' }, ico('info'), h('div', null, 'وضع العرض: بوابة الدفع الحقيقية غير موصولة ولن يُحصَّل أي مبلغ. للتجربة استخدم الرقم ', h('b', { class: 'ltr' }, '4242 4242 4242 4242'), ' مع أي تاريخ مستقبلي.')) : null,
        form),
      h('div', { class: 'col' }, preview,
        h('div', { class: 'card' }, h('h3', null, 'ملخص الطلب'),
          h('div', { class: 'summary-line' }, h('span', null, `باقة ${plan.name_ar}`), h('b', null, PERIOD_LABEL[period])),
          h('div', { class: 'summary-line' }, h('span', null, 'السعر'), h('b', null, `${jod(amount)} دينار`)),
          h('div', { class: 'summary-line total' }, h('span', null, 'الإجمالي'), h('b', null, `${jod(amount)} دينار`))))));
}
