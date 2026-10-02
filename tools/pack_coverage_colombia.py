import json, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import server
con = server.db()
packs = json.loads(server.PACKS.read_text(encoding="utf-8"))["es"]
CO = ("Caracol", "CanalRCN", "Canal RCN", "ColombianSpanish", "DianaUribe", "LaPulla", "ShotsdeCiencia", "RCN", "Suso", "Andres", "Juanpis", "LosInformantes", "Los Informantes", "Séptimo", "Señal", "Magic", "oficial", "Sábados", "Desafío")
chans = dict(con.execute("SELECT id, name FROM channels WHERE lang='es'"))
co_ids = server.id_list([i for i, n in chans.items() if (n.startswith(CO) or n.replace(" ", "").startswith(CO))])
all_ids = server.id_list(list(chans))
print("Colombian channels:", [n for n in chans.values() if (n.startswith(CO) or n.replace(" ", "").startswith(CO))])
thin_all, thin_co = [], []
for pack in packs:
    for ph in pack["phrases"]:
        where, params = server.match_sql(server.tokens_of(ph["p"]), "phrase")
        q = "SELECT count(*) FROM fts JOIN lines l ON l.id = fts.rowid JOIN videos v ON v.id = l.video WHERE {} AND v.channel IN ({})"
        (n,) = con.execute(q.format(where, all_ids), params).fetchone()
        if 5 <= n < 20: thin_all.append((n, ph["p"], pack["title"]))
        if pack.get("section") == "Colombia":
            (c,) = con.execute(q.format(where, co_ids), params).fetchone()
            if c < 10: thin_co.append((c, n, ph["p"], pack["title"]))
print("\n-- phrases with 5 to 19 clips:")
for n, p, t in sorted(thin_all): print(f"  {n:3} | {p}  [{t}]")
print("\n-- Colombia-pack phrases with fewer than 10 clips from Colombian channels (colombian / all):")
for c, n, p, t in sorted(thin_co): print(f"  {c:3} / {n:4} | {p}  [{t}]")
tot = sum(len(p["phrases"]) for p in packs if p.get("section") == "Colombia")
print(f"\nColombia phrases: {tot}, of which under 10 Colombian clips: {len(thin_co)}")
