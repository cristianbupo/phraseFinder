"""Whether a channel's videos play inside another website, as they must in the app.

Some owners (all of TRT, many cartoons) let their videos play on YouTube only: the player in the
app then says "This video is unavailable" (YouTube's error 150). YouTube's oEmbed, which the app
asks for titles, says yes to those videos all the same, so only a real player can tell.

Takes a few videos of each channel and plays them, muted, in headless Chrome (Playwright), from
a blank page on this computer. Run with the Python that has Playwright, PYTHONPATH set to this repo:

    python tools/check_embed.py handle handle ...

Check this before downloading a new channel, together with check_subtitles.py.
"""
import itertools, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import scrapetube, scrapetube.scrapetube as st
from playwright.sync_api import sync_playwright
import channelSearcher as c

st.type_property_map["videos"] = "lockupViewModel"
PROBE = """async (ids) => {
  await new Promise((ready) => { if (window.YT && YT.Player) return ready();
    window.onYouTubeIframeAPIReady = ready; const s = document.createElement('script');
    s.src = 'https://www.youtube.com/iframe_api'; document.head.appendChild(s); });
  const out = {};
  await Promise.all(ids.map((id, i) => new Promise((done) => {
    const d = document.createElement('div'); d.id = 'probe' + i; document.body.appendChild(d);
    const t = setTimeout(() => { out[id] = 'no answer'; done(); }, 25000);
    new YT.Player(d.id, { videoId: id, width: 160, height: 90, playerVars: { autoplay: 1, mute: 1 },
      events: { onReady: (e) => { e.target.mute(); e.target.playVideo(); },
                onStateChange: (e) => { if (e.data === 1) { out[id] = 'plays'; clearTimeout(t); done(); } },
                onError: (e) => { out[id] = 'blocked ' + e.data; clearTimeout(t); done(); } } });
  })));
  return out;
}"""

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
    page = browser.new_page()
    # A real address, as the app has: a player on about:blank is refused for its own reasons.
    page.route("https://probe.example/", lambda r: r.fulfill(body="<html><body></body></html>", content_type="text/html"))
    page.goto("https://probe.example/")
    for handle in sys.argv[1:]:
        try:
            cid = c.get_channel_id_from_url(f"https://www.youtube.com/@{handle}")
            vids = [v["contentId"] for v in itertools.islice(scrapetube.get_channel(channel_id=cid, sleep=0), 40)][::10][:4]
            found = page.evaluate(PROBE, vids)
            plays = sum(found.get(v) == "plays" for v in vids)
            print(f"@{handle}: {plays}/{len(vids)} play inside the app | {[found.get(v) for v in vids]}", flush=True)
            page.evaluate("document.body.innerHTML = ''")
        except Exception as e:
            print(f"@{handle}: ERR {repr(e)[:120]}", flush=True)
    browser.close()
