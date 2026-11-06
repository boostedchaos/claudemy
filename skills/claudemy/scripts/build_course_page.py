"""Build one offline course page for a Claudemy workspace.

Usage: python3 build_course_page.py <workspace> ["<course title>"] [--voices "Liam,Jessica"]
       Title defaults to the topic in sources.json. --voices names host A and host B on the
       read-along (render_audio.py's ElevenLabs defaults are Liam and Jessica; macOS say uses
       Samantha and Daniel).
Reads  class/lesson-plan.md (arcs, all lessons), and for each made lesson
       class/NN-*/card.md, script.txt, *.mp3 and timing.json (optional, from align.py).
Writes class/course.html next to the lesson folders, so audio paths stay relative.
"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def section(card, start, stop):
    i = card.index(start) + len(start)
    j = card.index(stop, i)
    return card[i:j].strip()


def build(ws, title=None, voices=("Liam", "Jessica")):
    plan = (ws / "class/lesson-plan.md").read_text(encoding="utf-8")
    arcs = []
    for m in re.finditer(r"^## Arc \d+\. (.+?) \(lessons [^)]*\)\n+Why this arc: (.+?)(?=\n\n)", plan, re.M | re.S):
        arcs.append({"title": m.group(1).strip(), "why": " ".join(m.group(2).split()), "lessons": []})
    if not arcs:
        sys.exit("no '## Arc N. Title (lessons ...)' headings found in lesson-plan.md")
    for n, handle, body in re.findall(r"^### Lesson (\d+)\. (.+?)\n(.*?)(?=^### |^## )", plan, re.M | re.S):
        n = int(n)
        idea = re.search(r"- Idea: (.+?)(?=\n- )", body, re.S)
        arc_i = re.findall(r"^## Arc (\d+)\.", plan[: plan.index(f"### Lesson {n}.")], re.M)
        arcs[int(arc_i[-1]) - 1]["lessons"].append(
            {"n": n, "handle": handle.strip(), "idea": " ".join(idea.group(1).split()) if idea else "", "made": False})
    by_n = {l["n"]: l for a in arcs for l in a["lessons"]}
    for d in sorted((ws / "class").glob("[0-9][0-9]-*")):
        mp3 = sorted(d.glob("*.mp3"))
        card = (d / "card.md").read_text(encoding="utf-8")
        les = by_n[int(d.name[:2])]
        trys = section(card, "**Try it**", "**Rule to keep**").splitlines()
        energy, time = [x.strip() for x in trys[0].split("·")[1:3]]
        if (d / "timing.json").exists():
            transcript, timed = json.loads((d / "timing.json").read_text()), True
        else:
            transcript = [{"who": l[0], "words": [{"w": w} for w in re.sub(r"\[[a-z ]+\]\s*", "", l[3:]).split()]}
                          for l in (d / "script.txt").read_text(encoding="utf-8").splitlines() if re.match(r"^[AB]: ", l)]
            timed = False
        deeper = card.split("**Go deeper (optional)**")[1]
        les.update(
            made=bool(mp3), audio=f"{d.name}/{mp3[0].name}" if mp3 else None,
            length=re.search(r"\*\*Listen:\*\* \S+ \(([^)]+)\)", card).group(1),
            idea3=[l[2:] for l in section(card, "**The idea, in three lines**", "**Impact:**").splitlines() if l.startswith("- ")],
            impact=section(card, "**Impact:**", "**Who says it:**"),
            who=section(card, "**Who says it:**", "**Try it**"),
            tryEnergy=energy, tryTime=time,
            trySteps=[re.sub(r"^\d+\.\s*", "", l) for l in trys[1:] if re.match(r"^\d+\.", l)],
            rule=section(card, "**Rule to keep**", "**Skip**"),
            links=[{"text": m.group(1).rstrip(": "), "url": m.group(2)}
                   for m in re.finditer(r"^- (.+?)\s<?(https?://[^\s>]+)>?$", deeper, re.M)],
            transcript=transcript, timed=timed)
    topic = json.loads((ws / "sources.json").read_text(encoding="utf-8")).get("topic") if (ws / "sources.json").exists() else None
    title = title or topic or ws.name
    course = {"slug": ws.name, "title": title, "short": topic or title,
              "voices": {"A": voices[0], "B": voices[1]}, "arcs": arcs}
    tpl = (HERE / "course-template.html").read_text(encoding="utf-8")
    # Every "<" escaped, so no lesson text can close the script or open an HTML comment inside it.
    data = json.dumps(course, ensure_ascii=False).replace("<", "\\u003c")
    out = tpl.replace("/*COURSE*/null", data).replace("__TITLE__", title)
    (ws / "class/course.html").write_text(out, encoding="utf-8")
    made = [l for a in arcs for l in a["lessons"] if l["made"]]
    print(f"wrote {ws / 'class/course.html'}: {len(arcs)} arcs, {len(by_n)} lessons, "
          f"made {[l['n'] for l in made]}, timed {[l['n'] for l in made if l['timed']]}")


if __name__ == "__main__":
    args = sys.argv[1:]
    voices = ("Liam", "Jessica")
    if "--voices" in args:
        i = args.index("--voices")
        names = [v.strip() for v in args[i + 1].split(",")]
        if len(names) != 2 or not all(names):
            sys.exit('--voices takes two names, like "Liam,Jessica"')
        voices = tuple(names)
        del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    build(Path(args[0]).resolve(), args[1] if len(args) > 1 else None, voices)
