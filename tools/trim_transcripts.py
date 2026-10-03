"""Cuts each long transcript down to its best minutes, so the library stays small and no
channel crowds out the others. Run inside an app clone (it reads and rewrites transcripts/es
there, or the folder of the language named), with PYTHONPATH set to a clone that has a built
phrases.db. Without --apply it only reports.

    python trim_transcripts.py [--lang fr] [--apply]

From a big channel 10 minutes of a video are kept, from a small one (under 100,000 lines, where
the variety is and little is saved) 30 minutes. A video up to two minutes longer than that is
kept whole. From a longer one a single stretch is kept: the one with the most spoken lines that
other videos of the channel do not also say (theme songs, recaps, adverts). A stretch that holds
a topic-pack phrase with few clips always wins, and a video that says a phrase with very few
clips is not cut at all. What was cut is listed in trimmed.tsv in the language's folder. A cut file is
short, so a second run leaves it alone.
"""
import collections, glob, json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import server
LANG = sys.argv[sys.argv.index("--lang") + 1] if "--lang" in sys.argv else "es"
ROOT = "transcripts/" + LANG
APPLY = "--apply" in sys.argv
KEEP, KEEP_SMALL, SMALL = 600, 1800, 100_000   # seconds kept per video; a small channel, in lines
SLACK = 120                  # a video this much longer than what is kept is not worth cutting
RARE, RARE_CO = 150, 80      # a phrase with this few clips (in all, in Colombian channels) is protected
VERY_RARE = 40               # a video that says a phrase with this few clips stays whole
NOISE = re.compile(r"^\W*(\[[^\]]*\]|\([^)]*\)|♪.*|>>)?\W*$")
CO = ("Caracol", "CanalRCN", "Canal RCN", "ColombianSpanish", "DianaUribe", "LaPulla", "ShotsdeCiencia", "RCN", "Suso", "Andres", "Juanpis", "LosInformantes", "Los Informantes", "Séptimo", "Señal", "Magic", "oficial", "Sábados", "Desafío")

# where each topic-pack phrase is said: video -> second -> points for keeping that line
con = server.db()
chans = dict(con.execute("SELECT id, name FROM channels WHERE lang = ?", (LANG,)))
co = {i for i, n in chans.items() if n.startswith(CO) or n.replace(" ", "").startswith(CO)}
ids = server.id_list(list(chans))
phrases = []; bonus = collections.defaultdict(dict); whole = set()
for pack in json.loads(server.PACKS.read_text(encoding="utf-8")).get(LANG, []):
    for ph in pack["phrases"]:
        where, params = server.match_sql(server.tokens_of(ph["p"]), "phrase")
        hits = con.execute(f"SELECT v.yt, l.start, v.channel FROM fts JOIN lines l ON l.id = fts.rowid JOIN videos v ON v.id = l.video WHERE {where} AND v.channel IN ({ids})", params).fetchall()
        colombia = pack.get("section") == "Colombia"
        rare = len(hits) <= RARE or (colombia and sum(h[2] in co for h in hits) <= RARE_CO)
        phrases.append((ph["p"], pack["title"], colombia, hits))
        if len(hits) <= VERY_RARE: whole.update(h[0] for h in hits)
        for yt, start, _ in hits:
            bonus[yt][round(start, 3)] = bonus[yt].get(round(start, 3), 0) + (400 if rare else 2)
con.close()

def load(path):
    try: data = json.load(open(path, encoding="utf-8"))
    except Exception: return None
    return data if isinstance(data, list) and data and all(isinstance(e, dict) for e in data) else None
def said(e): return str(e.get("text", "")).replace("\n", " ").strip()

kept_range = {}; present = {}; log = []
print(f"{'channel':34} {'videos':>6} {'cut':>6} {'lines':>9} {'kept':>9} {'kept%':>6}")
T0 = T1 = TC = 0
for folder in sorted(os.listdir(ROOT)):
    files = glob.glob(os.path.join(ROOT, folder, "*.json"))
    if not files: continue
    seen = collections.Counter()   # long lines, by how many of the channel's videos say them
    size = 0
    for f in files:
        data = load(f)
        if data: seen.update({said(e).lower() for e in data if len(said(e)) >= 30}); size += len(data)
    keep = KEEP_SMALL if size < SMALL else KEEP
    before = after = cut = 0
    for f in files:
        data = load(f)
        if not data: continue
        yt = os.path.basename(f)[:-5]; present[yt] = folder
        before += len(data)
        starts = [float(e.get("start", 0)) for e in data]
        if starts[-1] + float(data[-1].get("duration", 0)) - starts[0] <= keep + SLACK or yt in whole or starts != sorted(starts):
            after += len(data); continue
        extra = bonus.get(yt, {})
        points = [(0 if NOISE.match(said(e)) or seen[said(e).lower()] >= 3 else 1) + extra.get(round(s, 3), 0) for e, s in zip(data, starts)]
        best = (-1, 0, 0); total = 0; i = 0
        for j, s in enumerate(starts):
            total += points[j]
            while s - starts[i] > keep: total -= points[i]; i += 1
            if total > best[0]: best = (total, i, j)
        _, i, j = best
        kept_range[yt] = (starts[i], starts[j])
        log.append(f"{yt}\t{folder}\t{int(starts[i])}\t{int(starts[j] + float(data[j].get('duration', 0)))}\t{len(data)}\t{j - i + 1}")
        after += j - i + 1; cut += 1
        if APPLY: open(f, "w", encoding="utf-8").write(json.dumps(data[i:j + 1], ensure_ascii=False))
    T0 += before; T1 += after; TC += cut
    print(f"{folder[:34]:34} {len(files):6} {cut:6} {before:9} {after:9} {100 * after / max(before, 1):5.1f}%")
print(f"{'TOTAL':34} {len(present):6} {TC:6} {T0:9} {T1:9} {100 * T1 / max(T0, 1):5.1f}%")

# what the cut leaves of each topic-pack phrase
def left(hits, only_co=False):
    n = 0
    for yt, start, ch in hits:
        if yt not in present or (only_co and ch not in co): continue
        lo, hi = kept_range.get(yt, (start, start))
        n += lo <= start <= hi
    return n
counts = sorted((left(h), p, t) for p, t, _, h in phrases)
print(f"\ntopic-pack phrases: {len(counts)}, fewest clips left {counts[0][0]}, median {counts[len(counts) // 2][0]}")
for n, p, t in counts:
    if n < 20: print(f"  only {n} clips left | {p}  [{t}]")
for p, t, colombia, h in phrases:
    if colombia and left(h, True) < 10: print(f"  only {left(h, True)} Colombian clips left | {p}  [{t}]")
if APPLY and log:
    path = os.path.join(ROOT, "trimmed.tsv")
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8", newline="\n") as out:
        if new: out.write("video\tchannel\tkept from second\tkept to second\tlines before\tlines kept\n")
        out.write("\n".join(log) + "\n")
    print(f"\n{len(log)} files cut, listed in {path}")
elif not APPLY: print("\nNothing was changed. Add --apply to cut the files.")
