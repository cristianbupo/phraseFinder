import csv
import html
import json
import os
import random
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter

import requests
import scrapetube
import scrapetube.scrapetube as scrapetube_internals
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
)

# yt-dlp gets blocked far less than youtube_transcript_api; without it the old way is used
try:
    import yt_dlp
except ImportError:
    yt_dlp = None

# Skips the cookie consent page YouTube shows in Europe
REQUEST_COOKIES = {"SOCS": "CAI"}
REQUEST_TIMEOUT = 20
# Wait between downloads, so YouTube is less likely to block us
PAUSE_SECONDS = (1, 3)
# Stop after this many "you are blocked" answers in a row
BLOCKED_LIMIT = 3
# This many failures in a row means YouTube stopped answering, not that the videos lack subtitles
FAILED_STREAK_LIMIT = 8
# How long the saved list of a channel's videos is reused before listing the channel again
VIDEO_LIST_MAX_AGE_DAYS = 7
# Only list a channel's newest videos: listing 30,000 takes 15 minutes before anything is saved
VIDEO_LIST_LIMIT = 2000


def get_channel_id_from_url(url):
    if not url.startswith("http"):
        url = "https://" + url
    if "/channel/" in url:
        return url.split("/channel/")[1].split("/")[0].split("?")[0]
    try:
        response = requests.get(url, cookies=REQUEST_COOKIES, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, "html.parser")
        tag = soup.find("link", {"rel": "canonical"})
        if tag and "/channel/" in tag["href"]:
            return tag["href"].split("/channel/")[1].split("/")[0]
    except requests.RequestException as e:
        print(f"⚠️ Could not open {url}: {e}")
    return None


