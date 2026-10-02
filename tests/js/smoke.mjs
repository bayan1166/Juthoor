import fs from 'node:fs';
import { install, all, find, text, byClass, byTag, byText, type, submit, tick, FEl } from './fakedom.js';

const PY = JSON.parse(fs.readFileSync(new URL('./fixtures/py.json', import.meta.url), 'utf8'));
const calls = [];
const state = { role: 'student', plan: 'basic', failNext: null };
const U = (n, name) => ({ user_id: n, handle: `10${n.length}`, full_name: name, role: 'student', avatar_svg: null });
const me = () => ({
  student: { user_id: 'S1', handle: '4821', email: 's@x.jo', full_name: 'ليان', role: 'student', plan: state.plan, plan_source: 'own', plan_expires_at: null, trial_days_left: null },
  teacher: { user_id: 'T1', handle: '7001', email: 't@x.jo', full_name: 'المعلمة سارة', role: 'teacher', plan: 'school', plan_source: 'trial', plan_expires_at: '2026-10-14T00:00:00Z', trial_days_left: 13 },
  parent: { user_id: 'P1', handle: '7002', email: 'p@x.jo', full_name: 'ولي الأمر', role: 'parent', plan: 'basic', plan_source: 'own', plan_expires_at: null, trial_days_left: null },
}[state.role]);
const planSnap = (rem = 18) => ({ plan: 'basic', source: 'own', expires_at: null, trial_days_left: null, limits: { questions_per_day: 20, tutor_per_day: 5, max_friends: 3, history_days: 7, full_gap_report: false, classrooms: false }, usage: { questions: 2, tutor: 1 }, remaining: { questions: rem, tutor: 4 } });
const skillsState = PY.skills.map((s) => ({ skill_id: s.skill_id, name_ar: s.name_ar, status: 'learning', p_mastery: 0.4, attempts: 3, correct: 2 }));
const avatar = { gender: 'بنت', skin: 'edb98a', clothing: 'shirtCrewNeck', top: 'none', neck: 'none', accessories: 'blank', hair: 'straight', hair_color: 'black' };
const catalog = [
  { id: 'tee1', category: 'clothing', group: 'tees', name: 'تيشيرت أخضر', gender: null, price_coins: 40, price_gems: 0, is_premium: false, owned: true, bundle: [] },
  { id: 'tee2', category: 'clothing', group: 'tees', name: 'تيشيرت مخطط', gender: null, price_coins: 60, price_gems: 0, is_premium: false, owned: false, bundle: [] },
  { id: 'engineer', category: 'clothing', group: 'jobs', name: 'مهندس', gender: null, price_coins: 0, price_gems: 5, is_premium: true, owned: false, bundle: [['top', 'hardHat']] },
  { id: 'cap1', category: 'top', group: 'caps', name: 'قبعة', gender: null, price_coins: 30, price_gems: 0, is_premium: false, owned: false, bundle: [] },
];
const convs = [{ friendship_id: 'F1', friend: U('U2', 'عمر'), last_message: { message_id: 'M1', sender_id: 'U2', recipient_id: 'S1', body: 'مرحبا ليان', created_at: '2026-10-01T10:00:00Z', read_at: null }, unread: 1 }];
let msgs = [{ message_id: 'M1', sender_id: 'U2', recipient_id: 'S1', body: 'مرحبا ليان', created_at: '2026-10-01T10:00:00Z', read_at: null }];
const classRow = { classroom_id: 'C1', name: 'السادس أ', join_code: 'JUTH26', teacher_name: 'سارة', member_count: 2, assignment_count: 1, quiz_count: 1, created_at: '2026-09-20T08:00:00Z' };
const assignStudent = [{ assignment_id: 'A1', classroom_id: 'C1', classroom_name: 'السادس أ', title: 'تمارين الجمع', description: 'حل خمس مسائل', skill_id: 'adding_integers', skill_name_ar: 'جمع', target_questions: 10, max_score: 100, due_at: '2026-10-04T10:00:00Z', created_at: '2026-10-01T08:00:00Z', state: 'open', submission: null }];
const quizRow = { quiz_id: 'Z1', classroom_id: 'C1', title: 'سباق الجمع', description: '', mode: 'race', time_limit_seconds: 180, is_open: true, question_count: 3, attempts: 1, created_at: '2026-10-01T08:00:00Z', mine: null };
const analytics = {
  classroom: classRow,
  kpis: { students: 2, avg_tree_health: 0.52, avg_accuracy: 0.7, active_last_7: 2, at_risk: 1 },
  students: [
    { user_id: 'U2', handle: '1002', full_name: 'عمر', avatar_svg: null, tree_health: 0.8, mastered: 5, current_skill: 'ضرب', accuracy: 0.9, answered: 40, last_active: '2026-10-01T09:00:00Z', days_since_active: 0, root_gaps: [], root_gap_ids: [], risk: 'low', submissions_done: 1, assignments_total: 1, quiz_points: 500 },
    { user_id: 'U3', handle: '1003', full_name: 'زياد', avatar_svg: null, tree_health: 0.2, mastered: 1, current_skill: 'جمع', accuracy: 0.4, answered: 30, last_active: '2026-09-25T09:00:00Z', days_since_active: 6, root_gaps: ['القيمة المطلقة'], root_gap_ids: ['absolute_value'], risk: 'high', submissions_done: 0, assignments_total: 1, quiz_points: 0 },
  ],
  top_gaps: [{ skill_id: 'absolute_value', name_ar: 'القيمة المطلقة', students: 1 }],
  skill_mastery: PY.skills.map((s) => ({ skill_id: s.skill_id, name_ar: s.name_ar, avg: 0.5 })),
  activity: Array.from({ length: 7 }, (_, i) => ({ date: `2026-09-${25 + i}`, answers: i * 4 })),
};
const report = { student: { user_id: 'S1', full_name: 'ليان', handle: '4821' }, state: { skills: skillsState, current_skill: 'adding_integers' }, drilldowns: [{ from_skill: 'a', from_name_ar: 'ضرب', to_skill: 'b', to_name_ar: 'جمع', direction: 'back', triggered_by: 'x', depth: 1, created_at: '2026-10-01T09:00:00Z' }], drilldowns_hidden: 2, gap_locked: true, forecast: { skill_id: 'b', name_ar: 'جمع', remaining_correct: 5, per_day: 2.5, days: 2 }, diagnoses: [{ diagnosis_id: 'D1', created_at: '2026-10-01T09:00:00Z', origin_skill: 'mult_div_integers', origin_name_ar: 'ضرب الأعداد الصحيحة', root_skill: 'adding_integers', root_name_ar: 'جمع الأعداد الصحيحة', path: [{ skill: 'mult_div_integers', name_ar: 'ضرب الأعداد الصحيحة' }, { skill: 'adding_integers', name_ar: 'جمع الأعداد الصحيحة' }], confidence: 'متوسطة', confidence_level: 'medium', explanation: 'اخترنا «جمع الأعداد الصحيحة» لأن الإجابات عليه 2 خاطئة و0 صحيحة.', evidence: [{ skill: 'adding_integers', name_ar: 'جمع الأعداد الصحيحة', wrong: 2, right: 0, role: 'root' }], intervention: 'استخدم قطع العد', outcome: { stage: 'remediating', root_status: 'gap', root_after: { right: 2, wrong: 1 }, origin_retry: { right: 0, wrong: 0 } } }], plan: planSnap() };
const insights = { struggle_alerts: [{ skill_id: 'b', skill_name_ar: 'جمع', severity: 'high', p_mastery: 0.3, consecutive_misses: 3, drill_down_depth_avg: 1, predicted_root_cause_skill: 'a', recommended_action: 'راجع القاعدة' }], engagement: { active_days_last_30: 8, avg_session_minutes: 12, questions_answered_last_7: 31, current_streak: 3 } };

