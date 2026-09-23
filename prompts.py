"""Prompt templates for generating diagnostic questions with an LLM."""
from __future__ import annotations

import random

import knowledge_graph as kg

SYSTEM_PROMPT = """\
You are Juthoor's Question Architect: an expert 6th-grade mathematics teacher and \
assessment designer. You write ONE diagnostic multiple-choice question at a time for a \
student aged 11-12.

# Purpose
The question must measure exactly ONE skill, so that a wrong answer tells the teacher \
WHY the student is stuck. Every wrong option must be the result of a specific, common \
misconception or procedural error. Random wrong numbers are not allowed.

# Rules
1. Test only the target skill. Keep any incidental arithmetic simple (clean numbers) so a \
mistake can be blamed on the target skill and not on something else.
2. Match the requested difficulty exactly, using the difficulty description you are given.
3. Provide exactly 1 correct answer and exactly 3 distractors. Each distractor needs a \
"misconception" label of at most 12 words that names the error that produces it. \
Use the known errors listed in the request when they fit.
4. All 4 answers must be different in VALUE, not just in format. Never offer two \
equivalent fractions (such as 1/2 and 2/4) if either could be argued to be correct.
5. Notation: plain text only. Fractions as a/b, mixed numbers as "2 1/3", use x and / or the \
symbols and ÷. No LaTeX, no markdown, no emojis.
6. Word problems: use the given context theme, at most 2 sentences (3 at difficulty 3), \
no names of real people or brands. Keep numbers realistic.
7. Language: write "question", "hint", "explanation" and "misconception" in the requested \
language. Always keep numerals as Western digits (0-9).
8. Work out the solution in "solution_steps" BEFORE writing "correct_answer", and \
double-check the arithmetic. If you cannot reach one unambiguous correct answer, \
change the question.
9. "hint": a nudge toward the method that does NOT reveal the answer. \
"explanation": at most 2 kid-friendly sentences that show the method and name the trap.
10. Do not try to place the correct answer in any particular position; the app shuffles.
11. Do not repeat or closely resemble any question listed under "Avoid".

# Output format
Return ONE JSON object and nothing else (no markdown fences, no commentary):
{
  "solution_steps": "<short working, max 3 lines>",
  "question": "<the question text>",
  "correct_answer": "<answer text>",
  "distractors": [
    {"text": "<wrong answer 1>", "misconception": "<why a student would pick it>"},
    {"text": "<wrong answer 2>", "misconception": "<...>"},
    {"text": "<wrong answer 3>", "misconception": "<...>"}
  ],
  "hint": "<hint>",
  "explanation": "<explanation>"
}
"""

USER_PROMPT_TEMPLATE = """\
Create one question.

Target skill: {skill_name} - {skill_description}
Prerequisite skills (do not test them, only rely on them lightly): {prerequisites}
Difficulty: {difficulty} of 3 - {difficulty_description}
Known errors for this skill: {typical_errors}
{misconception_block}Language: {language}
Context theme (only if you write a word problem): {theme}
Avoid these recent questions:
{recent_questions}
Variation seed: {seed}
"""

MISCONCEPTION_LINE = (
    "This is a REMEDIATION step: the student just failed a harder question because of this "
    "exact misconception: {misconception}. Write a simpler 'stepping-stone' question that "
    "isolates and directly targets that misconception -- do not just repeat the harder skill.\n"
)

# Everyday contexts familiar to students in the region; keeps word problems fresh.
THEMES = [
    "olive harvest", "school football match", "baking knafeh", "school library",
    "bus ride across the city", "garden and vegetables", "classroom art project",
    "market shopping in dinars", "water tank on a roof", "planting trees",
    "family picnic", "science-lab experiment",
]


def build_messages(skill_id: str, difficulty: int, language: str = "English",
                   recent: list[str] | None = None, misconception: str | None = None) -> list[dict]:
    """
    Return the chat messages (system + user) for the LLM.

    `misconception`, when given, is the exact wrong-answer trap diagnosed from the
    student's last answer (see practice.diagnose). Passing it turns this into a
    targeted remediation prompt instead of a generic question for the skill.
    """
    skill = kg.SKILLS[skill_id]
    pres = [kg.SKILLS[p].name for p in skill.prerequisites] or ["none"]
    recent_block = "\n".join(f"- {q}" for q in (recent or [])[-5:]) or "- (none yet)"
    user = USER_PROMPT_TEMPLATE.format(
        skill_name=skill.name,
        skill_description=skill.description,
        prerequisites=", ".join(pres),
        difficulty=difficulty,
        difficulty_description=skill.ladder[difficulty - 1],
        typical_errors="; ".join(skill.typical_errors),
        misconception_block=MISCONCEPTION_LINE.format(misconception=misconception) if misconception else "",
        language=language,
        theme=random.choice(THEMES),
        recent_questions=recent_block,
        seed=random.randint(1000, 9999),
    )
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]