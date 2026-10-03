"""Downloads the subtitles of given videos into one folder, as channelSearcher.py does for a channel.
For a show inside a channel (a playlist, a search of the channel): Profesor Súper O and Los puros
criollos of Señal Colombia were taken this way. Run with PYTHONPATH set to this repo:

    python tools/download_ids.py <Folder_name> <es|fr|tr> <video id> <video id> ...

The folder gets a video_list.txt and a lang.txt, so push_to_app.sh files it like a channel.
"""
import json, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import channelSearcher as c
folder, lang, ids = sys.argv[1], sys.argv[2], sys.argv[3:]
path = os.path.join("transcripts", folder); os.makedirs(path, exist_ok=True)
open(os.path.join(path, "lang.txt"), "w", encoding="utf-8").write(lang)
open(os.path.join(path, "video_list.txt"), "w", encoding="utf-8").write("\n".join(ids) + "\n")
ydl = c.make_ytdlp(); saved = failed = 0
for v in ids:
    out = os.path.join(path, v + ".json")
    if os.path.exists(out): continue
    try:
        t = c.fetch_transcript_ytdlp(ydl, v, lang)
        json.dump(t, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2); saved += 1
    except Exception as e:
        failed += 1; print("  no:", v, type(e).__name__, str(e)[:60])
print(folder, "saved", saved, "failed", failed)
