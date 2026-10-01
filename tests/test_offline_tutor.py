from app.engine import knowledge_graph as kg
from app.services.rag import offline_tutor as ot


def test_mixed_sign_addition_is_solved_with_the_rule():
    reply = ot.solve_reply("ما ناتج 7 + (-3)")
    assert reply is not None
    assert "الإشارتان مختلفتان" in reply
    assert "4" in reply


def test_arabic_digits_and_unicode_minus():
    solved = ot.solve_lines("٧ + (\u2212٣٠)")
    assert solved is not None and solved[1] == -23


def test_precedence_and_parentheses():
    assert ot.solve_lines("2 + 3 * 4")[1] == 14
    assert ot.solve_lines("(2 + 3) * 4")[1] == 20
    assert ot.solve_lines("|-7| + (-3)")[1] == 4


def test_subtraction_of_negative_and_signs_of_products():
    assert ot.solve_lines("3 - (-5)")[1] == 8
    assert ot.solve_lines("(-6) * 4")[1] == -24
    assert ot.solve_lines("(-18) / (-3)")[1] == 6


def test_unsafe_and_degenerate_input_is_ignored():
    assert ot.find_expression("__import__('os').system('ls')") is None
    assert ot.find_expression("hello") is None
    assert ot.find_expression("123") is None


def test_division_edge_cases_do_not_crash():
    zero = ot.solve_lines("5 / 0")
    assert zero is not None and zero[1] is None
    inexact = ot.solve_lines("7 / 2")
    assert inexact is not None and inexact[1] is None


def test_practice_dialogue_grades_the_students_answer():
    first = ot.offline_turn("adding_integers", [], "مش فاهم")
    history = [{"role": "tutor", "content": first.reply}]
    wrong = ot.offline_turn("adding_integers", history, "9")
    assert ot.WRONG_MARK in wrong.reply and "الحل" in wrong.reply
    pending = ot.pending_question(history)
    right_value = pending[2][1]
    right = ot.offline_turn("adding_integers", history, str(right_value))
    assert "إجابة صحيحة" in right.reply


def test_repeated_misses_flag_the_prerequisite():
    first = ot.offline_turn("mult_div_integers", [], "اختبرني")
    history = [{"role": "tutor", "content": first.reply}]
    turn = ot.offline_turn("mult_div_integers", history, "999")
    history += [{"role": "student", "content": "999"}, {"role": "tutor", "content": turn.reply}]
    turn2 = ot.offline_turn("mult_div_integers", history, "888")
    flagged = turn.gap_skill or turn2.gap_skill
    assert flagged in kg.ancestors("mult_div_integers")


def test_keyword_gap_detection_only_for_prerequisites():
    gap = ot.offline_turn("mult_div_integers", [], "مش فاهم الجمع")
    assert gap.gap_detected and gap.gap_skill == "adding_integers"
    own = ot.offline_turn("adding_integers", [], "مش فاهم الجمع")
    assert not own.gap_detected


def test_explain_uses_curriculum_concepts_and_an_example():
    turn = ot.offline_turn("adding_integers", [], "اشرح لي الجمع")
    assert "مثال محلول" in turn.reply and "الإشارتان" in turn.reply


def test_comparison_and_absolute_value_questions():
    cmp_turn = ot.offline_turn("comparing_integers", [], "قارن بين -3 و -8")
    assert "أكبر" in cmp_turn.reply
    abs_turn = ot.offline_turn("absolute_value", [], "|-7|")
    assert "7" in abs_turn.reply


def test_unknown_message_gets_actionable_menu_not_a_loop():
    turn = ot.offline_turn("adding_integers", [], "كيف حالك اليوم")
    assert "اكتب" in turn.reply and not turn.gap_detected


def test_every_practice_pool_item_is_solvable():
    for skill, items in ot.POOL.items():
        for item in items:
            if item.startswith("CMP:"):
                continue
            solved = ot.solve_lines(item)
            assert solved is not None and solved[1] is not None, (skill, item)


def test_fraction_solver_steps_and_results():
    from fractions import Fraction
    assert ot.solve_fraction("1/2 + 1/3")[1] == Fraction(5, 6)
    assert ot.solve_fraction("3/4 - 1/2")[1] == Fraction(1, 4)
    assert ot.solve_fraction("2/3 * 3/4")[1] == Fraction(1, 2)
    assert ot.solve_fraction("3/4 : 1/2")[1] == Fraction(3, 2)
    assert ot.solve_fraction("3 : 1/4")[1] == 12
    assert ot.solve_fraction("1/0 + 1/2")[1] is None
    assert ot.solve_fraction("7 + 3") is None
    assert ot.solve_fraction("1/2 : 0/3")[1] is None
    steps = ot.solve_fraction("1/2 + 1/3")[0]
    assert "المقام المشترك" in steps[0]
    assert ot.solve_fraction("\u0661/\u0662 \u00F7 \u0661/\u0664")[1] == 2


def test_fraction_questions_do_not_hijack_integer_division():
    assert ot.solve_fraction("20 / 4") is None
    assert ot.fraction_reply("(-24) / 6") is None
    assert "الناتج" in ot.fraction_reply("1/2 + 1/3")
    assert ot.solve_lines("(-18) / (-3)")[1] == 6


def test_fraction_practice_dialogue_grades_answers():
    first = ot.offline_turn("fractions_addsub", [], "اختبرني")
    assert "3/4" in first.reply or "كسراً" in first.reply
    history = [{"role": "tutor", "content": first.reply}]
    pending = ot.pending_question(history)
    assert pending[0] == "frac"
    expected = pending[2][1]
    right = ot.offline_turn("fractions_addsub", history, ot.fr_text(expected))
    assert "إجابة صحيحة" in right.reply
    wrong = ot.offline_turn("fractions_addsub", history, "9/7")
    assert ot.WRONG_MARK in wrong.reply and "خطوة بخطوة" in wrong.reply


def test_fraction_misconception_and_unsimplified_answers():
    history = [{"role": "tutor", "content": "كم ناتج \u20661/2 + 1/3\u2069؟"}]
    added = ot.offline_turn("fractions_addsub", history, "2/5")
    assert "جمعت أو طرحت البسطين والمقامين" in added.reply
    history = [{"role": "tutor", "content": "كم ناتج \u20662/3 \u00D7 3/4\u2069؟"}]
    loose = ot.offline_turn("mixed_mult", history, "6/12")
    assert "إجابة صحيحة" in loose.reply and "أبسط صورة" in loose.reply


def test_fraction_explain_and_free_typed_fractions():
    for skill in ("fractions_addsub", "mixed_addsub", "mixed_mult", "mixed_div"):
        reply = ot.offline_turn(skill, [], "اشرح لي الدرس").reply
        assert "مثال محلول" in reply and "الناتج" in reply, skill
    typed = ot.offline_turn("mixed_div", [], "ما ناتج 3/4 \u00F7 1/2").reply
    assert "3/2" in typed


def test_every_fraction_pool_item_is_solvable():
    for skill, items in ot.FR_POOL.items():
        for item in items:
            solved = ot.solve_fraction(item)
            assert solved is not None and solved[1] is not None and solved[1] > 0, (skill, item)
            assert ot.pending_question([{"role": "tutor", "content": ot.question_text("FR:" + item)}])[0] == "frac"
