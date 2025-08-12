import os
import scrapetube
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi
import itertools

def get_channel_id_from_url(url):
    if "/channel/" in url:
        return url.split("/channel/")[1].split("/")[0]
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        tag = soup.find("link", {"rel": "canonical"})
        if tag and "/channel/" in tag["href"]:
            return tag["href"].split("/channel/")[1]
    except:
        pass
    return None

def get_channel_title(channel_id):
    url = f"https://www.youtube.com/channel/{channel_id}"
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        title_tag = soup.find("meta", property="og:title")
        if title_tag:
            return title_tag["content"].replace(" - YouTube", "").replace(" ", "_")
    except:
        pass
    return "channel"

def fetch_and_save_transcripts(channel_url):
    channel_id = get_channel_id_from_url(channel_url)
    if not channel_id:
        print("❌ Could not extract Channel ID.")
        return

    print(f"✅ Channel ID: {channel_id}")
    channel_title = get_channel_title(channel_id)
    print(f"🔖 Channel Title: {channel_title}")
    folder_path = f"transcripts/{channel_title}"
    os.makedirs(folder_path, exist_ok=True)

    print("⏳ Fetching videos...")
    try:
        print("here0")
        videos = scrapetube.get_channel(channel_id)
        print("here1")
        video_ids = video_ids = [video["videoId"] for video in itertools.islice(videos, 50)]  # Only first 50 videos
        print("here2")
    except Exception as e:
        print(f"❌ Failed to fetch videos: {e}")
        return
    
    print("here3")

    if not video_ids:
        print("⚠️ No videos found.")
        return

    print(f"🎯 Trying to download transcripts for {len(video_ids)} videos...\n")
    saved = 0
    skipped = 0
    failed = 0


    transcript_files = []
    for idx, video_id in enumerate(video_ids, start=1):
        file_path = os.path.join(folder_path, f"{video_id}.json")
        if os.path.exists(file_path):
            skipped += 1
            # print(f"\n⏭️ Skipped (already exists): {video_id}")
            transcript_files.append(file_path)
            continue

        try:
            # print(f"\n📥 Downloading transcript for: {video_id}")
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            with open(file_path, "w", encoding="utf-8") as f:
                import json
                json.dump(transcript, f, ensure_ascii=False, indent=2)
            saved += 1
            transcript_files.append(file_path)
        except Exception as e:
            failed += 1
            # print(f"⚠️ Failed to fetch transcript for {video_id}: {e}")

        print(f"\r📊 Progress: {idx}/{len(video_ids)} | 💾 Saved: {saved} | ⏭️ Skipped: {skipped} | ❌ Failed: {failed}", end='')

    # Write CSV with YouTube video links (append mode)
    import csv
    csv_path = os.path.join(folder_path, "transcript_files.csv")
    write_header = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if write_header:
            writer.writerow(["youtube_url"])
        for file_path in transcript_files:
            video_id = os.path.splitext(os.path.basename(file_path))[0]
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            writer.writerow([youtube_url])

    print(f"\n\n✅ Done! Transcripts saved in: {folder_path}")
    print(f"💾 Total new saved: {saved}")
    print(f"⏭️ Total skipped (already existed): {skipped}")
    print(f"❌ Total failed: {failed}")
    print(f"📄 CSV with file links: {csv_path}")


def main():
    print("🎬 YouTube Transcript Scraper (just try + save)\n")
    while True:
        user_input = input("Paste a YouTube channel URL (or 'exit' to quit): ").strip()
        if user_input.lower() == "exit":
            print("👋 Goodbye!")
            break
        elif user_input:
            fetch_and_save_transcripts(user_input)

if __name__ == "__main__":
    main()