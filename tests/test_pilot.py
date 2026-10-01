from scripts import pilot_summary as ps


def test_summary_counts_gains_and_skips_bad_rows():
    rows = [
        {"student_code": "A", "pre_correct": "4", "post_correct": "7", "total_questions": "10"},
        {"student_code": "B", "pre_correct": "6", "post_correct": "6", "total_questions": "10"},
        {"student_code": "C", "pre_correct": "8", "post_correct": "5", "total_questions": "10"},
        {"student_code": "D", "pre_correct": "", "post_correct": "5", "total_questions": "10"},
        {"student_code": "E", "pre_correct": "11", "post_correct": "5", "total_questions": "10"},
    ]
    result = ps.summarize(rows)
    assert result["n"] == 3 and result["skipped"] == ["D", "E"]
    assert (result["improved"], result["same"], result["worse"]) == (1, 1, 1)
    assert abs(result["mean_pre"] - 60) < 1e-9 and abs(result["mean_post"] - 60) < 1e-9
    assert result["best"] == "A"


def test_report_is_honest_about_small_samples():
    text = ps.report(ps.summarize([{"student_code": "A", "pre_correct": "2", "post_correct": "6", "total_questions": "10"}]))
    assert "+40" in text and "ليست إثباتاً" in text and "تراجع" in text


def test_empty_and_template_files_are_handled(tmp_path):
    assert ps.summarize([])["n"] == 0
    assert "لا توجد صفوف صالحة" in ps.report(ps.summarize([]))
    path = tmp_path / "r.csv"
    path.write_text("student_code,pre_correct,post_correct,total_questions\nS1,3,8,10\n", encoding="utf-8")
    assert ps.summarize(ps.load(str(path)))["mean_gain"] == 50
