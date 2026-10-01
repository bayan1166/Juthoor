import argparse
import csv
import sys


def _num(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def summarize(rows):
    usable, skipped = [], []
    for row in rows:
        pre, post, total = _num(row.get("pre_correct")), _num(row.get("post_correct")), _num(row.get("total_questions"))
        valid = None not in (pre, post, total) and total > 0 and 0 <= pre <= total and 0 <= post <= total
        if valid:
            usable.append((row.get("student_code", "").strip() or f"#{len(usable) + 1}", pre / total * 100, post / total * 100))
        else:
            skipped.append(row.get("student_code", "").strip() or "?")
    n = len(usable)
    if n == 0:
        return {"n": 0, "skipped": skipped}
    gains = [post - pre for _, pre, post in usable]
    return {
        "n": n,
        "skipped": skipped,
        "mean_pre": sum(p for _, p, _ in usable) / n,
        "mean_post": sum(q for _, _, q in usable) / n,
        "mean_gain": sum(gains) / n,
        "improved": sum(1 for g in gains if g > 0),
        "same": sum(1 for g in gains if g == 0),
        "worse": sum(1 for g in gains if g < 0),
        "best": max(usable, key=lambda r: r[2] - r[1])[0],
    }


def report(result):
    if result["n"] == 0:
        return "لا توجد صفوف صالحة في الملف. تأكد من الأعمدة: student_code, pre_correct, post_correct, total_questions."
    lines = [
        f"عدد الطلاب المحتسبين: {result['n']}",
        f"متوسط الاختبار القبلي: {result['mean_pre']:.0f}%",
        f"متوسط الاختبار البعدي: {result['mean_post']:.0f}%",
        f"متوسط التغير: {result['mean_gain']:+.0f} نقطة مئوية",
        f"تحسّن: {result['improved']} | ثبت: {result['same']} | تراجع: {result['worse']}",
    ]
    if result["skipped"]:
        lines.append(f"صفوف مستبعدة لنقص أو خطأ في البيانات: {', '.join(result['skipped'])}")
    lines.append("تنبيه: العينة صغيرة وبلا مجموعة ضابطة، فالأرقام مؤشر أولي وليست إثباتاً للأثر. اذكر عدد الطلاب دائماً واذكر من تراجع منهم.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="ملخص نتائج التجربة الميدانية")
    parser.add_argument("csv_path")
    args = parser.parse_args(argv)
    print(report(summarize(load(args.csv_path))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