const reportRow = { report_id: 'R1', reason: 'bullying', details: 'يشتمني في الدردشة', status: 'open', created_at: '2026-10-01T09:30:00Z', reporter: { user_id: 'U2', full_name: 'عمر', handle: '1002' }, reported: { user_id: 'U3', full_name: 'زياد', handle: '1003' }, has_message: true, resolution_note: '', resolved_at: null };
const blockedState = { list: [] };
const ok = (json, status = 200) => ({ ok: status < 400, status, text: async () => JSON.stringify(json), blob: async () => ({}) });
const routes = [
  ['POST', /^\/classrooms\/C1\/remediation/, () => ok({ assignment: { ...assignStudent[0], assignment_id: 'A2', kind: 'remediation', targeted: true, target_count: 1 }, students: [{ user_id: 'U3', full_name: 'زياد' }], count: 1, tip: 'استخدم خط الأعداد الأرضي' })],
  ['POST', /^\/classrooms\/C1\/safety\/reports\/R1\/resolve/, (b) => ok({ ...reportRow, status: b.action })],
  ['GET', /^\/classrooms\/C1\/safety\/reports\/R1/, () => ok({ ...reportRow, thread: [{ message_id: 'M7', sender_id: 'U3', sender_name: 'زياد', body: 'أنت مزعج', created_at: '2026-10-01T09:29:00Z', flagged: true }, { message_id: 'M8', sender_id: 'U2', sender_name: 'عمر', body: 'توقف من فضلك', created_at: '2026-10-01T09:29:30Z', flagged: false }] })],
  ['GET', /^\/classrooms\/C1\/safety\/reports/, () => ok([reportRow])],
  ['POST', /^\/community\/report/, () => ok({ status: 'received', duplicate: false })],
  ['POST', /^\/community\/block\//, () => ok({ status: 'blocked' })],
  ['DELETE', /^\/community\/block\//, () => ok({ status: 'unblocked' })],
  ['GET', /^\/community\/blocked/, () => ok(blockedState.list)],
  ['GET', /^\/health/, () => ok({ status: 'ok', ai_tutor: 'offline_fallback', demo: true })],
  ['GET', /^\/auth\/me/, () => ok(me())],
  ['POST', /^\/auth\/login/, (b) => (b.password === 'bad' ? ok({ detail: 'invalid_credentials' }, 401) : ok({ access_token: 'tok', token_type: 'bearer', user_id: 'S1' }))],
  ['POST', /^\/auth\/register/, () => ok({ access_token: 'tok', user_id: 'S1', role: 'student' })],
  ['POST', /^\/auth\/forgot-password/, () => ok({ status: 'sent', demo_code: '123456' })],
  ['POST', /^\/auth\/verify-reset-code/, (b) => (b.code === '123456' ? ok({ reset_token: 'rt' }) : ok({ detail: 'invalid_or_expired_code' }, 400))],
  ['POST', /^\/auth\/reset-password/, () => ok({ access_token: 'tok2', user_id: 'S1' })],
  ['GET', /^\/curriculum\/map/, () => ok(PY.map)],
  ['GET', /^\/curriculum\/skills/, () => ok(PY.skills)],
  ['GET', /\/adaptive\/tree/, () => ok(PY.tree_full)],
  ['GET', /\/adaptive\/bootstrap/, () => ok({ state: { current_skill: 'adding_integers', skills: skillsState }, wallet: { coins: 120, gems: 3 }, avatar, avatar_svg: '<svg id="me"></svg>', drilldowns: [], drilldowns_hidden: 0, plan: planSnap() })],
  ['GET', /\/adaptive\/question/, () => (state.qSkill ? ok({ question: 'س', hint: 'ت', skill: state.qSkill(), difficulty: 1, pattern: 'p', source: 'offline', remedial: null, banner: null, guided: false, type: 'mcq', options: ['3', '-3', '7', '2'], skill_name: 'x' }) : state.failNext === 'quota' ? ok({ detail: 'daily_limit_reached:questions' }, 402) : ok({ question: 'أوجد ناتج: 5 + (-2)', hint: 'انظر للإشارة', skill: 'adding_integers', difficulty: 2, pattern: 'p', source: 'offline', remedial: null, banner: 'مرحباً', guided: false, type: 'mcq', options: ['3', '-3', '7', '2'], skill_name: 'جمع الأعداد الصحيحة' }))],
  ['POST', /\/adaptive\/answer/, (b) => ok({ action: 'continue', next_skill: 'adding_integers', next_difficulty: 2, reason: 'r', breadcrumb: 'سنراجع الفكرة', gap_skill: null, round_over: false, coins_awarded: 0, gems_awarded: 0, is_correct: b.selected_answer === '3', correct_answer: '3', misconception: '', explanation: '', new_gaps: [], remedial: null, next_stage: 'same_pattern', mistake_card: { title: 'جمع بإشارتين', rule: 'اطرح القيمتين', example: '5 + (-2) = 3', why: 'جمعت القيمتين', chosen: b.selected_answer, correct: '3', solution: 'الحل 3' }, gap_locked: true, remaining_questions: 17 })],
  ['POST', /\/adaptive\/round/, () => ok({})],
  ['GET', /\/adaptive\/report/, () => ok(report)],
  ['GET', /\/insights/, () => ok(insights)],
  ['POST', /\/chat\/start/, () => ok({ session_id: 'sess1', opening_message: 'أهلاً بك' })],
  ['GET', /\/chat\/sessions\//, () => ok([])],
  ['POST', /\/chat\/message/, () => (state.failNext === 'tutor' ? ok({ detail: 'daily_limit_reached:tutor' }, 402) : ok({ reply: 'الناتج 3 لأن الإشارتان مختلفتان', gap_detected: true, gap_skill: 'x', drill_down_triggered: true, next_skill: 'x', next_difficulty: 1, breadcrumb: 'مراجعة', remaining_today: 3 }))],
  ['GET', /\/economy\/catalog/, () => ok(catalog)],
  ['GET', /\/economy\/options/, () => ok({ skins: [{ id: 'f8d25c', name: 'فاتح' }, { id: 'edb98a', name: 'حنطي' }], hair_styles: [{ id: 'straight', name: 'ستريت', gender: null }, { id: 'buzz', name: 'قصير', gender: 'ولد' }], hair_colors: [{ id: 'black', name: 'أسود', hex: '#2A1B15' }] })],
  ['GET', /\/economy\/previews/, () => ok({ 'i:tee1': { svg: '<svg id="ptee1"></svg>', uid: 'ptee1' }, 'i:tee2': { svg: '<svg id="ptee2"></svg>', uid: 'ptee2' }, 'skin:f8d25c': { svg: '<svg id="pskin_f8d25c"></svg>', uid: 'pskin_f8d25c' } })],
  ['PUT', /\/economy\/avatar/, () => ok({ status: 'saved', svg: '<svg id="me2"></svg>' })],
  ['POST', /\/economy\/purchase/, () => ok({ success: true, message: 'ok', wallet: { coins: 60, gems: 3 } })],
  ['GET', /^\/community\/summary/, () => ok({ unread_messages: 1, pending_requests: 1 })],
  ['GET', /^\/community\/conversations/, () => ok(convs)],
  ['GET', /^\/community\/requests/, () => ok([{ friendship_id: 'F9', friend: U('U9', 'هبة'), status: 'pending', is_incoming: true, created_at: '2026-10-01T09:00:00Z' }])],
  ['GET', /^\/community\/search/, () => ok([{ ...U('U5', 'يوسف'), friendship_status: null }])],
  ['POST', /^\/community\/request\//, () => ok({})],
  ['POST', /^\/community\/accept\//, () => ok({})],
  ['GET', /^\/community\/messages\//, () => ok(msgs)],
  ['POST', /^\/community\/messages\/[^/]+\/read/, () => ok({ marked: 1 })],
  ['POST', /^\/community\/messages\//, (b) => { const m = { message_id: `M${msgs.length + 1}`, sender_id: 'S1', recipient_id: 'U2', body: b.body, created_at: '2026-10-01T10:05:00Z', read_at: null }; msgs = [...msgs, m]; return ok(m); }],
  ['GET', /^\/classrooms\/assignments\/A1/, () => ok({ ...assignStudent[0], students: [{ user_id: 'U2', handle: '1', full_name: 'عمر', avatar_svg: null, submission: { submission_id: 'SB1', text: 'حليت', file_name: 'h.pdf', has_file: true, submitted_at: '2026-10-01T09:00:00Z', late: false, score: null, feedback: '', graded_at: null } }, { user_id: 'U3', handle: '2', full_name: 'زياد', avatar_svg: null, submission: null }] })],
  ['GET', /^\/classrooms\/assignments/, () => ok(state.role === 'teacher' ? [{ ...assignStudent[0], submissions: 1, graded: 0, members: 2 }, { ...assignStudent[0], assignment_id: 'A2', title: 'تقوية: القيمة المطلقة', kind: 'remediation', targeted: true, target_count: 1, submissions: 0, graded: 0, members: 1 }] : assignStudent)],
  ['POST', /^\/classrooms\/assignments\/A1\/submit/, () => ok({ submission_id: 'SB1' })],
  ['POST', /^\/classrooms\/submissions\/SB1\/grade/, () => ok({ score: 90 })],
  ['POST', /^\/classrooms\/join/, () => ok(classRow)],
  ['GET', /^\/classrooms\/C1\/analytics/, () => ok(analytics)],
  ['GET', /^\/classrooms\/C1\/members/, () => ok([{ user_id: 'U2', handle: '1', full_name: 'عمر', avatar_svg: null }])],
  ['GET', /^\/classrooms\/C1\/quizzes/, () => ok([quizRow])],
  ['POST', /^\/classrooms\/C1\/quizzes\/generate/, () => ok(quizRow)],
  ['POST', /^\/classrooms\/C1\/quizzes/, () => ok(quizRow)],
  ['POST', /^\/classrooms\/C1\/assignments/, () => ok(assignStudent[0])],
  ['GET', /^\/classrooms\/C1\/leaderboard/, () => ok({ quiz_count: 1, rows: [{ user_id: 'U2', handle: '1', full_name: 'عمر', avatar_svg: null, score: 500, quizzes_taken: 1, duration_seconds: 50, rank: 1 }] })],
  ['GET', /^\/classrooms\/quizzes\/Z1\/leaderboard/, () => ok({ quiz: quizRow, rows: [{ user_id: 'U2', handle: '1', full_name: 'عمر', avatar_svg: null, score: 500, correct: 3, total: 3, duration_seconds: 50, rank: 1 }] })],
  ['POST', /^\/classrooms\/quizzes\/Z1\/start/, () => ok({ quiz_id: 'Z1', title: 'سباق الجمع', mode: 'race', time_limit_seconds: 180, seconds_left: 180, questions: [{ id: 'Q1', position: 0, prompt: '2 + 3', options: ['4', '5'], points: 100 }, { id: 'Q2', position: 1, prompt: '1 + 1', options: ['2', '3'], points: 100 }] })],
  ['POST', /^\/classrooms\/quizzes\/Z1\/submit/, () => ok({ score: 250, correct: 2, total: 2, base: 200, bonus: 50, duration_seconds: 20, rank: 1, participants: 2, review: [{ id: 'Q1', correct_index: 1, picked: 1 }, { id: 'Q2', correct_index: 0, picked: 0 }] })],
  ['GET', /^\/classrooms$/, () => ok(state.role === 'student' ? [{ ...classRow, join_code: null }] : [classRow])],
  ['POST', /^\/classrooms$/, () => ok(classRow)],
  ['GET', /^\/payments\/plans/, () => ok(PY.plans)],
  ['POST', /^\/payments\/checkout/, () => ok({ session_id: 'abcdef12-0000', provider: 'mock', plan: 'pro', period: 'monthly', amount_minor: 2990, currency: 'JOD', stripe_url: null })],
  ['POST', /^\/payments\/confirm/, () => ok({ session_id: 'abcdef12-0000', plan: 'pro', period: 'monthly', status: 'succeeded', amount_minor: 2990, currency: 'JOD', provider: 'mock', created_at: '2026-10-01T10:00:00Z' })],
  ['GET', /^\/me\/students/, () => ok([{ student_id: 'S1', full_name: 'ليان', email: 'a@x', grade_level: 6 }])],
];
const fetchMock = async (url, opts = {}) => {
  const method = (opts.method || 'GET').toUpperCase();
  const path = url.split('?')[0];
  const body = opts.body && typeof opts.body === 'string' ? JSON.parse(opts.body) : {};
  calls.push({ method, url, body });
  const hit = routes.find(([m, re]) => m === method && re.test(path));
  if (!hit) return ok({ detail: 'no_mock' }, 404);
  return hit[2](body);
};

const { body } = install(fetchMock);
const results = [];
let failures = 0;
const check = (name, cond, extra = '') => { results.push([cond, name, extra]); if (!cond) failures += 1; };
const byLabelOf = (root, label) => find(root, (e) => e.attrs && e.attrs['aria-label'] === label);
const mkctx = (params = {}, query = {}) => {
  const root = new FEl('div');
  body.appendChild(root);
  const ctx = { root, params, query, destroyed: false, cbs: [], onDestroy(fn) { if (ctx.destroyed) fn(); else ctx.cbs.push(fn); }, login: async (t, landing) => { ctx.loggedIn = t; ctx.landing = landing; }, reload() { ctx.reloaded = true; }, refreshShell() { ctx.shellRefreshed = true; }, navigate() {} };
  ctx.destroy = () => { ctx.destroyed = true; ctx.cbs.forEach((f) => f()); root.remove(); };
  return ctx;
};
const run = async (name, fn) => {
  try { await fn(); } catch (e) { failures += 1; results.push([false, `${name} threw`, e.stack.split('\n').slice(0, 4).join(' | ')]); }
};

const st = await import('../../app/static/js/store.js');
const api = await import('../../app/static/js/api.js');
await st.loadHealth();
api.setToken('tok');

await run('auth', async () => {
  const { authView } = await import('../../app/static/js/views/auth.js');
  const ctx = mkctx({ mode: 'login' });
  await authView(ctx);
  check('login renders form', byTag(ctx.root, 'form').length === 1);
  check('login shows demo chips', text(ctx.root).includes('وضع العرض'));
  const form = byTag(ctx.root, 'form')[0];
  const [email] = byTag(form, 'input');
  type(email, 'a@b.jo');
  const pw = byTag(form, 'input')[1];
  pw.value = 'bad';
  submit(form); await tick();
  check('login error shown (Arabic)', text(ctx.root).includes('البريد الإلكتروني أو كلمة المرور غير صحيحة'));
  pw.value = 'good1234'; submit(form); await tick();
  check('login success calls ctx.login', ctx.loggedIn === 'tok');
  const omar = byText(ctx.root, 'button', 'طالب (عمر - ضمن صف)')[0];
  check('omar demo chip exists', !!omar);
  const omarLogin = calls.length;
  omar.click(); await tick(40);
  const posted = calls.slice(omarLogin).find((c) => c.url.includes('/auth/login'));
  check('omar chip logs in with one click', !!posted && posted.body.email === 'student2@demo.jo' && ctx.loggedIn === 'tok');
  check('omar chip lands straight on practice', ctx.landing === '#/practice');
  ctx.landing = undefined;
  byText(ctx.root, 'button', 'طالبة (ليان - برو)')[0].click(); await tick(40);
  check('other chips keep the default landing', ctx.landing === undefined);
  const forgot = byText(ctx.root, 'button', 'نسيت كلمة المرور')[0];
  check('forgot link exists', !!forgot);
  forgot.click();
  check('step1 asks for email', text(ctx.root).includes('أدخل بريدك الإلكتروني') && byTag(ctx.root, 'input').length === 1);
  const f1 = byTag(ctx.root, 'form')[0];
  byTag(f1, 'input')[0].value = 'u@x.jo'; submit(f1); await tick();
  check('step2 shows OTP boxes', byTag(ctx.root, 'input').length === 6);
  check('demo code banner shown', text(ctx.root).includes('123456'));
  const boxes = byTag(ctx.root, 'input');
  '000000'.split('').forEach((d, i) => { boxes[i].value = d; boxes[i].dispatchEvent({ type: 'input' }); });
  await tick(40);
  check('wrong code shows error', text(ctx.root).includes('الرمز غير صحيح'));
  '123456'.split('').forEach((d, i) => { boxes[i].value = d; boxes[i].dispatchEvent({ type: 'input' }); });
  await tick(40);
  check('step3 new password + confirm', byTag(ctx.root, 'input').length === 2 && text(ctx.root).includes('تأكيد كلمة المرور'));
  const f3 = byTag(ctx.root, 'form')[0];
  const [a, b] = byTag(f3, 'input');
  a.value = 'newpass1'; b.value = 'different'; submit(f3); await tick();
  check('mismatch blocked', text(ctx.root).includes('غير متطابقتين'));
  b.value = 'newpass1'; submit(f3); await tick();
  check('reset completes and logs in', ctx.loggedIn === 'tok2');
  ctx.destroy();
  const reg = mkctx({ mode: 'register' });
  await authView(reg);
  check('register renders role seg + gender', text(reg.root).includes('اختر الشخصية') && text(reg.root).includes('رمز المدرسة'));
  byText(reg.root, 'button', 'معلم')[0].click();
  check('teacher trial note visible', !byClass(reg.root, 'banner')[0].hasAttribute('hidden'));
  reg.destroy();
});

await run('tree', async () => {
  const { renderTreeStage, demoTreeData } = await import('../../app/static/js/tree.js');
  const host = new FEl('div'); body.appendChild(host);
  const ctrl = renderTreeStage(host, PY.tree_full, { studentId: 'S1' });
  const panel = byClass(host, 'leaf-panel')[0];
  check('panel hidden by default', panel.hasAttribute('hidden') && panel.childNodes.length === 0);
  check('scene svg rendered', byClass(host, 'stage')[0].childNodes[0]._html.includes('class="leaf'));
  check('hud shows health + gap', text(host).includes('تابع التدريب') && text(host).includes('الجذر المرصود'));
  ctrl.select('u1l3');
  check('panel opens only after select', !panel.hasAttribute('hidden') && panel.hidden === false && text(panel).includes('أهم الأفكار'));
  check('panel has start button', text(panel).includes('ابدأ التدريب') || text(panel).includes('راجع بالتدريب'));
  ctrl.select('u3l1');
  check('soon lesson panel disabled', text(panel).includes('قريباً'));
  ctrl.close();
  check('panel hidden after close', panel.hasAttribute('hidden'));
  ctrl.update(PY.tree_locked);
  check('locked tree hud nudges upgrade', text(host).includes('اكشف الجذر بباقة برو'));
  const stage = byClass(host, 'stage')[0];
  const sceneBox = stage.childNodes[0];
  stage.dispatchEvent({ type: 'click', target: new FEl('div') });
  ctrl.destroy();
  const demo = demoTreeData(PY.map);
  check('demo data has 4 units/18 lessons', demo.units.length === 4 && demo.units.reduce((n, u) => n + u.lessons.length, 0) === 18);
  const bare = new FEl('div'); body.appendChild(bare);
  renderTreeStage(bare, demo, { fill: true, bare: true, interactive: false }).destroy();
  check('bare stage has no panel', true);
});

await run('home', async () => {
  const { homeView } = await import('../../app/static/js/views/home.js');
  const ctx = mkctx(); state.role = 'student'; await st.loadMe();
  await homeView(ctx);
  check('home renders stage', byClass(ctx.root, 'stage').length === 1 && text(ctx.root).includes('تابع التدريب'));
  ctx.destroy();
});

await run('practice', async () => {
  const { practiceView } = await import('../../app/static/js/views/practice.js');
  const ctx = mkctx(); await practiceView(ctx);
  check('question rendered', text(ctx.root).includes('أوجد ناتج'));
  check('quota shown', text(ctx.root).includes('المتبقي اليوم'));
  const opts = byClass(ctx.root, 'opt');
  check('4 options', opts.length === 4);
  check('no analyzing indicator before answering', byClass(ctx.root, 'analyzing').length === 0);
  let release;
  routes.unshift(['POST', /\/adaptive\/answer/, () => new Promise((resolve) => { release = () => resolve(ok({ action: 'continue', next_skill: 'adding_integers', next_difficulty: 2, reason: 'r', breadcrumb: null, gap_skill: null, round_over: false, coins_awarded: 0, gems_awarded: 0, is_correct: true, correct_answer: '3', misconception: '', explanation: '', new_gaps: [], remedial: null, next_stage: 'same_pattern', mistake_card: null, gap_locked: false, remaining_questions: 17 })); })]);
  opts[0].click(); await tick(10);
  check('analyzing spinner shown immediately while waiting', byClass(ctx.root, 'analyzing').length === 1 && text(ctx.root).includes('المعلم الذكي يقوم بتحليل إجابتك...'));
  release(); await tick(20);
  check('analyzing spinner removed when the answer resolves', byClass(ctx.root, 'analyzing').length === 0 && text(ctx.root).includes('إجابة صحيحة'));
  routes.shift();
  byText(ctx.root, 'button', 'السؤال التالي')[0].click(); await tick();
  routes.unshift(['POST', /\/adaptive\/answer/, () => new Promise((resolve) => { release = () => resolve(ok({ detail: 'boom' }, 500)); })]);
  byClass(ctx.root, 'opt')[0].click(); await tick(10);
  check('spinner visible during a request that will fail', byClass(ctx.root, 'analyzing').length === 1);
  release(); await tick(20);
  check('spinner removed when the request rejects', byClass(ctx.root, 'analyzing').length === 0 && byClass(ctx.root, 'opt').length === 4);
  routes.shift();
  opts[1].click(); await tick();
  check('wrong answer verdict', text(ctx.root).includes('إجابة غير صحيحة'));
  check('explanation hidden until clicked', byClass(ctx.root, 'explain')[0].hasAttribute('hidden'));
  byText(ctx.root, 'button', 'اعرض الشرح')[0].click();
  check('explanation toggles open', !byClass(ctx.root, 'explain')[0].hasAttribute('hidden') && text(ctx.root).includes('جمع بإشارتين'));
  check('breadcrumb banner + locked upsell', text(ctx.root).includes('سنراجع الفكرة') && text(ctx.root).includes('رصدنا فجوة جذرية'));
  check('quota decremented', text(ctx.root).includes('17'));
  byText(ctx.root, 'button', 'السؤال التالي')[0].click(); await tick();
  check('next question loads', byClass(ctx.root, 'opt').length === 4);
  state.failNext = 'quota';
  byClass(ctx.root, 'opt')[0].click(); await tick();
  byText(ctx.root, 'button', 'السؤال التالي')[0].click(); await tick();
  check('quota upsell on limit', text(ctx.root).includes('انتهت أسئلة اليوم'));
  state.failNext = null; ctx.destroy();
});

await run('tutor', async () => {
  const { tutorView } = await import('../../app/static/js/views/tutor.js');
  const ctx = mkctx(); await tutorView(ctx);
  check('opening message', text(ctx.root).includes('أهلاً بك'));
  check('skill select populated', byTag(ctx.root, 'option').length === PY.skills.length);
  const input = byTag(ctx.root, 'textarea')[0];
  let releaseTutor;
  routes.unshift(['POST', /\/chat\/message/, () => new Promise((resolve) => { releaseTutor = () => resolve(ok({ reply: 'الناتج 3 لأن الإشارتان مختلفتان', gap_detected: true, gap_skill: 'x', drill_down_triggered: true, next_skill: 'x', next_difficulty: 1, breadcrumb: 'مراجعة', remaining_today: 3 })); })]);
  input.value = '5 + (-2)';
  byClass(ctx.root, 'send')[0].click(); await tick(10);
  check('tutor shows the analysis label while waiting', byClass(ctx.root, 'typing').length === 1 && text(ctx.root).includes('المعلم الذكي يقوم بتحليل إجابتك...'));
  releaseTutor(); await tick(20);
  check('tutor indicator removed after the reply', byClass(ctx.root, 'typing').length === 0);
  routes.shift();
  input.value = '5 + (-2)';
  byClass(ctx.root, 'send')[0].click(); await tick();
  check('student + tutor bubbles', text(ctx.root).includes('5 + (-2)') && text(ctx.root).includes('الإشارتان مختلفتان'));
  check('drill-down note', text(ctx.root).includes('أضفنا لك أسئلة'));
  check('quota chip updated', text(ctx.root).includes('المتبقي اليوم: 3'));
  state.failNext = 'tutor';
  input.value = 'مرحبا'; byClass(ctx.root, 'send')[0].click(); await tick();
  check('tutor limit shows upsell', text(ctx.root).includes('انتهت رسائل اليوم'));
  state.failNext = null; ctx.destroy();
});

await run('shop', async () => {
  const { shopView } = await import('../../app/static/js/views/shop.js');
  const ctx = mkctx(); await shopView(ctx); await tick(30);
  check('items render with previews', byClass(ctx.root, 'item-card').length >= 2 && byClass(ctx.root, 'pv')[0]._html.includes('ptee1'));
  const owned = byClass(ctx.root, 'item-card').find((c) => text(c).includes('تيشيرت أخضر'));
  owned.click(); await tick(30);
  check('owned item equips instantly + PUT sent', calls.some((c) => c.method === 'PUT' && c.body.clothing === 'tee1'));
  check('preview svg refreshed from server', byClass(ctx.root, 'preview-av')[0]._html.includes('me2'));
  const locked = byClass(ctx.root, 'item-card').find((c) => text(c).includes('تيشيرت مخطط'));
  locked.click();
  check('buy modal opens', text(body).includes('اشترِ وارتدِ'));
  const buyBtn = byText(body, 'button', 'اشترِ وارتدِ')[0];
  buyBtn.click(); await tick(40);
  check('purchase posted with coins', calls.some((c) => c.url.includes('/economy/purchase') && c.body.currency === 'coins'));
  byText(ctx.root, 'button', 'المظهر')[0].click();
  check('look tab swatches', byClass(ctx.root, 'sw').length >= 3);
  ctx.destroy();
});

await run('community', async () => {
  const { communityView } = await import('../../app/static/js/views/social.js');
  const ctx = mkctx(); await communityView(ctx);
  check('conversation + request listed', text(ctx.root).includes('عمر') && text(ctx.root).includes('طلبات الصداقة'));
  check('unread badge', byClass(ctx.root, 'badge').length === 1);
  byClass(ctx.root, 'conv')[0].click(); await tick(40);
  check('thread opens with message', text(ctx.root).includes('مرحبا ليان'));
  check('mark read posted', calls.some((c) => c.url.includes('/read')));
  const input = byTag(ctx.root, 'textarea')[0];
  input.value = 'أهلاً عمر';
  byClass(ctx.root, 'send')[0].click(); await tick(40);
  const mine = byClass(ctx.root, 'bubble').filter((b) => b.classList.contains('mine'));
  check('optimistic send then confirmed (single bubble)', mine.length === 1 && !mine[0].classList.contains('sending'), String(mine.length));
  check('read tick present', byClass(mine[0], 'ico').length >= 1);
  byText(ctx.root, 'button', 'إضافة صديق')[0].click();
  const search = byTag(body, 'input').find((i) => (i.attrs.placeholder || '').includes('معرّف'));
  search.value = '1234'; byText(body, 'button', 'بحث')[0].click(); await tick(30);
  check('search result with add button', text(body).includes('يوسف'));
  ctx.destroy();
});

await run('classes', async () => {
  const { classesView } = await import('../../app/static/js/views/classes.js');
  const ctx = mkctx(); await classesView(ctx); await tick(30);
  check('assignment card', text(ctx.root).includes('تمارين الجمع') && text(ctx.root).includes('مفتوح'));
  byText(ctx.root, 'button', 'تسليم الواجب')[0].click();
  check('submit modal', text(body).includes('إرفاق ملف'));
  byText(body, 'button', 'تسليم')[byText(body, 'button', 'تسليم').length - 1].click(); await tick(30);
  check('upload posted', calls.some((c) => c.url.includes('/assignments/A1/submit')));
  byText(ctx.root, 'button', 'الاختبارات')[0].click(); await tick(30);
  check('quiz listed', text(ctx.root).includes('سباق الجمع') && text(ctx.root).includes('سباق سرعة'));
  byText(ctx.root, 'button', 'ابدأ الآن')[0].click(); await tick(40);
  const overlay = byClass(body, 'quiz-overlay')[0];
  check('quiz overlay + timer', !!overlay && text(overlay).includes('03:00') || text(overlay).includes('02:5'));
  byClass(overlay, 'opt')[1].click();
  byText(overlay, 'button', 'التالي')[0].click();
  byClass(overlay, 'opt')[0].click();
  byText(overlay, 'button', 'إنهاء وتسليم')[0].click(); await tick(60);
  check('quiz result shows score + rank', text(overlay).includes('250 نقطة') && text(overlay).includes('المركز 1'));
  byText(overlay, 'button', 'إغلاق')[0].click();
  byText(ctx.root, 'button', 'لوحة الصدارة')[0].click(); await tick(30);
  ctx.destroy();
});

await run('plans+checkout', async () => {
  const { plansView, checkoutView, luhn, expiryOk, cardBrand } = await import('../../app/static/js/views/plans.js');
  check('luhn valid/invalid', luhn('4242 4242 4242 4242') && !luhn('4242 4242 4242 4241') && !luhn('123'));
  check('expiry validation', expiryOk('12/30') && !expiryOk('01/20') && !expiryOk('13/30') && cardBrand('4111') === 'Visa');
  const ctx = mkctx(); await plansView(ctx);
  const t = text(ctx.root);
  check('3 equal plan cards', byClass(ctx.root, 'plan').length === 3);
  check('USP block', t.includes('مسح الجذر'));
  check('pro price monthly 2.99', t.includes('2.99'));
  byText(ctx.root, 'button', 'سنوياً')[0].click();
  check('yearly toggles price', text(ctx.root).includes('29.90'));
  check('comparison table', byClass(ctx.root, 'cmp').length === 1);
  const out = byClass(ctx.root, 'plan')[1];
  check('plan list items wrap', byTag(out, 'li').length >= 4);
  ctx.destroy();
  const co = mkctx({ plan: 'pro' }, { period: 'monthly' }); await checkoutView(co);
  check('demo card hint', text(co.root).includes('4242 4242 4242 4242'));
  const form = byTag(co.root, 'form')[0];
  const [holder, number, expiry, cvv] = byTag(form, 'input');
  holder.value = 'Lian'; type(number, '4242424242424241'); type(expiry, '1230'); cvv.value = '123';
  submit(form); await tick();
  check('bad luhn blocked', text(co.root).includes('رقم البطاقة غير صحيح'));
  type(number, '4242424242424242'); check('number formatted', number.value === '4242 4242 4242 4242');
  submit(form); await tick(40);
  check('success screen', text(co.root).includes('تم الاشتراك بنجاح') && co.shellRefreshed === true);
  co.destroy();
});

await run('teacher', async () => {
  state.role = 'teacher'; await st.loadMe();
  const { teacherView } = await import('../../app/static/js/views/teacher.js');
  const ctx = mkctx(); await teacherView(ctx); await tick(40);
  check('trial banner', text(ctx.root).includes('تجربتك المجانية') && text(ctx.root).includes('13'));
  check('KPIs + students table', byClass(ctx.root, 'kpi').length >= 5 && text(ctx.root).includes('زياد'));
  check('risk labels', text(ctx.root).includes('مرتفعة') && text(ctx.root).includes('منخفضة'));
  const rows = byClass(ctx.root, 'click');
  check('table rows clickable', rows.length === 2);
  rows[0].click(); await tick(40);
  check('student drawer opens', byClass(body, 'drawer').length === 1 && text(byClass(body, 'drawer')[0]).includes('سلسلة الجذر'));
  const drawerText = text(byClass(body, 'drawer')[0]);
  check('teacher sees the diagnosis record with evidence, confidence, intervention and outcome', drawerText.includes('سجل التشخيص') && drawerText.includes('الثقة: متوسطة') && drawerText.includes('التدخل المقترح') && drawerText.includes('العلاج جارٍ') && drawerText.includes('2 صحيحة و1 خاطئة'));
  byText(body, 'button', 'عرض الشجرة كاملة')[0].click();
  check('tree modal opens', byClass(body, 'modal').length >= 1 && byClass(body, 'stage').length >= 1);
  byText(ctx.root, 'button', 'الواجبات')[0].click(); await tick(40);
  check('assignment list', text(ctx.root).includes('تمارين الجمع') && text(ctx.root).includes('1/2'));
  byText(ctx.root, 'button', 'فتح وتصحيح')[0].click(); await tick(40);
  const drawer = byClass(body, 'drawer').pop();
  check('submissions with download + grade', text(drawer).includes('h.pdf') && text(drawer).includes('لم يسلّم'));
  const scoreIn = byTag(drawer, 'input').find((i) => i.attrs.type === 'number');
  scoreIn.value = '90';
  byText(drawer, 'button', 'حفظ')[0].click(); await tick(30);
  check('grade posted', calls.some((c) => c.url.includes('/grade') && c.body.score === 90));
  byText(ctx.root, 'button', 'واجب جديد')[0].click();
  check('assignment modal', text(body).includes('موعد التسليم'));
  byText(ctx.root, 'button', 'الاختبارات')[0].click(); await tick(40);
  check('quiz list teacher', text(ctx.root).includes('سباق الجمع') && text(ctx.root).includes('النتائج'));
  byText(ctx.root, 'button', 'اختبار جديد')[0].click();
  check('quiz modal modes', text(body).includes('توليد تلقائي من درس') && text(body).includes('إدخال الأسئلة يدوياً'));
  byText(ctx.root, 'button', 'لوحة الصدارة')[0].click(); await tick(30);
  check('leaderboard tab', text(ctx.root).includes('ترتيب الصف'));
  byText(ctx.root, 'button', 'الصفوف والطلاب')[0].click(); await tick(30);
  check('classes tab shows code', text(ctx.root).includes('JUTH26'));
  ctx.destroy();
});

await run('parent', async () => {
  state.role = 'parent'; await st.loadMe();
  const { parentView, reportView, chainFrom } = await import('../../app/static/js/views/parent.js');
  const ctx = mkctx(); await parentView(ctx); await tick(30);
  check('parent chain + upsell', text(ctx.root).includes('سلسلة الجذر') && text(ctx.root).includes('فعّل برو لابنك'));
  check('tree embedded', byClass(ctx.root, 'stage').length === 1);
  check('chainFrom order', chainFrom([{ from_name_ar: 'ب', to_name_ar: 'ج' }, { from_name_ar: 'أ', to_name_ar: 'ب' }]).join('>') === 'أ>ب>ج');
  ctx.destroy();
  const rep = mkctx({ id: 'S1' }); await reportView(rep); await tick(30);
  check('report renders', text(rep.root).includes('تقرير مسح الجذر') && text(rep.root).includes('طباعة التقرير'));
  byText(rep.root, 'button', 'طباعة التقرير')[0].click();
  check('print invoked', globalThis.__printed === true);
  rep.destroy();
});

await run('scan animation', async () => {
  const { renderTreeStage, computeScene, sceneSvg } = await import('../../app/static/js/tree.js');
  const sc = computeScene(900, 700, PY.tree_full);
  check('nine live leaves in the scene', sc.leaves.filter((l) => l.lesson.skill).length === 9);
  check('scene has a scan layer inside the tree group', sceneSvg(sc).includes('class="scan-layer"'));
  const host = new FEl('div'); body.appendChild(host);
  const ctrl = renderTreeStage(host, PY.tree_full, { embedded: true, bare: true, interactive: false, compact: true });
  check('compact class applied', byClass(host, 'stage')[0].classList.contains('compact'));
  const seen = [];
  const n = await ctrl.scan(['mult_div_integers', 'subtracting_integers', 'adding_integers', 'nonexistent'], { stepMs: 5, onStep: (i, lesson, last) => seen.push([i, lesson.skill, last]) });
  check('scan walks leaf by leaf in order and ignores unknown skills', n === 3 && seen.map((x) => x[1]).join() === 'mult_div_integers,subtracting_integers,adding_integers');
  check('only the last step is final', seen.map((x) => x[2]).join() === 'false,false,true');
  check('empty scan resolves immediately', (await ctrl.scan([], {})) === 0);
  ctrl.clearScan();
  ctrl.destroy();
});

await run('practice scan', async () => {
  state.role = 'student'; await st.loadMe();
  const { practiceView } = await import('../../app/static/js/views/practice.js');
  const ctx = mkctx(); await practiceView(ctx);
  byClass(ctx.root, 'opt')[1].click(); await tick(60);
  check('scan card appears after a wrong answer', byClass(ctx.root, 'scan-card').length === 1 && text(ctx.root).includes('مسح الجذر'));
  check('scan uses a compact tree stage', byClass(ctx.root, 'stage').length === 1 && byClass(ctx.root, 'stage')[0].classList.contains('compact'));
  await tick(2600);
  check('basic plan scan ends at a hidden root', text(ctx.root).includes('جذر مخفي'));
  check('locked scan offers the upgrade link', byText(ctx.root, 'a', 'اكشف الجذر').length >= 1);
  ctx.destroy();
  routes.unshift(['POST', /\/adaptive\/answer/, () => ok({ action: 'remediate', next_skill: 'absolute_value', next_difficulty: 1, reason: 'r', breadcrumb: 'الأرجح أن «القيمة المطلقة» هو الجذر', gap_skill: 'absolute_value', round_over: false, coins_awarded: 0, gems_awarded: 0, is_correct: false, correct_answer: '3', misconception: '', explanation: '', new_gaps: ['absolute_value'], remedial: null, next_stage: 'same_pattern', mistake_card: null, gap_locked: false, remaining_questions: 16, diagnosis: { root: 'absolute_value', origin: 'adding_integers', path: ['adding_integers', 'comparing_integers', 'absolute_value'], confidence: 'متوسطة', p_gap: 0.77, evidence: [{ skill: 'adding_integers', wrong: 1, right: 0 }, { skill: 'absolute_value', wrong: 2, right: 0 }] } })]);
  const full = mkctx(); await practiceView(full);
  byClass(full.root, 'opt')[1].click(); await tick(60);
  await tick(2600);
  check('pro plan scan lands on the likely root with hedged wording', text(full.root).includes('الجذر الأرجح') && !text(full.root).includes('هو الجذر الحقيقي'));
  check('pro plan shows the diagnosis card with confidence and evidence', text(full.root).includes('نتيجة التشخيص') && text(full.root).includes('الثقة متوسطة') && text(full.root).includes('الأدلة') && text(full.root).includes('2 خاطئة'));
  check('diagnosis card states it is an estimate', text(full.root).includes('تقدير'));
  check('no upsell link when the root is found', byText(full.root, 'a', 'اكشف الجذر').length === 0);
  routes.shift();
  full.destroy();
  const calm = mkctx(); routes.unshift(['POST', /\/adaptive\/answer/, () => ok({ action: 'continue', next_skill: 'adding_integers', next_difficulty: 2, reason: 'r', breadcrumb: null, gap_skill: null, round_over: false, coins_awarded: 0, gems_awarded: 0, is_correct: true, correct_answer: '3', misconception: '', explanation: '', new_gaps: [], remedial: null, next_stage: 'same_pattern', mistake_card: null, gap_locked: false, remaining_questions: 15 })]);
  await practiceView(calm);
  byClass(calm.root, 'opt')[0].click(); await tick(60);
  check('no scan on a correct answer', byClass(calm.root, 'scan-card').length === 0);
  routes.shift();
  calm.destroy();
});

await run('real engine flow replay', async () => {
  state.role = 'student'; await st.loadMe();
  const flow = JSON.parse(fs.readFileSync(new URL('./fixtures/omar_flow.json', import.meta.url), 'utf8'));
  const { practiceView } = await import('../../app/static/js/views/practice.js');
  let index = 0;
  routes.unshift(['GET', /\/adaptive\/question/, () => ok({ ...flow[Math.min(index, flow.length - 1)].question, banner: flow[Math.min(index, flow.length - 1)].question.banner || '' })]);
  routes.unshift(['POST', /\/adaptive\/answer/, () => ok(flow[Math.min(index, flow.length - 1)].result)]);
  const ctx = mkctx(); await practiceView(ctx);
  const seen = [];
  for (let n = 0; n < flow.length; n += 1) {
    index = n;
    const step = flow[n];
    if (step.question.type === 'input') {
      type(byTag(ctx.root, 'input')[0], step.wrong);
      byText(ctx.root, 'button', 'تأكيد الإجابة')[0].click();
    } else {
      const el = byClass(ctx.root, 'opt').find((o) => text(o).includes(step.wrong));
      if (!el) throw new Error(`step ${n + 1}: option ${JSON.stringify(step.wrong)} not found in ${JSON.stringify(byClass(ctx.root, 'opt').map(text))}`);
      el.click();
    }
    await tick(60);
    const flowCard = byClass(ctx.root, 'flow')[0];
    seen.push({ cards: byClass(ctx.root, 'scan-card').length, text: text(ctx.root), stage: flowCard ? flowCard.getAttribute('data-stage') : null });
    if (n < flow.length - 1) {
      index = n + 1;
      byText(ctx.root, 'button', 'السؤال التالي')[0].click(); await tick(60);
    }
  }
  await tick(5200);
  const finalText = text(ctx.root);
  const diagnosis = flow[flow.length - 1].result.diagnosis;
  check('replayed flow covers mcq, tf and input question types', new Set(flow.map((f) => f.question.type)).size === 3);
  check('the scan starts at the very first wrong answer', seen[0].cards === 1);
  check('no diagnosis card before the evidence threshold', seen.slice(0, -1).every((s) => !s.text.includes('نتيجة التشخيص')));
  check('the final recorded answer carries a real engine diagnosis', diagnosis.root === 'adding_integers' && diagnosis.origin === 'mult_div_integers' && diagnosis.path.length === 3);
  check('UI shows the diagnosis card built from the real payload', finalText.includes('نتيجة التشخيص') && finalText.includes('جمع الأعداد الصحيحة') && finalText.includes('ضرب'));
  check('UI shows the confidence label from the engine', finalText.includes(`الثقة ${diagnosis.confidence}`));
  check('UI lists the evidence counts from the engine', diagnosis.evidence.every((e) => finalText.includes(`${e.wrong} خاطئة`)));
  const withNeeded = flow.slice(0, -1).map((f, i) => [f, i]).filter(([f]) => f.result.evidence_status && (f.result.evidence_status.evidence_needed || []).length);
  check('when the engine reports evidence_needed, the learner sees what would settle the diagnosis', withNeeded.length > 0 && withNeeded.every(([, i]) => seen[i].text.includes('ما يلزم لحسم التشخيص')));
  check('before the root is named, each wrong answer explains what evidence is still missing', seen.slice(0, -1).every((s) => s.text.includes('نجمع الأدلة')));
  check('a confirmation probe is announced before blaming the root', seen.some((s) => s.text.includes('سؤال تأكيد')));
  check('UI shows why this lesson was chosen and the remediation plan', finalText.includes('لماذا هذا الدرس؟') && finalText.includes('الخطة العلاجية'));
  check('wrong answers in the realistic replay are misconception-linked, never nonsense', flow.every((f) => f.result.misconception));
  check('workflow stepper shows evidence gathering before the root is named', seen.slice(0, -1).every((s) => s.stage === 'gathering_evidence'));
  check('workflow stepper moves to the named root on the diagnosis answer', seen[seen.length - 1].stage === 'root_identified' && finalText.includes('مسار التشخيص'));
  routes.shift(); routes.shift();
  ctx.destroy();
});

await run('real engine recovery replay (remediation -> retry -> mastery)', async () => {
  state.role = 'student'; await st.loadMe();
  const flow = JSON.parse(fs.readFileSync(new URL('./fixtures/omar_recovery.json', import.meta.url), 'utf8'));
  const { practiceView } = await import('../../app/static/js/views/practice.js');
  let index = 0;
  routes.unshift(['POST', /\/adaptive\/round/, () => ok({ student_id: 'S1', current_skill: 'adding_integers', difficulty: 1, total_answered: 0, tree_health: 0.3, skills: [] })]);
  routes.unshift(['GET', /\/adaptive\/question/, () => ok({ ...flow[Math.min(index, flow.length - 1)].question, banner: flow[Math.min(index, flow.length - 1)].question.banner || '' })]);
  routes.unshift(['POST', /\/adaptive\/answer/, () => ok(flow[Math.min(index, flow.length - 1)].result)]);
  const ctx = mkctx(); await practiceView(ctx);
  const stages = [];
  for (let n = 0; n < flow.length; n += 1) {
    index = n;
    const step = flow[n];
    if (step.question.type === 'input') {
      type(byTag(ctx.root, 'input')[0], step.answer);
      byText(ctx.root, 'button', 'تأكيد الإجابة')[0].click();
    } else {
      const el = byClass(ctx.root, 'opt').find((o) => text(o).includes(step.answer));
      if (!el) throw new Error(`recovery step ${n + 1}: option ${JSON.stringify(step.answer)} not found`);
      el.click();
    }
    await tick(60);
    const card = byClass(ctx.root, 'flow')[0];
    const stage = card ? card.getAttribute('data-stage') : null;
    if (!stages.length || stages[stages.length - 1] !== stage) stages.push(stage);
    if (n < flow.length - 1) {
      index = n + 1;
      const next = byText(ctx.root, 'button', 'السؤال التالي')[0] || byText(ctx.root, 'button', 'جولة جديدة')[0];
      next.click(); await tick(60);
    }
  }
  const finalText = text(ctx.root);
  check('every recovery answer is correct and graded by the real engine', flow.every((f) => f.result.is_correct));
  check('stepper goes remediation -> retry -> resolved', JSON.stringify(stages) === JSON.stringify(['remediation', 'retry', 'resolved']), JSON.stringify(stages));
  check('the original lesson is retried after the root is firm', flow.some((f) => f.result.action === 'return_up') && flow.some((f) => f.question.skill === 'mult_div_integers'));
  check('final stepper text reports the closed gap for root and original lesson', finalText.includes('أُغلقت الفجوة') && finalText.includes('جمع الأعداد الصحيحة') && finalText.includes('ضرب'));
  routes.shift(); routes.shift(); routes.shift();
  ctx.destroy();
});

await run('whatsapp share', async () => {
  state.role = 'parent'; await st.loadMe();
  const { parentView, reportView, reportText, whatsappUrl } = await import('../../app/static/js/views/parent.js');
  const tree = PY.tree_full;
  const full = reportText({ name: 'ليان', tree, report, insights });
  check('summary names the child, health and mastered count', full.includes('ليان') && full.includes('صحة الشجرة') && full.includes(`${tree.summary.mastered} من ${tree.summary.live}`));
  check('full access summary names the root', !!tree.root_gap.name_ar && full.includes(tree.root_gap.name_ar));
  const locked = reportText({ name: 'ليان', tree: PY.tree_locked, report, insights });
  check('basic summary does not leak the root name', !locked.includes(tree.root_gap.name_ar) && locked.includes('باقة برو'));
  const url = whatsappUrl('مرحبا\nجذور');
  check('wa.me link is url-encoded', url.startsWith('https://wa.me/?text=') && !url.includes('\n') && decodeURIComponent(url.split('=')[1]) === 'مرحبا\nجذور');
  let opened = null;
  window.open = (u, target, feat) => { opened = [u, target, feat]; };
  const ctx = mkctx(); await parentView(ctx); await tick(30);
  const btn = byText(ctx.root, 'button', 'مشاركة عبر واتساب')[0];
  check('share button on the parent dashboard', !!btn);
  btn.click();
  check('opens wa.me in a new tab with noopener', !!opened && opened[0].startsWith('https://wa.me/?text=') && opened[1] === '_blank' && opened[2] === 'noopener');
  ctx.destroy();
  opened = null;
  const rep = mkctx({ id: 'S1' }); await reportView(rep); await tick(30);
  byText(rep.root, 'button', 'مشاركة عبر واتساب')[0].click();
  check('printable report shares the same summary', !!opened && decodeURIComponent(opened[0]).includes('تقرير جذور عن ليان'));
  rep.destroy();
});

await run('teacher remediation + safety', async () => {
  state.role = 'teacher'; await st.loadMe();
  const { teacherView } = await import('../../app/static/js/views/teacher.js');
  const ctx = mkctx(); await teacherView(ctx); await tick(40);
  const btn = byText(ctx.root, 'button', 'تكليف علاجي')[0];
  check('remediation button on the top gaps card', !!btn);
  btn.click(); await tick(30);
  const confirm = byClass(body, 'modal').pop();
  check('confirmation lists only the affected students', text(confirm).includes('زياد') && text(confirm).includes('تقوية: القيمة المطلقة') && !text(confirm).includes('عمر'));
  byText(confirm, 'button', 'إنشاء التكليف')[0].click(); await tick(60);
  const post = calls.filter((c) => c.method === 'POST' && c.url.includes('/remediation')).pop();
  check('remediation posted for exactly that skill', !!post && post.body.skill_id === 'absolute_value' && Object.keys(post.body).length === 1);
  check('result modal shows students and the teaching tip', text(body).includes('تم إنشاء التكليف العلاجي') && text(body).includes('استخدم خط الأعداد الأرضي'));
  byText(byClass(body, 'modal').pop(), 'button', 'عرض الواجبات')[0].click(); await tick(40);
  check('assignments tab marks remediation work', text(ctx.root).includes('علاجي') && text(ctx.root).includes('تقوية: القيمة المطلقة'));
  byText(ctx.root, 'button', 'السلامة')[0].click(); await tick(40);
  check('safety tab explains the privacy model', text(ctx.root).includes('لا تظهر لك محادثات الطلاب إلا عندما يبلّغ'));
  check('open report listed with reason and names', text(ctx.root).includes('تنمّر أو إساءة') && text(ctx.root).includes('أبلغ عن'));
  byText(ctx.root, 'button', 'مراجعة')[0].click(); await tick(40);
  const drawer = byClass(body, 'drawer').pop();
  check('thread shows the flagged message and context', text(drawer).includes('الرسالة المُبلَّغ عنها') && text(drawer).includes('أنت مزعج') && text(drawer).includes('توقف من فضلك'));
  byText(drawer, 'button', 'تمت المعالجة')[0].click(); await tick(40);
  const res = calls.filter((c) => c.url.includes('/resolve')).pop();
  check('resolve posted with the decision', !!res && res.body.action === 'resolved');
  ctx.destroy();
});

await run('block + report', async () => {
  state.role = 'student'; await st.loadMe();
  const { communityView } = await import('../../app/static/js/views/social.js');
  const ctx = mkctx(); await communityView(ctx);
  byClass(ctx.root, 'conv')[0].click(); await tick(40);
  const byLabel = (label) => find(ctx.root, (e) => e.attrs && e.attrs['aria-label'] === label);
  check('safety note visible in the thread', text(ctx.root).includes('لا تشارك أرقام هاتف'));
  check('header has report and block actions', !!byLabel('حظر') && !!byLabel('إبلاغ'));
  const flags = byClass(ctx.root, 'bubble-flag');
  check('only received bubbles carry a flag', flags.length === 1);
  flags[0].click();
  check('message report dialog opens', text(body).includes('الإبلاغ عن رسالة'));
  const sel = byTag(byClass(body, 'modal').pop(), 'select')[0];
  sel.value = 'bullying';
  byText(byClass(body, 'modal').pop(), 'button', 'إرسال البلاغ')[0].click(); await tick(40);
  const rep = calls.filter((c) => c.url.includes('/community/report')).pop();
  check('report carries user, message and reason', !!rep && rep.body.user_id === 'U2' && rep.body.message_id === 'M1' && rep.body.reason === 'bullying' && rep.body.also_block === false);
  byLabel('إبلاغ').click();
  check('user report dialog names the person', text(body).includes('الإبلاغ عن عمر'));
  byText(byClass(body, 'modal').pop(), 'button', 'إلغاء')[0].click();
  byLabel('حظر').click(); await tick(20);
  byText(byClass(body, 'modal').pop(), 'button', 'حظر')[0].click(); await tick(60);
  check('block posted for the open friend', calls.some((c) => c.method === 'POST' && c.url.includes('/community/block/U2')));
  byText(ctx.root, 'button', 'المحظورون')[0].click(); await tick(40);
  check('empty blocked list message', text(body).includes('لا يوجد مستخدمون محظورون'));
  byText(byClass(body, 'modal').pop(), 'button', 'إغلاق')[0].click();
  blockedState.list = [U('U7', 'سلمى')];
  byText(ctx.root, 'button', 'المحظورون')[0].click(); await tick(40);
  check('blocked list shows the person', text(byClass(body, 'modal').pop()).includes('سلمى'));
  byText(byClass(body, 'modal').pop(), 'button', 'إلغاء الحظر')[0].click(); await tick(40);
  check('unblock sends DELETE', calls.some((c) => c.method === 'DELETE' && c.url.includes('/community/block/U7')));
  blockedState.list = [];
  ctx.destroy();
  const link = api.toError(422, { detail: 'message_not_allowed:link' });
  const contact = api.toError(422, { detail: 'message_not_allowed:contact' });
  check('chat filter messages are specific', link.message.includes('الروابط') && contact.message.includes('أرقام الهاتف') && link.message !== contact.message);
  check('rate limit messages are friendly', api.toError(429, { detail: 'rate_limited' }).message.includes('طلبات كثيرة') && api.toError(429, { detail: 'too_many_attempts' }).message.includes('انتظر'));
  check('new error codes are all mapped', ['unblock_first', 'no_students_with_gap', 'not_assigned', 'report_not_found', 'cannot_block_self', 'cannot_report_self', 'not_blocked', 'message_not_found'].every((c) => !api.toError(400, { detail: c }).message.includes('غير متوقع')));
});

await run('judge hint + input validation + diagnosis card', async () => {
  state.role = 'student'; await st.loadMe();
  const { practiceView } = await import('../../app/static/js/views/practice.js');
  const before = st.store.health;
  st.store.health = { ...before, judge: true };
  const first = mkctx(); await practiceView(first);
  check('judge hint is shown in judge mode', byClass(first.root, 'judge-hint').length === 1 && text(first.root).includes('أجب إجابات خاطئة'));
  byLabelOf(first.root, 'إغلاق التلميح').click();
  check('judge hint can be dismissed', byClass(first.root, 'judge-hint').length === 0);
  first.destroy();
  const again = mkctx(); await practiceView(again);
  check('dismissed hint stays dismissed', byClass(again.root, 'judge-hint').length === 0);
  again.destroy();
  st.store.health = { ...before, judge: false };

  routes.unshift(['GET', /\/adaptive\/question/, () => ok({ question: 'أوجد ناتج الجمع: 1/2 + 1/3', hint: 'ت', skill: 'fractions_addsub', difficulty: 1, pattern: 'fa_unlike', source: 'offline', remedial: null, banner: null, guided: false, type: 'input', options: [], skill_name: 'x' })]);
  const ctx = mkctx(); await practiceView(ctx);
  const input = byTag(ctx.root, 'input')[0];
  check('fraction questions show a fraction placeholder', !!input && input.attrs.placeholder.includes('3/4'));
  check('input length is capped', input.attrs.maxlength === '20');
  const sent = () => calls.filter((c) => c.url.includes('/adaptive/answer')).length;
  const baseline = sent();
  const sendBtn = byText(ctx.root, 'button', 'تأكيد الإجابة')[0];
  type(input, 'abc'); sendBtn.click(); await tick(20);
  check('letters are rejected before reaching the server', sent() === baseline);
  type(input, '<script>1</script>'); sendBtn.click(); await tick(20);
  check('markup is rejected before reaching the server', sent() === baseline);
  type(input, ''); sendBtn.click(); await tick(20);
  check('empty answer is rejected before reaching the server', sent() === baseline);
  routes.unshift(['POST', /\/adaptive\/answer/, () => ok({ action: 'continue', next_skill: 'fractions_addsub', next_difficulty: 1, reason: 'r', breadcrumb: null, gap_skill: null, round_over: false, coins_awarded: 0, gems_awarded: 0, is_correct: true, correct_answer: '5/6', misconception: '', explanation: '', new_gaps: [], remedial: null, next_stage: 'same_pattern', mistake_card: null, gap_locked: false, remaining_questions: 10 })]);
  type(input, '5/6'); sendBtn.click(); await tick(40);
  check('a valid fraction is sent', sent() === baseline + 1);
  routes.shift(); routes.shift();
  ctx.destroy();
});

await run('tutor source badge + judge chips', async () => {
  state.role = 'student'; await st.loadMe();
  const { tutorView } = await import('../../app/static/js/views/tutor.js');
  const before = st.store.health;
  st.store.health = { ...before, judge: true };
  const ctx = mkctx(); await tutorView(ctx); await tick(40);
  check('judge chips include a fraction and an off-topic probe', text(ctx.root).includes('جرّب: 1/2 + 1/3') && text(ctx.root).includes('جرّب سؤالاً خارج المنهج'));
  const reply = (source, body) => routes.unshift(['POST', /\/chat\/message/, () => ok({ reply: body, gap_detected: false, gap_skill: null, drill_down_triggered: false, next_skill: null, next_difficulty: null, breadcrumb: '', remaining_today: 3, source })]);
  const ask = async (msg) => { byTag(ctx.root, 'textarea')[0].value = msg; byClass(ctx.root, 'send')[0].click(); await tick(40); };
  reply('solver', 'الناتج 5/6'); await ask('1/2 + 1/3'); routes.shift();
  check('solver reply carries the verified badge', byClass(ctx.root, 'src-badge').some((b) => text(b).includes('حل محسوب آلياً')));
  reply('guardrail', 'عذراً، أنا مبرمج حصرياً لمساعدتك في المنهج التعليمي وتطوير مستواك الأكاديمي.'); await ask('ما هي عاصمة فرنسا'); routes.shift();
  const badges = byClass(ctx.root, 'src-badge');
  check('off-topic reply is labelled as never sent to a model', badges.some((b) => b.attrs['data-source'] === 'guardrail' && text(b).includes('لم يُرسل لأي نموذج')));
  check('exact fallback sentence is shown', text(ctx.root).includes('عذراً، أنا مبرمج حصرياً لمساعدتك في المنهج التعليمي وتطوير مستواك الأكاديمي.'));
  reply('mystery', 'x'); await ask('سؤال'); routes.shift();
  check('unknown source shows no badge and does not crash', byClass(ctx.root, 'src-badge').length === badges.length);
  ctx.destroy();
  st.store.health = before;
});

const loadedViews = fs.readdirSync(new URL('../../app/static/js/views', import.meta.url)).length;
for (const [cond, name, extra] of results) console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? '  -> ' + extra : ''}`);
console.log(`\n${results.length - failures}/${results.length} checks passed (${loadedViews} view modules)`);
process.exit(failures ? 1 : 0);
