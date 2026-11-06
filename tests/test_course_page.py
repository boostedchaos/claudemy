"""Tests for the course page: align.py and build_course_page.py. Stdlib only.

Run from the repo root:  python3 -m unittest discover -s tests
"""
import contextlib
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "claudemy" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_course_page  # noqa: E402

PLAN = """# Lesson plan

## Arc 1. First steps (lessons 1 to 2)

Why this arc: start small.

### Lesson 1. Two Columns
- Agree: 8 of 15.
- Idea: sort what you face into two columns.
- Try it: write one worry.

### Lesson 2. The Pause
- Agree: 8 of 14.
- Idea: take a breath before you agree.
- Try it: pause once.

## Splits
"""

CARD = """# Lesson 1. Two Columns

**Listen:** two-columns.mp3 (2:20)

**The idea, in three lines**
- Some things are up to you.
- Some are not.
- Act on your column.

**Impact:** worries get smaller.

**Who says it:** 8 of 15 sources agree.

**Try it** · Quick Win · 5 min
1. Write one worry.
2. Draw a line.

**Rule to keep**
RULE_TEXT

**Skip** · no cost, no catch-up. Lesson 2 is just lesson 2.

**Go deeper (optional)**
- The handbook: https://example.org/handbook
"""

SCRIPT = "A: Lesson one. Two columns.\nB: [laughs] Okay, go.\n"


def make_workspace(root, rule="When I worry, I sort it.", timing=True):
    ws = Path(root) / "topic"
    lesson = ws / "class" / "01-two-columns"
    lesson.mkdir(parents=True)
    (ws / "sources.json").write_text(json.dumps({"topic": "Stoicism", "pages": []}))
    (ws / "class" / "lesson-plan.md").write_text(PLAN)
    (lesson / "card.md").write_text(CARD.replace("RULE_TEXT", rule), encoding="utf-8")
    (lesson / "script.txt").write_text(SCRIPT)
    (lesson / "two-columns.mp3").write_bytes(b"ID3")
    if timing:
        words = [{"w": w, "s": i * 0.5, "e": i * 0.5 + 0.4} for i, w in
                 enumerate(["Lesson", "won.", "Two", "columns.", "Okay,", "go."])]
        (lesson / "words.json").write_text(json.dumps(words))
    return ws, lesson


def course_data(html):
    """The COURSE object embedded in the page, exactly as the browser will parse it."""
    raw = re.search(r"const COURSE = (.*?);\n", html, re.S).group(1)
    return raw, json.loads(raw)


def build(ws, *args, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        build_course_page.build(ws, *args, **kw)
    return (ws / "class" / "course.html").read_text(encoding="utf-8")


class AlignTest(unittest.TestCase):
    def test_script_text_wins_and_unmatched_words_get_neighbour_times(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, lesson = make_workspace(tmp)
            out = subprocess.run([sys.executable, str(SCRIPTS / "align.py"), str(lesson)],
                                 capture_output=True, text=True, check=True).stdout
            self.assertIn("matched 5 of 6 script words", out)  # "won." was misheard for "one."
            turns = json.loads((lesson / "timing.json").read_text())
            self.assertEqual([t["who"] for t in turns], ["A", "B"])
            words = [w for t in turns for w in t["words"]]
            self.assertEqual([w["w"] for w in words], ["Lesson", "one.", "Two", "columns.", "Okay,", "go."])
            self.assertNotIn("[laughs]", [w["w"] for w in words])
            starts = [w["s"] for w in words]
            self.assertEqual(starts, sorted(starts))
            self.assertTrue(words[0]["e"] <= words[1]["s"] <= words[2]["s"])


class BuildCoursePageTest(unittest.TestCase):
    def test_builds_every_planned_lesson_and_marks_the_made_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws, _ = make_workspace(tmp, timing=False)
            _, course = course_data(build(ws))
            lessons = [l for a in course["arcs"] for l in a["lessons"]]
            self.assertEqual([l["n"] for l in lessons], [1, 2])
            self.assertEqual([l["made"] for l in lessons], [True, False])
            one = lessons[0]
            self.assertEqual(one["audio"], "01-two-columns/two-columns.mp3")
            self.assertEqual((one["tryEnergy"], one["tryTime"]), ("Quick Win", "5 min"))
            self.assertEqual(one["trySteps"], ["Write one worry.", "Draw a line."])
            self.assertEqual(one["links"], [{"text": "The handbook", "url": "https://example.org/handbook"}])
            self.assertFalse(one["timed"])
            self.assertEqual(course["title"], "Stoicism")  # title defaults to the topic

    def test_voices_and_title_are_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws, _ = make_workspace(tmp, timing=False)
            _, course = course_data(build(ws, "My course", ("Samantha", "Daniel")))
            self.assertEqual(course["title"], "My course")
            self.assertEqual(course["voices"], {"A": "Samantha", "B": "Daniel"})

    def test_lesson_text_cannot_break_out_of_the_script(self):
        # Escaping only "</" left "<!--<script>" able to keep the real </script> from closing: a blank page.
        planted = "Keep it </script><!--<script>alert(1)</script> simple."
        with tempfile.TemporaryDirectory() as tmp:
            ws, _ = make_workspace(tmp, rule=planted, timing=False)
            html = build(ws)
            raw, course = course_data(html)
            self.assertNotIn("<", raw)
            self.assertEqual(html.count("</script>"), 1)
            self.assertEqual(course["arcs"][0]["lessons"][0]["rule"], planted)


if __name__ == "__main__":
    unittest.main()
