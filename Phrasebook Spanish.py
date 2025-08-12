import os
import re
import json
import pandas as pd

# ---------------------------
# Configuration
# ---------------------------
base_folder = 'transcripts'  # Folder containing your transcript subfolders

# ---------------------------
# Verify base folder
# ---------------------------
if not os.path.isdir(base_folder):
    raise FileNotFoundError(f"No such folder: '{base_folder}'")

# ---------------------------
# List available subfolders
# ---------------------------
available_folders = sorted([
    d for d in os.listdir(base_folder)
    if os.path.isdir(os.path.join(base_folder, d))
])
if not available_folders:
    raise ValueError("⚠️ No subfolders found in 'transcripts'!")

print("📁 Available folders:")
for idx, folder in enumerate(available_folders, start=1):
    print(f"  {idx}. {folder}")

# ---------------------------
# Prompt user for folder selection
# ---------------------------
while True:
    choice = input("\n🔢 Select folders by number (comma-separated, or 'all'): ").strip().lower()
    if choice == 'all':
        selected_folders = [os.path.join(base_folder, f) for f in available_folders]
        break
    try:
        indices = [int(x.strip()) - 1 for x in choice.split(',')]
        if all(0 <= i < len(available_folders) for i in indices):
            selected_folders = [
                os.path.join(base_folder, available_folders[i]) for i in indices
            ]
            break
    except:
        pass
    print("❌ Invalid selection. Please enter valid numbers or 'all'.")


# ---------------------------
# Helper: extract YouTube video ID
# ---------------------------
def extract_video_id(filepath):
    filename = os.path.splitext(os.path.basename(filepath))[0]
    m = re.search(r'([A-Za-z0-9_-]{11})', filename)
    return m.group(1) if m else None

# ---------------------------
# Main search loop
# ---------------------------
while True:
    print("\n✅ Selected folders:")
    for f in selected_folders:
        print(f"   - {f}")

    query = input("\n📝 Enter search terms (or 'exit' to quit): ").strip()
    if query.lower() == 'exit':
        print("👋 Goodbye!")
        break
    if not query:
        continue

    terms = query.lower().split()
    print("🔍 Scanning transcripts...")

    # Gather all JSON transcript files
    json_files = []
    for folder in selected_folders:
        for root, _, files in os.walk(folder):
            for fn in files:
                if fn.endswith('.json'):
                    json_files.append(os.path.join(root, fn))

    # Search for terms in each file
    results = []
    for path in json_files:
        try:
            with open(path, encoding='utf-8') as f:
                transcript = json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load {path}: {e}")
            continue

        vid = extract_video_id(path)
        for entry in transcript:
            text = entry.get('text', '')
            if all(t in text.lower() for t in terms):
                start = entry.get('start', 0)
                mm, ss = divmod(int(start), 60)
                timestamp = f"{mm}:{ss:02d}"
                url = f"https://www.youtube.com/watch?v={vid}"
                # For Excel, use HYPERLINK formulas; for console, plain URLs
                results.append({
                    'VideoURL': url,
                    'Time': timestamp,
                    'Line': text.strip(),
                    'LinkURL': f"{url}&t={int(start)}s",
                    'VideoFormula': f'=HYPERLINK("{url}", "Video")',
                    'LinkFormula': f'=HYPERLINK("{url}&t={int(start)}s", "Go to time")'
                })

    # Print results to console
    if not results:
        print(f"❌ No matches found for '{query}'.")
        continue

    print(f"\n✅ Found {len(results)} matches\n")

    # ---------------------------
    # Save results to Excel with HYPERLINK formulas
    # ---------------------------
    # Sanitize filename
    safe_name = re.sub(r'[^A-Za-z0-9_]+', '_', query).strip('_')
    excel_path = os.path.join(base_folder, f'{safe_name}.xlsx')
    df = pd.DataFrame(results)[['VideoFormula', 'Time', 'Line', 'LinkFormula']]
    df.columns = ['Video', 'Time', 'Line', 'Link']
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Results')
    print(f"💾 Saved results to '{excel_path}'\n")
