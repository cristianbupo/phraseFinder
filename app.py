import os, re, json
import pandas as pd
import streamlit as st

# ---------------------------
# Config
# ---------------------------
baseFolder = "transcripts"  # Folder with your transcript subfolders

# ---------------------------
# Helpers
# ---------------------------
def extractVideoId(filepath: str):
    filename = os.path.splitext(os.path.basename(filepath))[0]
    m = re.search(r"([A-Za-z0-9_-]{11})", filename)
    return m.group(1) if m else None

def listTranscriptFolders(baseFolder: str):
    if not os.path.isdir(baseFolder):
        st.error(f"No such folder: '{baseFolder}'")
        st.stop()
    folders = sorted([
        d for d in os.listdir(baseFolder)
        if os.path.isdir(os.path.join(baseFolder, d))
    ])
    if not folders:
        st.error("No subfolders found in 'transcripts'")
        st.stop()
    return folders

def collectJsonFiles(selectedFolders):
    jsonFiles = []
    for folder in selectedFolders:
        for root, _, files in os.walk(folder):
            for fn in files:
                if fn.endswith(".json"):
                    jsonFiles.append(os.path.join(root, fn))
    return jsonFiles

def searchTranscripts(jsonFiles, terms):
    results = []
    for path in jsonFiles:
        try:
            with open(path, encoding="utf-8") as f:
                transcript = json.load(f)
        except Exception as e:
            st.warning(f"Failed to load {path}: {e}")
            continue

        vid = extractVideoId(path)
        for entry in transcript:
            text = entry.get("text", "")
            if all(t in text.lower() for t in terms):
                start = float(entry.get("start", 0))
                mm, ss = divmod(int(start), 60)
                timestamp = f"{mm}:{ss:02d}"
                url = f"https://www.youtube.com/watch?v={vid}" if vid else ""
                linkUrl = f"{url}&t={int(start)}s" if vid else ""
                results.append({
                    "Video": url,
                    "Time": timestamp,
                    "Line": text.strip(),
                    "Link": linkUrl
                })
    return pd.DataFrame(results)

def makeDownloadFilename(query: str):
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", query).strip("_")
    return f"{safe or 'results'}.xlsx"

# ---------------------------
# UI
# ---------------------------
st.set_page_config(page_title="Phrase Finder", page_icon="🔍", layout="wide")

st.title("Phrase Finder 🔍")
st.caption("Find words and phrases in real video subtitles. Click the link to jump right to them.")

# Soft colors
st.markdown("""
<style>
:root {
  --primary: #5C7FA3;
  --secondary: #92B7A5;
  --accent: #F5D38C;
  --bg: #FAF8F6;
  --text: #3A3A3A;
}
.stApp { background-color: var(--bg); color: var(--text); }
.stButton>button { background: var(--primary); color: white; border-radius: 12px; }
.stButton>button:hover { filter: brightness(0.92); }
</style>
""", unsafe_allow_html=True)

folders = listTranscriptFolders(baseFolder)
selected = st.multiselect(
    "Choose transcript folders",
    folders,
    default=folders
)

query = st.text_input("Search terms (separate with spaces)", value="")

if st.button("Search"):
    if not query.strip():
        st.warning("Type at least one word.")
        st.stop()

    terms = query.lower().split()
    jsonFiles = collectJsonFiles([os.path.join(baseFolder, f) for f in selected])
    with st.spinner("Scanning transcripts..."):
        df = searchTranscripts(jsonFiles, terms)

    if df.empty:
        st.info(f"No matches for '{query}'. Try a different word.")
    else:
        st.success(f"Found {len(df)} matches.")
        # Show table with clickable links
        showDf = df.copy()
        showDf["Video"] = showDf["Video"].apply(lambda u: f"[Video]({u})" if u else "")
        showDf["Link"] = showDf["Link"].apply(lambda u: f"[Go to time]({u})" if u else "")
        st.dataframe(showDf, use_container_width=True)

        # Provide an Excel download
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Results")
        st.download_button(
            label="Download Excel",
            data=output.getvalue(),
            file_name=makeDownloadFilename(query),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
