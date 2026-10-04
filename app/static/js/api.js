const TOKEN_KEY = 'juthoor.token';

const MESSAGES = {
  network: 'تعذّر الاتصال بالخادم. تأكد من أنه يعمل ثم حاول مجدداً.',
  server_error: 'حدث خطأ في الخادم. حاول مرة أخرى بعد قليل.',
  database_unavailable: 'قاعدة البيانات غير متاحة الآن. تأكد من تشغيل PostgreSQL ثم أعد المحاولة.',
  student_only: 'هذه العملية متاحة للطالب نفسه فقط.',
  unknown: 'حدث خطأ غير متوقع.',
  validation: 'بعض المدخلات غير صحيحة، راجعها وحاول مجدداً.',
  invalid_credentials: 'البريد الإلكتروني أو كلمة المرور غير صحيحة.',
  email_already_registered: 'هذا البريد مسجّل مسبقاً، جرّب تسجيل الدخول.',
  guardian_must_be_existing_parent: 'بريد ولي الأمر غير مسجّل كحساب ولي أمر.',
  child_id_required: 'رمز الطالب (Child ID) مطلوب لإنشاء حساب ولي الأمر.',
  child_id_invalid: 'رمز الطالب غير صحيح. انسخه كما يظهر في حساب ابنك على جذور.',
  child_already_linked: 'هذا الطالب مرتبط بحساب ولي أمر آخر.',
  no_active_question: 'انتهت صلاحية السؤال، سنعرض سؤالاً جديداً.',
  cannot_access_student: 'لا تملك صلاحية عرض بيانات هذا الطالب.',
  insufficient_role: 'هذه الصفحة غير متاحة لنوع حسابك.',
  invalid_token: 'انتهت الجلسة، سجّل الدخول من جديد.',
  user_not_found: 'المستخدم غير موجود.',
  session_not_found: 'جلسة غير موجودة أو منتهية.',
  unknown_skill_context: 'الدرس غير معروف.',
  cannot_friend_self: 'لا يمكنك إضافة نفسك.',
  friendship_exists: 'طلب الصداقة موجود مسبقاً.',
  friendship_not_found: 'طلب الصداقة غير موجود.',
  not_your_incoming_request: 'هذا الطلب ليس موجهاً إليك.',
  not_friends: 'يجب قبول الصداقة أولاً قبل المراسلة.',
  friend_limit_reached: 'وصلت إلى الحد الأقصى للأصدقاء في الباقة المجانية.',
  empty_message: 'اكتب رسالة أولاً.',
  session_not_pending: 'تم استخدام جلسة الدفع مسبقاً.',
  confirm_only_for_mock_provider: 'يجب إتمام الدفع عبر بوابة الدفع.',
  bad_card: 'بيانات البطاقة غير صحيحة.',
  payment_provider_not_configured: 'الدفع الإلكتروني غير مفعّل بعد على هذا الخادم، ولم يُخصم أي مبلغ.',
  payment_provider_unavailable: 'تعذّر الاتصال ببوابة الدفع الآن. لم يُخصم أي مبلغ، حاول مجدداً بعد قليل.',
  pro_plan_for_students: 'باقة برو مخصصة للطلاب وأولياء الأمور.',
  child_required: 'اختر الابن الذي ستفعّل له الباقة.',
  payment_not_completed: 'لم يكتمل الدفع بعد.',
  not_a_stripe_session: 'جلسة الدفع غير صالحة.',
  invalid_or_expired_code: 'الرمز غير صحيح أو انتهت صلاحيته.',
  too_many_attempts: 'محاولات كثيرة. انتظر بضع دقائق ثم حاول مجدداً.',
  student_only: 'هذه الميزة متاحة للطالب نفسه فقط.',
  unknown_skill: 'الدرس غير معروف.',
  bad_after: 'طلب غير صحيح.',
  rate_limited: 'طلبات كثيرة خلال وقت قصير. انتظر قليلاً ثم حاول مجدداً.',
  message_link: 'لا يُسمح بإرسال الروابط في الدردشة حفاظاً على سلامتك.',
  message_contact: 'لا يُسمح بمشاركة أرقام الهاتف أو البريد أو حسابات التواصل في الدردشة حفاظاً على سلامتك.',
  unblock_first: 'ألغِ الحظر أولاً إن أردت إرسال طلب صداقة.',
  report_not_found: 'البلاغ غير موجود.',
  cannot_block_self: 'لا يمكنك حظر نفسك.',
  cannot_report_self: 'لا يمكنك الإبلاغ عن نفسك.',
  not_blocked: 'هذا المستخدم غير محظور.',
  message_not_found: 'تعذّر العثور على الرسالة المُبلَّغ عنها.',
};

