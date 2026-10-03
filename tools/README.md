# Tools for growing the Phrase Finder library

Run from Git Bash in the phraseFinder folder, with the `.venv` that has yt-dlp.

| File | What it does |
|---|---|
| `find_channels.py "name" "name"` | Searches YouTube for channels by name: handle, subscribers, verified |
| `check_subtitles.py handle handle` | Samples 5 videos per channel and says whether they have Spanish subtitles (needs `PYTHONPATH` set to this repo). Another language: `CS_LANG=tr python tools/check_subtitles.py handle` |
| `check_embed.py handle handle` | Plays 4 videos per channel in a player inside another page, as the app does, and says whether they play: some owners (all of TRT) allow YouTube only, and those videos are useless in the app. Check it with `check_subtitles.py` before a download. Needs Playwright: `PYTHONPATH=".;<Python user site-packages>" .venv/Scripts/python tools/check_embed.py handle` |
| `download_round.sh "0,0" 150 handle handle=1/4 ...` | Downloads several channels at once; `handle=i/n` splits one channel between n downloads. Spanish unless `CS_LANG` says otherwise: `CS_LANG=fr tools/download_round.sh "0,0" 150 handle ...` (`tr` for Turkish). It ends with exit code 2 when one channel failed many times in a row: usually a channel without subtitles, not YouTube blocking (look at whether the other channels finished) |
| `push_to_app.sh` | Copies new transcripts into the clean clone `phrase-finder-app-push` and pushes; a channel goes to `transcripts/es`, `transcripts/fr` or `transcripts/tr` by its `lang.txt` (written by `channelSearcher.py`; Spanish without one; a `lang.txt` that says `skip` keeps the channel out of the app); skips ids in that language's `removed.tsv`; `COPY_ONLY=1 tools/push_to_app.sh` only copies, so a download can be cleaned and cut (`trim_transcripts.py`) in the clone before the real run commits it |
| `download_ids.py Folder es id id ...` | Downloads given videos into one folder (a show inside a channel: a playlist, a search of the channel); the folder is then pushed like a channel. `PYTHONPATH` set to this repo |
| `find_foreign.py es Channel ... [--apply]` | New channels: transcripts in another language than the channel's (Korean, Hindi, Dutch: dubbed-show channels have them); run inside the app clone |
| `analyse_transcripts.py out.json` | Per channel: size, video length, noise and repeated lines (run inside the app clone) |
| `find_useless.py out.json delete.json` | Marks repeats, empty, music-only and non-Spanish transcripts |
| `trim_transcripts.py [--apply]` | Cuts long Spanish videos to their best 10 minutes (30 in a small channel) and lists them in `transcripts/es/trimmed.tsv`; without `--apply` it only reports (run inside the app clone after `build_index.py`, `PYTHONPATH` set to it) |
| `pack_coverage.py out.json` | Clips per topic-pack phrase, after `build_index.py` (run inside the app clone, `PYTHONPATH` set to it) |
| `pack_coverage_colombia.py` | The same, counting Colombian channels only |
