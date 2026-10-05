"""Real-browser end-to-end walk-through of the core loop (Playwright + Chromium).

Against the real stack (the judged setup):
    python run_demo.py --reset --no-browser          # terminal 1 (PostgreSQL + FastAPI)
    python tests/e2e/browser_e2e.py                  # terminal 2
Requires: pip install playwright && python -m playwright install chromium

It drives the UI exactly as a judge would: Omar's demo button -> his tree -> practice page -> realistic
wrong answers (the bank's misconception-linked distractors) until the root is named -> correct answers
through remediation and the retry of the original lesson -> page refresh -> parent login (the buyer) ->
the diagnosis record in the parent report. To know which option is right or wrong it reads the pending question
from PostgreSQL (`--oracle db`, a test oracle only; the browser never sees answers). At the end it
re-reads PostgreSQL to confirm the diagnosis and the mastery updates were persisted.

`--oracle sim --base http://127.0.0.1:8765` runs the same walk-through against
tests/e2e/sim_server.py (real engine, simulated HTTP/persistence) when no database is available.

Mutates Omar's demo state: run `python run_demo.py --reset` again before judging.
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.engine.offline_bank import norm  # noqa: E402

OMAR_EMAIL = "student2@demo.jo"
ROOT_NAME, ORIGIN_NAME = "جمع الأعداد الصحيحة", "ضرب الأعداد الصحيحة وقسمتها"


class DbOracle:
    def __init__(self):
        from sqlalchemy import select
        from app.database import SessionLocal
        from app.models.org import User
        self.Session = SessionLocal
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == OMAR_EMAIL))
            if user is None:
                raise SystemExit("Omar's demo account is missing: run python run_demo.py --reset first")
            self.student_id = user.id

    def student_id_for_report(self) -> str:
        return str(self.student_id)

    def pending(self) -> dict:
        from app.models.adaptive import StudentAdaptiveState
        with self.Session() as db:
            return dict(db.get(StudentAdaptiveState, self.student_id).pending_question or {})

    def persisted(self) -> dict:
        from sqlalchemy import select
        from app.models.adaptive import DiagnosisEvent, SkillMastery
        with self.Session() as db:
            events = db.scalars(select(DiagnosisEvent).where(DiagnosisEvent.student_id == self.student_id)).all()
            mastery = {m.skill_id: m.status.value for m in db.scalars(
                select(SkillMastery).where(SkillMastery.student_id == self.student_id))}
        return {"diagnoses": [(e.origin_skill, e.root_skill, e.confidence_level) for e in events], "mastery": mastery}


class SimOracle:
    def __init__(self, base):
        self.base = base

    def pending(self) -> dict:
        with urllib.request.urlopen(self.base + "/__mock__/pending", timeout=5) as res:
            return json.loads(res.read().decode("utf-8"))

    def persisted(self):
        return None

    def student_id_for_report(self) -> str:
        return "00000000-0000-4000-8000-000000000002"


results = []

# Smallest WCAG contrast ratio among visible text inside the given selectors (fg vs the first opaque background
# up the tree). Elements on gradient/brand surfaces (.upsell, buttons) and SVG text are skipped.
CONTRAST_JS = """(sel) => {
  const parse = (s) => { const m = s && s.match(/rgba?\\(([^)]+)\\)/); if (!m) return null;
    const p = m[1].split(',').map((x) => parseFloat(x)); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const bgOf = (el) => { for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor);
    if (c && c.a > 0.5) return c; } return parse(getComputedStyle(document.body).backgroundColor); };
  let worst = 99, sample = '', n = 0;
  for (const host of document.querySelectorAll(sel)) {
    for (const el of host.querySelectorAll('*')) {
      if (el.closest('.upsell, svg, button, .btn, .chip.lime')) continue;
      const own = Array.from(el.childNodes).some((t) => t.nodeType === 3 && t.textContent.trim());
      if (!own || !el.getClientRects().length) continue;
      const fg = parse(getComputedStyle(el).color), bg = bgOf(el);
      if (!fg || !bg) continue;
      const a = lum(fg), b = lum(bg), ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
      n += 1;
      if (ratio < worst) { worst = ratio; sample = el.textContent.trim().slice(0, 40) + ' [' + getComputedStyle(el).color + ' on ' + JSON.stringify(bg) + ']'; }
    }
  }
  return { worst: Math.round(worst * 100) / 100, sample, n };
}"""


def check(name, ok, note=""):
    results.append((bool(ok), name, note))
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  -> ' + str(note)) if note else ''}", flush=True)
    return ok


def stage(page):
    el = page.query_selector("[data-testid=workflow]")
    return el.get_attribute("data-stage") if el else None


def answer(page, pending: dict, mistake: bool, double_click=False):
    target = next(iter(pending["traps"])) if mistake else pending["correct_answer"]
    card = page.locator(".q-card").first
    if pending.get("type") == "input":
        card.locator("input.input").fill(str(target))
        card.get_by_role("button", name="تأكيد الإجابة").click()
    else:
        for opt in card.locator(".opt").all():
            if norm(opt.locator(".grow").inner_text()) == norm(target):
                opt.dblclick() if double_click else opt.click()
                break
        else:
            raise AssertionError(f"option {target!r} not on screen")
    page.wait_for_selector(".verdict", timeout=10000)


def next_question(page):
    nxt = page.get_by_role("button", name="السؤال التالي")
    if nxt.count():
        nxt.first.click()
    else:
        page.get_by_role("button", name="جولة جديدة").first.click()
    page.wait_for_selector(".q-card", timeout=10000)


def run(base: str, oracle, headed: bool, shots: Path) -> int:
    from playwright.sync_api import sync_playwright
    shots.mkdir(parents=True, exist_ok=True)
    errors, answer_posts, server_errors, client_errors = [], [], [], []
    injecting = {"on": False}  # responses we fake on purpose are not server errors
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        page = browser.new_page(viewport={"width": 1280, "height": 900}, locale="ar-JO")
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: m.type == "error" and "Failed to load resource" not in m.text
                and errors.append(f"console: {m.text}"))
        page.on("response", lambda r: r.url.startswith(base) and r.status >= 400 and not injecting["on"]
                and (server_errors if r.status >= 500 else client_errors).append(f"{r.status} {r.request.method} {r.url[len(base):]}"))
        page.on("request", lambda r: r.method == "POST" and r.url.endswith("/adaptive/answer") and answer_posts.append(time.time()))

        page.goto(base + "/app/#/login")
        page.get_by_role("button", name="طالب (عمر - برو)").click()
        page.wait_for_selector("svg.scene .leaf", timeout=15000)
        check("demo login lands on the learner's tree first", page.evaluate("location.hash") in ("#/", "") and page.locator(".leaf.cur").count() == 1,
              page.evaluate("location.hash"))
        nav = page.locator("nav").first.inner_text()
        check("no coins, gems, wallet or shop in the learner's navigation",
              page.locator(".pill.coin, .pill.gem").count() == 0 and "المتجر" not in nav, nav[:120])
        page.get_by_role("link", name="تابع التدريب").first.click()
        page.wait_for_selector(".q-card", timeout=15000)
        page.wait_for_selector("[data-testid=workflow]", timeout=10000)
        check("learner opens practice; diagnosis stepper visible", stage(page) in ("practising", "gathering_evidence"), stage(page))
        check("current lesson is shown on the question", ORIGIN_NAME in page.locator(".q-card").inner_text())

        stages, diagnosed, early_ctas = [], False, 0
        for n in range(10):
            answer(page, oracle.pending(), mistake=True)
            stages.append(stage(page))
            if stages[-1] != "root_identified":
                early_ctas += page.locator("[data-testid=root-cta]").count()
            if n == 0:
                page.get_by_role("button", name="اعرض الشرح").first.click()
                explain = page.locator(".explain").first.inner_text()
                check("a wrong answer names its likely misconception", "سبب الخطأ المحتمل" in explain, explain[:80])
                check("a wrong answer explains why no root is named yet",
                      "نجمع الأدلة" in page.locator("[data-testid=evidence-status]").first.inner_text())
            if stages[-1] == "root_identified":
                diagnosed = True
                break
            next_question(page)
        check("wrong answers gather evidence before any diagnosis", diagnosed and all(s == "gathering_evidence" for s in stages[:-1]), stages)
        check("no «root found» button while the evidence is insufficient", early_ctas == 0, early_ctas)
        card = page.wait_for_selector("[data-testid=diagnosis-card]", timeout=15000)
        text = card.inner_text()
        check("diagnosis card: root, confidence, evidence, why, remediation",
              all(k in text for k in (ROOT_NAME, "الثقة", "الأدلة", "لماذا هذا الدرس؟", "الخطة العلاجية")), text[:160])
        cta = page.locator("[data-testid=root-cta]")
        check("root identified -> one clear «ظهر جذر المشكلة» button", cta.count() == 1 and "ظهر جذر المشكلة" in cta.first.inner_text(),
              cta.count())
        cta.first.click()
        panel = page.wait_for_selector("[data-testid=root-diagnosis]", timeout=10000).inner_text()
        check("the button opens the diagnosis card: problem, root, why, confidence, mastery %, next step",
              all(k in panel for k in (ORIGIN_NAME, ROOT_NAME, "لماذا", "مستوى الثقة", "%", "ماذا سنفعل الآن")), panel[:200])
        first_mastery = int(page.inner_text("[data-testid=dx-mastery]").split("%")[0])
        page.screenshot(path=str(shots / "1_diagnosis.png"), full_page=True)

        seen, posts_before = [], None
        for i in range(40):
            next_question(page)
            pending = oracle.pending()
            if i == 1:
                # Break it: the API answers 503 (database down). The UI must say so and let the
                # learner resend the same answer once the backend is back.
                injecting["on"] = True
                page.route("**/adaptive/answer", lambda route: route.fulfill(
                    status=503, content_type="application/json", body='{"detail": "database_unavailable"}'))
                card = page.locator(".q-card").first
                if pending.get("type") == "input":
                    card.locator("input.input").fill(str(pending["correct_answer"]))
                    card.get_by_role("button", name="تأكيد الإجابة").click()
                else:
                    next(o for o in card.locator(".opt").all()
                         if norm(o.locator(".grow").inner_text()) == norm(pending["correct_answer"])).click()
                toast = page.wait_for_selector(".toast.error", timeout=5000).inner_text()
                check("database outage is shown to the learner in plain words", "قاعدة البيانات غير متاحة" in toast, toast)
                page.unroute("**/adaptive/answer")
                injecting["on"] = False
                answer(page, pending, mistake=False)
                check("the same answer can be resent after the outage", page.locator(".verdict.good").count() >= 1)
            elif i == 2:
                posts_before = len(answer_posts)
                answer(page, pending, mistake=False, double_click=pending.get("type") != "input")
                time.sleep(0.4)
                check("double click submits one answer only", len(answer_posts) - posts_before == 1, len(answer_posts) - posts_before)
            else:
                answer(page, pending, mistake=False)
            current = stage(page)
            if i == 3:
                # The card is read from the backend each time it is opened: mastery follows the learner.
                flow_cta = page.locator("[data-testid=root-cta]")
                check("the «root found» button stays available during remediation / retry", flow_cta.count() == 1, (current, flow_cta.count()))
                if flow_cta.count():
                    flow_cta.first.click()
                    page.wait_for_selector("[data-testid=dx-mastery]", timeout=10000)
                    later = int(page.inner_text("[data-testid=dx-mastery]").split("%")[0])
                    check("the diagnosis card shows the CURRENT mastery (it rose after correct answers)", later > first_mastery,
                          f"{first_mastery}% -> {later}%")
            if not seen or seen[-1] != current:
                seen.append(current)
            if current == "resolved":
                break
        check("stepper: remediation -> retry -> resolved", seen[:1] == ["remediation"] and "retry" in seen and seen[-1] == "resolved", seen)
        page.screenshot(path=str(shots / "2_resolved.png"), full_page=True)

        page.reload()
        page.wait_for_selector("[data-testid=workflow]", timeout=15000)
        page.wait_for_function("document.querySelector('[data-testid=workflow]').dataset.stage === 'resolved'", timeout=10000)
        check("refresh keeps the learner state (served from the backend)", stage(page) == "resolved")
        check("no «root found» button once the gap is closed", page.locator("[data-testid=root-cta]").count() == 0)

        page.evaluate("localStorage.removeItem('juthoor.token')")
        page.goto(base + "/app/#/login")
        page.reload()
        # B2C: the parent (the buyer) sees where the gap started, the evidence and what happened after it.
        page.get_by_role("button", name="ولي أمر", exact=True).click()
        page.wait_for_selector("select[aria-label='الابن']", timeout=15000)
        page.select_option("select[aria-label='الابن']", label="عمر")
        page.wait_for_function("(() => { const r = document.querySelector('[data-testid=diagnosis-record]'); "
                               "return r && r.innerText.includes('التعثّر الظاهر في'); })()", timeout=15000)
        record = page.locator("[data-testid=diagnosis-record]").inner_text()
        check("parent report shows origin, root, confidence, evidence, next step and outcome",
              all(k in record for k in ("التعثّر الظاهر في", ROOT_NAME, "الثقة", "الأدلة", "الخطوة التالية المقترحة", "أُغلقت الفجوة")), record[:200])
        live = page.locator("[data-testid=diagnosis-live]").first.inner_text()
        check("parent record shows the live state (current mastery and the original lesson)", "%" in live and ORIGIN_NAME in live, live)
        light = page.evaluate(CONTRAST_JS, "[data-testid=diagnosis-record], main .card:not(.upsell)")
        check("light mode: report text contrast >= 4.5", light["worst"] >= 4.5 and light["n"] > 10, light)
        page.screenshot(path=str(shots / "3_parent.png"), full_page=True)
        page.get_by_role("button", name="تبديل المظهر").click()
        page.wait_for_function("document.documentElement.dataset.theme === 'dark'", timeout=5000)
        dark = page.evaluate(CONTRAST_JS, "[data-testid=diagnosis-record], main .card:not(.upsell)")
        check("dark mode: report text contrast >= 4.5 (no dark text on dark cards)", dark["worst"] >= 4.5 and dark["n"] > 10, dark)
        page.wait_for_timeout(700)  # let the page-enter animation finish before the screenshot
        page.screenshot(path=str(shots / "4_parent_dark.png"), full_page=True)
        page.goto(base + f"/app/#/report/{oracle.student_id_for_report()}")
        page.wait_for_selector(".report [data-testid=diagnosis-record]", timeout=15000)
        printable = page.evaluate(CONTRAST_JS, ".report")
        check("dark mode: printable report text contrast >= 4.5", printable["worst"] >= 4.5 and printable["n"] > 10, printable)
        page.wait_for_timeout(700)  # let the page-enter animation finish before the screenshot
        page.screenshot(path=str(shots / "5_report_dark.png"), full_page=True)
        browser.close()

    check("no uncaught JavaScript errors", not errors, errors[:5])
    check("no 5xx responses from the API", not server_errors, server_errors[:5])
    if client_errors:
        print("info: expected 4xx responses seen:", sorted(set(client_errors))[:8])
    persisted = oracle.persisted()
    if persisted is not None:
        check("PostgreSQL holds the diagnosis", any(r == "adding_integers" for _, r, _ in persisted["diagnoses"]), persisted["diagnoses"])
        check("PostgreSQL holds the mastery updates", persisted["mastery"].get("adding_integers") == "mastered"
              and persisted["mastery"].get("mult_div_integers") == "mastered", persisted["mastery"])
    failed = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(failed)}/{len(results)} browser checks passed; screenshots in {shots}")
    return 1 if failed else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--oracle", choices=("db", "sim"), default="db")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--shots", default=str(ROOT / "docs" / "e2e"))
    args = parser.parse_args(argv)
    base = args.base.rstrip("/")
    oracle = DbOracle() if args.oracle == "db" else SimOracle(base)
    return run(base, oracle, args.headed, Path(args.shots))


if __name__ == "__main__":
    sys.exit(main())