const FIELDS = {
  password: 'كلمة المرور يجب ألا تقل عن 6 أحرف.',
  new_password: 'كلمة المرور يجب ألا تقل عن 6 أحرف.',
  email: 'صيغة البريد الإلكتروني غير صحيحة.',
  guardian_email: 'صيغة بريد ولي الأمر غير صحيحة.',
  child_id: 'رمز الطالب غير صحيح.',
  full_name: 'يرجى كتابة الاسم.',
  role: 'نوع الحساب غير مسموح.',
  selected_answer: 'يرجى إدخال إجابة.',
  message: 'الرسالة فارغة أو طويلة جداً.',
  body: 'الرسالة فارغة أو طويلة جداً.',
  code: 'الرمز يتكون من 6 أرقام.',
};

export class ApiError extends Error {
  constructor(message, status = 0, code = '', upsell = null) {
    super(message);
    this.status = status;
    this.code = code;
    this.upsell = upsell;
  }
}

let token = '';
try {
  token = localStorage.getItem(TOKEN_KEY) || '';
} catch (e) {
  token = '';
}

let onExpired = () => {};

export function setToken(value) {
  token = value || '';
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch (e) {
    token = value || '';
  }
}

export function getToken() {
  return token;
}

export function setExpiredHandler(fn) {
  onExpired = fn;
}

export function toError(status, data) {
  const detail = data && data.detail;
  if (typeof detail === 'string') {
    const [code, arg] = detail.split(':');
    let upsell = null;
    let message = MESSAGES[code] || MESSAGES.unknown;
    if (code === 'message_not_allowed') message = arg === 'link' ? MESSAGES.message_link : MESSAGES.message_contact;
    if (code === 'daily_limit_reached') {
      upsell = { type: 'quota', kind: arg };
      message = arg === 'tutor' ? 'استنفدت رسائل المساعد الذكي لهذا اليوم في الباقة المجانية.' : 'استنفدت أسئلة التدريب لهذا اليوم في الباقة المجانية.';
    } else if (code === 'plan_upgrade_required') {
      upsell = { type: 'plan', plan: arg };
      message = 'هذه الميزة تحتاج باقة برو.';
    } else if (code === 'friend_limit_reached') {
      upsell = { type: 'friends' };
    } else if (code === 'item_not_owned') {
      message = MESSAGES.item_not_owned;
    }
    return new ApiError(message, status, code, upsell);
  }
  if (Array.isArray(detail) && detail.length) {
    const loc = detail[0].loc || [];
    const field = loc[loc.length - 1];
    return new ApiError(FIELDS[field] || MESSAGES.validation, status, 'validation');
  }
  if (status >= 500) return new ApiError(MESSAGES.server_error, status, 'server_error');
  return new ApiError(MESSAGES.unknown, status, 'unknown');
}

async function request(method, path, opts = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let body;
  if (opts.form) {
    body = opts.form;
  } else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }
  let res;
  try {
    res = await fetch(path, { method, headers, body, signal: opts.signal });
  } catch (e) {
    if (e && e.name === 'AbortError') throw e;
    throw new ApiError(MESSAGES.network, 0, 'network');
  }
  if (opts.blob) {
    if (!res.ok) throw toError(res.status, null);
    return res.blob();
  }
  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (e) {
      data = null;
    }
  }
  if (!res.ok) {
    const err = toError(res.status, data);
    if (res.status === 401 && (err.code === 'invalid_token' || err.code === 'user_not_found')) onExpired();
    throw err;
  }
  return data;
}

const cache = new Map();
const inflight = new Map();

function query(params) {
  if (!params) return '';
  const parts = Object.keys(params).filter((k) => params[k] !== undefined && params[k] !== null).map((k) => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`);
  return parts.length ? `?${parts.join('&')}` : '';
}

export const api = {
  get(path, opts = {}) {
    const url = path + query(opts.params);
    const ttl = opts.ttl || 0;
    if (ttl) {
      const hit = cache.get(url);
      if (hit && hit.until > Date.now()) return Promise.resolve(hit.data);
    }
    if (!opts.signal && inflight.has(url)) return inflight.get(url);
    const p = request('GET', url, opts).then((data) => {
      if (ttl) cache.set(url, { data, until: Date.now() + ttl });
      return data;
    }).finally(() => inflight.delete(url));
    if (!opts.signal) inflight.set(url, p);
    return p;
  },
  post: (path, body, opts = {}) => request('POST', path, { ...opts, body }),
  put: (path, body, opts = {}) => request('PUT', path, { ...opts, body }),
  patch: (path, body, opts = {}) => request('PATCH', path, { ...opts, body }),
  del: (path, opts = {}) => request('DELETE', path, opts),
  invalidate(prefix = '') {
    for (const key of Array.from(cache.keys())) if (key.startsWith(prefix)) cache.delete(key);
  },
  async download(path, filename) {
    const blob = await request('GET', path, { blob: true });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  },
};