def get_channel_title(channel_id):
    url = f"https://www.youtube.com/channel/{channel_id}"
    try:
        response = requests.get(url, cookies=REQUEST_COOKIES, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(response.text, "html.parser")
        title_tag = soup.find("meta", property="og:title")
        if title_tag:
            title = title_tag["content"].replace(" - YouTube", "").replace(" ", "_")
            # Remove characters that are not allowed in folder names
            title = re.sub(r'[<>:"/\\|?*]', "", title).strip("._")
            if title:
                return title
    except requests.RequestException:
        pass
    return channel_id


def get_channel_video_ids(channel_id):
    """YouTube changed how it lists videos (videoRenderer -> lockupViewModel), so try both."""
    formats = getattr(scrapetube_internals, "type_property_map", None)
    for video_format, id_key in (("lockupViewModel", "contentId"), ("videoRenderer", "videoId")):
        if formats is not None:
            formats["videos"] = video_format
        video_ids = []
        seen = set()
        for video in scrapetube.get_channel(channel_id, limit=VIDEO_LIST_LIMIT, sleep=0.5):
            video_id = video.get(id_key)
            if video_id and video_id not in seen:
                seen.add(video_id)
                video_ids.append(video_id)
                print(f"\r⏳ Fetching videos... {len(video_ids)} found", end='')
        if video_ids or formats is None:
            print()
            return video_ids
    return []


def load_or_fetch_video_ids(channel_id, folder_path):
    """Listing a big channel takes minutes, so keep the list in the folder and reuse it."""
    list_path = os.path.join(folder_path, "video_list.txt")
    if os.path.exists(list_path):
        age_days = (time.time() - os.path.getmtime(list_path)) / 86400
        with open(list_path, encoding="utf-8") as f:
            video_ids = [line.strip() for line in f if line.strip()]
        if video_ids and age_days < VIDEO_LIST_MAX_AGE_DAYS:
            print(f"📋 Using the saved list of {len(video_ids)} videos (delete video_list.txt to list the channel again)")
            return video_ids
    video_ids = get_channel_video_ids(channel_id)
    if video_ids:
        with open(list_path, "w", encoding="utf-8") as f:
            f.write("\n".join(video_ids) + "\n")
    return video_ids


def progress_bar(done, total, width=30):
    filled = int(width * done / total)
    return f"[{'█' * filled}{'░' * (width - filled)}] {done}/{total} ({100 * done // total}%)"


class NoSubtitles(Exception):
    pass


class YouTubeBlocked(Exception):
    pass


def make_ytdlp():
    if yt_dlp is None:
        return None
    return yt_dlp.YoutubeDL({
        "skip_download": True,
        "ignore_no_formats_error": True,
        "quiet": True,
        "no_warnings": True,
        # YouTube blocks its phone app far less than a browser
        "extractor_args": {"youtube": {"player_client": ["android"]}},
    })


def pick_subtitle_track(info, language):
    """Preferred language first (written subtitles, then automatic ones);
    if the video does not have it, take the language the video is spoken in.
    Automatic translations are never used."""
    manual = {k: v for k, v in (info.get("subtitles") or {}).items() if k != "live_chat"}
    auto = info.get("automatic_captions") or {}
    original = [k for k in auto if k.endswith("-orig")] or [k for k in auto if k == info.get("language")]

    def matches(code):
        return code == language or code.startswith(language + "-")

    candidates = (
        [manual[k] for k in manual if matches(k)]
        + [auto[k] for k in original if matches(k)]
        + [auto[k] for k in original]
        + list(manual.values())
    )
    for formats in candidates:
        for track in formats:
            if track.get("ext") == "srv1":
                return track
    raise NoSubtitles()


def fetch_transcript_ytdlp(ydl, video_id, language):
    try:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        track = pick_subtitle_track(info, language)
        raw = ydl.urlopen(track["url"]).read().decode("utf-8")
    except NoSubtitles:
        raise
    except Exception as e:
        if "not a bot" in str(e) or "429" in str(e):
            raise YouTubeBlocked() from e
        raise
    # Same shape as youtube_transcript_api: one entry per subtitle line
    transcript = [
        {
            "text": html.unescape(line.text or ""),
            "start": float(line.attrib["start"]),
            "duration": float(line.attrib.get("dur", 0)),
        }
        for line in ET.fromstring(raw).iter("text")
        if (line.text or "").strip()
    ]
    if not transcript:
        raise NoSubtitles()
    return transcript


def fetch_transcript(api, video_id, language="en", ydl=None):
    """Preferred language first; if the video does not have it, take the language it does have."""
    if ydl is not None:
        return fetch_transcript_ytdlp(ydl, video_id, language)
    try:
        return api.fetch(video_id=video_id, languages=[language]).to_raw_data()
    except NoTranscriptFound:
        available = list(api.list(video_id))
        if not available:
            raise
        return available[0].fetch().to_raw_data()


def failure_reason(error):
    if isinstance(error, TranscriptsDisabled):
        return "subtitles are turned off"
    if isinstance(error, (NoTranscriptFound, NoSubtitles)):
        return "no transcript"
    if isinstance(error, VideoUnavailable):
        return "video unavailable"
    return f"{type(error).__name__}: {str(error)[:60]}".rstrip(": ")


def write_links_csv(folder_path):
    """One row per saved transcript, rebuilt each run so there are no duplicates."""
    csv_path = os.path.join(folder_path, "transcript_files.csv")
    video_ids = sorted(
        os.path.splitext(fn)[0] for fn in os.listdir(folder_path) if fn.endswith(".json")
    )
    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["youtube_url"])
        for video_id in video_ids:
            writer.writerow([f"https://www.youtube.com/watch?v={video_id}"])
    return csv_path


