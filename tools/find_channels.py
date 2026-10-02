import json, re, sys, time, requests
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
shows = sys.argv[1:]
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36", "Accept-Language": "es"})
S.cookies.set("SOCS", "CAI", domain=".youtube.com")
def walk(o, key):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key: yield v
            else: yield from walk(v, key)
    elif isinstance(o, list):
        for v in o: yield from walk(v, key)
out = []
for q in shows:
    try:
        r = S.get("https://www.youtube.com/results", params={"search_query": q, "sp": "EgIQAg=="}, timeout=20)
        m = re.search(r"var ytInitialData = (\{.*?\});</script>", r.text, re.S)
        data = json.loads(m.group(1))
        chans = list(walk(data, "channelRenderer"))[:3]
        for c in chans:
            title = c["title"]["simpleText"]
            handle = (c.get("subscriberCountText") or {}).get("simpleText", "")
            subs = (c.get("videoCountText") or {}).get("simpleText", "")
            verified = any("VERIFIED" in json.dumps(b) for b in c.get("ownerBadges", []))
            print(f"{q:28} | {title[:34]:34} | {handle:26} | {subs:22} | {'verified' if verified else ''} | {c['channelId']}")
    except Exception as e:
        print(q, "ERR", repr(e)[:100])
    time.sleep(1)
