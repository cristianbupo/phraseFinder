import itertools, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import scrapetube, scrapetube.scrapetube as st
import channelSearcher as c
st.type_property_map["videos"] = "lockupViewModel"
ydl = c.make_ytdlp()
for handle in sys.argv[1:]:
    try:
        cid = c.get_channel_id_from_url(f"https://www.youtube.com/@{handle}")
        vids = list(itertools.islice(scrapetube.get_channel(channel_id=cid, sleep=0), 60))
        sample = vids[::12][:5]
        res, titles = [], []
        for v in sample:
            title = v["metadata"]["lockupMetadataViewModel"]["title"]["content"]
            titles.append(title[:60])
            try:
                info = ydl.extract_info("https://www.youtube.com/watch?v=" + v["contentId"], download=False)
                manual = [k for k in (info.get("subtitles") or {}) if k.startswith("es")]
                auto = [k for k in (info.get("automatic_captions") or {}) if k.endswith("-orig")]
                dur = int(info.get("duration") or 0)
                if manual: res.append(f"es written ({dur//60}m)")
                elif any(a.startswith("es") for a in auto): res.append(f"es auto ({dur//60}m)")
                elif auto: res.append(f"{auto[0]} only")
                else: res.append("none")
            except Exception as e:
                res.append("ERR " + str(e)[:40])
            time.sleep(1.5)
        ok = sum(r.startswith("es") for r in res)
        print(f"\n@{handle}: {ok}/{len(res)} with Spanish subtitles | {res}")
        for t in titles[:3]: print("     -", t)
    except Exception as e:
        print(f"\n@{handle}: ERR {repr(e)[:120]}")