def fetch_and_save_transcripts(channel_url, language="en", max_new=None):
    """Returns True when YouTube blocked the run. max_new stops it after that many new transcripts."""
    channel_id = get_channel_id_from_url(channel_url)
    if not channel_id:
        print("❌ Could not extract Channel ID.")
        return

    print(f"✅ Channel ID: {channel_id}")
    channel_title = get_channel_title(channel_id)
    print(f"🔖 Channel Title: {channel_title}")
    folder_path = os.path.join("transcripts", channel_title)
    os.makedirs(folder_path, exist_ok=True)

    try:
        video_ids = load_or_fetch_video_ids(channel_id, folder_path)
    except Exception as e:
        print(f"❌ Failed to fetch videos: {e}")
        return

    if not video_ids:
        print("⚠️ No videos found.")
        return

    print(f"🎯 Trying to download transcripts for {len(video_ids)} videos...\n")
    saved = 0
    skipped = 0
    failed = Counter()
    blocked = False
    blocked_in_a_row = 0
    api = YouTubeTranscriptApi()
    ydl = make_ytdlp()

    def show_progress(checked):
        print(f"\r{progress_bar(checked, len(video_ids))} | 💾 Saved: {saved} | ⏭️ Skipped: {skipped} | ❌ Failed: {sum(failed.values())}  ", end='')

    # Videos found to have no subtitles, so later runs don't ask YouTube about them again
    no_subtitles_path = os.path.join(folder_path, "no_subtitles.txt")
    no_subtitles = set()
    failed_in_a_row = []
    if os.path.exists(no_subtitles_path):
        with open(no_subtitles_path, encoding="utf-8") as f:
            no_subtitles = set(f.read().split())

    for idx, video_id in enumerate(video_ids, start=1):
        file_path = os.path.join(folder_path, f"{video_id}.json")
        # An empty file is a failed download from an earlier run, so try it again
        if video_id in no_subtitles or (os.path.exists(file_path) and os.path.getsize(file_path) > 0):
            skipped += 1
            show_progress(idx)
            continue

        try:
            transcript = fetch_transcript(api, video_id, language, ydl)
            # Save under a temporary name first, so a crash never leaves a half-written file
            temp_path = file_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(transcript, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, file_path)
            saved += 1
            blocked_in_a_row = 0
            # A success after a few failures means those really had no subtitles: remember them
            if len(failed_in_a_row) < FAILED_STREAK_LIMIT and any(failed_in_a_row):
                with open(no_subtitles_path, "a", encoding="utf-8") as f:
                    f.write("\n".join(v for v in failed_in_a_row if v) + "\n")
            failed_in_a_row = []
            show_progress(idx)
            if max_new and saved >= max_new:
                break
            time.sleep(random.uniform(*PAUSE_SECONDS))
        except (IpBlocked, RequestBlocked, YouTubeBlocked):
            blocked_in_a_row += 1
            # yt-dlp can get one refusal and then work again, so only stop when it keeps happening
            if ydl is not None and blocked_in_a_row < BLOCKED_LIMIT:
                failed["refused by YouTube (will retry next run)"] += 1
                time.sleep(10)
                show_progress(idx)
                continue
            blocked = True
            print("\n\n🛑 YouTube is blocking this computer for now. Stopping here.")
            print("   Run it again later: it will carry on from where it stopped.")
            break
        except KeyboardInterrupt:
            print("\n\n⏹️ Stopped by you. Run it again to carry on from here.")
            break
        except Exception as e:
            failed[failure_reason(e)] += 1
            blocked_in_a_row = 0
            failed_in_a_row.append(video_id if isinstance(e, (NoSubtitles, NoTranscriptFound, TranscriptsDisabled)) else None)
            # Many failures in a row is not "no subtitles": YouTube has quietly stopped
            # answering this session. Start a fresh one; if that doesn't help, stop.
            if len(failed_in_a_row) % FAILED_STREAK_LIMIT == 0:
                if len(failed_in_a_row) >= 3 * FAILED_STREAK_LIMIT:
                    blocked = True
                    print(f"\n\n🛑 {len(failed_in_a_row)} videos in a row failed. YouTube has stopped answering. Stopping here.")
                    break
                ydl = make_ytdlp()
                time.sleep(60)
            time.sleep(1)

        show_progress(idx)

    csv_path = write_links_csv(folder_path)

    print(f"\n\n{'⚠️ Stopped early.' if blocked else '✅ Done!'} Transcripts saved in: {folder_path}")
    print(f"💾 Total new saved: {saved}")
    print(f"⏭️ Total skipped (already existed): {skipped}")
    print(f"❌ Total failed: {sum(failed.values())}")
    for reason, count in failed.most_common():
        print(f"   - {reason}: {count}")
    print(f"📄 CSV with file links: {csv_path}")
    return blocked


def main():
    # So the emojis and the progress bar never crash an older Windows terminal
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("🎬 YouTube Transcript Scraper (just try + save)\n")
    # Channel links can also be given on the command line, with --lang es for Spanish subtitles
    args = sys.argv[1:]
    language = "en"
    if "--lang" in args:
        position = args.index("--lang")
        language = args[position + 1]
        del args[position:position + 2]
    # --max 500 stops after 500 new transcripts per channel
    max_new = None
    if "--max" in args:
        position = args.index("--max")
        max_new = int(args[position + 1])
        del args[position:position + 2]
    if args:
        for channel_url in args:
            if fetch_and_save_transcripts(channel_url, language, max_new):
                sys.exit(2)
        return
    while True:
        user_input = input("Paste a YouTube channel URL (or 'exit' to quit): ").strip()
        if user_input.lower() == "exit":
            print("👋 Goodbye!")
            break
        elif user_input:
            language = input("Subtitle language, en or es (Enter for en): ").strip().lower() or "en"
            fetch_and_save_transcripts(user_input, language)

if __name__ == "__main__":
    main()
