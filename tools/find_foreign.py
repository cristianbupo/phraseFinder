"""Transcripts whose words are plainly not in the channel's language (Korean, Hindi, Dutch, English...).
find_useless.py only weighs Spanish against English; dubbed-show channels (Disney+, Hulu, WB Kids)
also carry videos subtitled in other languages. Run inside the app clone:

    python find_foreign.py <es|fr> <Channel_folder> ... [--apply]

--apply deletes them and lists them in that language's removed.tsv. Without it, only a report.
"""
import glob, json, os, re, sys, unicodedata
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv
lang, chans = sys.argv[1], [a for a in sys.argv[2:] if a != "--apply"]
COMMON = {"es": set("que de la el en y no es lo me se te si ya yo mi su le eso qué los las una un por con para pero como más esto está muy porque también cuando a al del esta este".split()),
          "fr": set("les des est pas une dans pour qui vous nous mais avec c'est très aussi cette tout être alors de la le et je tu il on que ne ce un en à ça j'ai elle au du".split())}[lang]
WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*")
out = []
for ch in chans:
    for f in glob.glob(f"transcripts/{lang}/{ch}/*.json"):
        text = " ".join(str(e.get("text", "")) for e in json.load(open(f, encoding="utf-8")) if isinstance(e, dict)).lower()
        words = WORD.findall(text)
        if len(words) < 20: continue
        letters = [c for c in text if c.isalpha()]
        latin = sum("LATIN" in unicodedata.name(c, "") for c in letters) / max(len(letters), 1)
        share = sum(w in COMMON for w in words) / len(words)
        # Under 0.12 of little words is another language; songs and trailers sit between 0.12 and 0.2: read those.
        if latin < 0.8 or share < 0.12:
            out.append((ch, os.path.basename(f)[:-5], round(latin, 2), round(share, 2), len(words), " ".join(words[:9])))
for r in sorted(out): print(*r, sep=" | ")
print(len(out), "flagged")
if APPLY:
    for ch, vid, *_ in out:
        os.remove(f"transcripts/{lang}/{ch}/{vid}.json")
        with open(f"transcripts/{lang}/removed.tsv", "a", encoding="utf-8", newline="") as t:
            t.write(f"{vid}\t{ch}\tnot in {'Spanish' if lang == 'es' else 'French'}\r\n")
