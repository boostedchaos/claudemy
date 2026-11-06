"""Line up a lesson's script.txt with whisper word times (words.json).
Usage: python3 align.py <lesson-dir>   ->  writes <lesson-dir>/timing.json
The script text is the truth; whisper only supplies times. Unmatched script words get
times interpolated from their neighbours. Prints the match rate so a bad run is visible."""
import json, re, sys, difflib
from pathlib import Path
d = Path(sys.argv[1])
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower().replace("’", "'"))
turns = []
for line in (d / "script.txt").read_text(encoding="utf-8").splitlines():
    m = re.match(r"^([AB]): (.*)", line.strip())
    if m:
        turns.append({"who": m.group(1), "words": re.sub(r"\[[a-z ]+\]\s*", "", m.group(2)).split()})
sw = [(ti, wi) for ti, t in enumerate(turns) for wi in range(len(t["words"]))]
ww = json.loads((d / "words.json").read_text())
a = [norm(turns[ti]["words"][wi]) for ti, wi in sw]; b = [norm(x["w"]) for x in ww]
times = [None] * len(sw)
for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
    for k in range(blk.size):
        times[blk.a + k] = (ww[blk.b + k]["s"], ww[blk.b + k]["e"])
matched = sum(t is not None for t in times)
i = 0
while i < len(times):
    if times[i] is None:
        j = i
        while j < len(times) and times[j] is None: j += 1
        s = times[i - 1][1] if i > 0 else 0.0
        e = times[j][0] if j < len(times) else s + 0.3 * (j - i)
        step = (e - s) / (j - i)
        for k in range(i, j): times[k] = (round(s + (k - i) * step, 2), round(s + (k - i + 1) * step, 2))
        i = j
    i += 1
out, k = [], 0
for t in turns:
    ws = []
    for w in t["words"]:
        ws.append({"w": w, "s": times[k][0], "e": times[k][1]}); k += 1
    out.append({"who": t["who"], "s": ws[0]["s"], "e": ws[-1]["e"], "words": ws})
(d / "timing.json").write_text(json.dumps(out))
ordered = all(out[i]["s"] <= out[i + 1]["s"] for i in range(len(out) - 1))
print(f"{d.name}: matched {matched} of {len(sw)} script words ({100 * matched / len(sw):.1f}%), "
      f"{len(out)} turns, starts in order: {ordered}, last word ends {out[-1]['e']}s")
