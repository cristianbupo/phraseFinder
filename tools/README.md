# Tools for growing the Phrase Finder library

Run from Git Bash in the phraseFinder folder, with the `.venv` that has yt-dlp.

| File | What it does |
|---|---|
| `find_channels.py "name" "name"` | Searches YouTube for channels by name: handle, subscribers, verified |
| `check_subtitles.py handle handle` | Samples 5 videos per channel and says whether they have Spanish subtitles (needs `PYTHONPATH` set to this repo; change `"es"` for another language) |
| `download_round.sh "0,0" 150 handle handle=1/4 ...` | Downloads several channels at once; `handle=i/n` splits one channel between n downloads |
| `push_to_app.sh` | Copies new transcripts into the clean clone `phrase-finder-app-push` and pushes; skips ids in `transcripts/es/removed.tsv` |
| `analyse_transcripts.py out.json` | Per channel: size, video length, noise and repeated lines (run inside the app clone) |
| `find_useless.py out.json delete.json` | Marks repeats, empty, music-only and non-Spanish transcripts |
| `pack_coverage.py out.json` | Clips per topic-pack phrase, after `build_index.py` (run inside the app clone, `PYTHONPATH` set to it) |
| `pack_coverage_colombia.py` | The same, counting Colombian channels only |
