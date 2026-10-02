import json, sys, statistics
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import server
con = server.db()
packs = json.loads(server.PACKS.read_text(encoding="utf-8"))
out = {}
for lang in ("es", "en"):
    in_lang = server.id_list(server.lang_channels(lang))
    rows = []
    for pack in packs[lang]:
        for ph in pack["phrases"]:
            where, params = server.match_sql(server.tokens_of(ph["p"]), "phrase")
            (n,) = con.execute(f"SELECT count(*) FROM fts JOIN lines l ON l.id = fts.rowid JOIN videos v ON v.id = l.video WHERE {where} AND v.channel IN ({in_lang})", params).fetchone()
            (ch,) = con.execute(f"SELECT count(DISTINCT v.channel) FROM fts JOIN lines l ON l.id = fts.rowid JOIN videos v ON v.id = l.video WHERE {where} AND v.channel IN ({in_lang})", params).fetchone()
            rows.append((pack.get("section", ""), pack.get("level", ""), pack["title"], ph["p"], n, ch))
    out[lang] = rows
    ns = [r[4] for r in rows]
    print(f"== {lang}: {len(packs[lang])} packs, {len(rows)} phrases | 0 clips: {sum(n == 0 for n in ns)} | 1-4: {sum(1 <= n < 5 for n in ns)} | 5-19: {sum(5 <= n < 20 for n in ns)} | 20+: {sum(n >= 20 for n in ns)} | median {statistics.median(ns)}")
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False)
rows = out["es"]
print("\n-- Spanish packs (section | level | title : phrases, with <5 clips, min, median)")
seen = []
for r in rows:
    key = (r[0], r[1], r[2])
    if key not in seen: seen.append(key)
for key in seen:
    ph = [r for r in rows if (r[0], r[1], r[2]) == key]
    ns = [r[4] for r in ph]
    print(f"{key[0][:22]:22} | {key[1]:3} | {key[2][:38]:38}: {len(ph):2} phrases, {sum(n < 5 for n in ns)} thin, min {min(ns)}, median {int(statistics.median(ns))}")
print("\n-- Spanish phrases with fewer than 5 clips")
for r in sorted(rows, key=lambda r: r[4]):
    if r[4] < 5: print(f"  {r[4]:3} clips in {r[5]} channels | {r[3]}  [{r[2]}]")
