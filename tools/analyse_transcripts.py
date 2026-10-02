import re, sys, json, collections, os, glob
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = "transcripts/es"
NOISE = re.compile(r"^\W*(\[[^\]]*\]|\([^)]*\)|♪.*|>>)?\W*$")
ES = set("que los las una por con para pero como más esto está muy porque también cuando de la el en y no es lo me se te si ya yo mi su le eso qué".split())
EN = set("the and you that this with for have what not are was but they your know just of to is it in we he she".split())
stats = {}; rows = []
for folder in sorted(os.listdir(ROOT)):
    path = os.path.join(ROOT, folder)
    if not os.path.isdir(path): continue
    seen = collections.Counter(); vids = []
    for f in glob.glob(os.path.join(path, "*.json")):
        try: data = json.load(open(f, encoding="utf-8"))
        except Exception: data = None
        size = os.path.getsize(f)
        if not isinstance(data, list): vids.append([f, size, 0, 0, set(), 0, 0, 0.0]); continue
        texts = [str(e.get("text", "")).replace("\n", " ").strip() for e in data if isinstance(e, dict)]
        n_noise = sum(1 for t in texts if NOISE.match(t))
        words = " ".join(texts).lower().split()
        es = sum(w in ES for w in words); en = sum(w in EN for w in words)
        dur = 0.0
        if data and isinstance(data[-1], dict): dur = float(data[-1].get("start", 0)) + float(data[-1].get("duration", 0))
        long_t = {t.lower() for t in texts if len(t) >= 30}
        seen.update(long_t)
        vids.append([f, size, len(texts), n_noise, long_t, es, en, dur])
    tot = sum(v[2] for v in vids); mb = sum(v[1] for v in vids) / 1e6
    dup = 0; long_total = 0
    for v in vids:
        d = sum(1 for t in v[4] if seen[t] > 1); dup += d; long_total += len(v[4])
        rows.append(dict(ch=folder, f=v[0].replace("\\", "/"), size=v[1], lines=v[2], noise=v[3], long=len(v[4]), dup=d, es=v[5], en=v[6], dur=v[7]))
    sizes = sorted(v[2] for v in vids) or [0]
    stats[folder] = dict(videos=len(vids), lines=tot, mb=mb, noise=sum(v[3] for v in vids), dup=dup, long_total=long_total, med=sizes[len(sizes)//2], p90=sizes[int(len(sizes)*0.9)], mx=sizes[-1])
json.dump(rows, open(sys.argv[1], "w", encoding="utf-8"))
T = sum(s["lines"] for s in stats.values()); M = sum(s["mb"] for s in stats.values())
print(f"{'channel':34} {'videos':>6} {'MB':>6} {'lines':>9} {'share':>6} {'med':>5} {'p90':>6} {'max':>6} {'noise%':>6} {'repeat%':>7}")
for name, s in sorted(stats.items(), key=lambda kv: -kv[1]["lines"]):
    print(f"{name[:34]:34} {s['videos']:6} {s['mb']:6.0f} {s['lines']:9} {100*s['lines']/T:5.1f}% {s['med']:5} {s['p90']:6} {s['mx']:6} {100*s['noise']/max(s['lines'],1):5.1f}% {100*s['dup']/max(s['long_total'],1):6.1f}%")
print(f"{'TOTAL':34} {sum(s['videos'] for s in stats.values()):6} {M:6.0f} {T:9}")
