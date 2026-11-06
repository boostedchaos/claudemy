"""Word timings for a lesson's audio, for the course page's read-along. Optional.
Needs mlx-whisper (Apple Silicon, free, offline):  pip install mlx-whisper
Usage: python3 time_words.py <lesson-dir>   ->  writes <lesson-dir>/words.json [{"w","s","e"}, ...] in seconds.
Then run align.py on the same folder. Without timings the page still shows the words; they just don't follow the audio."""
import json, sys
from pathlib import Path
import mlx_whisper
d = Path(sys.argv[1]); mp3 = next(d.glob("*.mp3"))
r = mlx_whisper.transcribe(str(mp3), path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                           word_timestamps=True, language="en")
words = [{"w": w["word"].strip(), "s": round(float(w["start"]), 2), "e": round(float(w["end"]), 2)}
         for seg in r["segments"] for w in seg.get("words", [])]
(d / "words.json").write_text(json.dumps(words))
print(f"{mp3.name}: {len(words)} words, last ends {words[-1]['e']}s")
