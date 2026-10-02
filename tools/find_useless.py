import re, sys, json, collections, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
rows = json.load(open(sys.argv[1], encoding="utf-8"))
by_ch = collections.defaultdict(list)
for r in rows: by_ch[r["ch"]].append(r)
def long_lines(path):
    data = json.load(open(path, encoding="utf-8"))
    return {str(e.get("text", "")).replace("\n", " ").strip().lower() for e in data if isinstance(e, dict) and len(str(e.get("text", "")).strip()) >= 30}
delete = {}   # file -> reason
for ch, vs in by_ch.items():
    for r in vs:
        real = r["lines"] - r["noise"]
        if r["lines"] == 0 or real < 8: delete[r["f"]] = "almost empty"
        elif r["noise"] / r["lines"] > 0.5: delete[r["f"]] = "mostly music or sound labels"
        elif r["en"] > r["es"]: delete[r["f"]] = "not in Spanish"
    # repeated content: longest first (marathons over 3000 lines last), drop a video when 70% of it is already kept
    order = sorted([r for r in vs if r["f"] not in delete and r["long"] >= 10], key=lambda r: (r["lines"] > 3000, -r["lines"]))
    kept = set()
    if sum(r["dup"] for r in vs) / max(sum(r["long"] for r in vs), 1) < 0.02:
        continue   # channel has no repeats worth reading files for
    for r in order:
        if r["dup"] / r["long"] < 0.7:
            kept |= long_lines(r["f"]); continue
        ll = long_lines(r["f"])
        if len(ll & kept) / len(ll) >= 0.7: delete[r["f"]] = "repeat of another video"
        else: kept |= ll
by_f = {r["f"]: r for r in rows}
json.dump(delete, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
print(f"{'channel':34} {'videos':>6} {'delete':>6} {'empty':>5} {'music':>5} {'notES':>5} {'repeat':>6} {'MB freed':>8} {'lines freed':>11} {'% of lines':>10}")
TL = TF = TM = TD = 0
for ch, vs in sorted(by_ch.items(), key=lambda kv: -sum(by_f[f]["lines"] for f in delete if by_f[f]["ch"] == kv[0])):
    d = [r for r in vs if r["f"] in delete]
    c = collections.Counter(delete[r["f"]] for r in d)
    lines = sum(r["lines"] for r in vs); freed = sum(r["lines"] for r in d); mb = sum(r["size"] for r in d) / 1e6
    TL += lines; TF += freed; TM += mb; TD += len(d)
    if d: print(f"{ch[:34]:34} {len(vs):6} {len(d):6} {c['almost empty']:5} {c['mostly music or sound labels']:5} {c['not in Spanish']:5} {c['repeat of another video']:6} {mb:8.0f} {freed:11} {100*freed/max(lines,1):9.1f}%")
print(f"{'TOTAL':34} {len(rows):6} {TD:6} {'':24} {TM:8.0f} {TF:11} {100*TF/TL:9.1f}%")
