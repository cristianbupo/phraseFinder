import os, re, json
import pandas as pd
import streamlit as st
# Font + base styles
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

st.markdown("""
<style>
:root{
  --primary:#5C7FA3;   /* muted denim */
  --secondary:#92B7A5; /* soft sage */
  --accent:#F5D38C;    /* warm sand */
  --bg:#FAF8F6;        /* paper */
  --bg2:#F3EFEA;       /* card */
  --ink:#3A3A3A;       /* text */
}

/* page */
html, body, .stApp{ background:var(--bg); color:var(--ink); font-family:"Poppins", system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
.block-container{ max-width:1100px; padding-top:2.2rem; }

/* header card */
.k-hero{
  background:var(--bg2);
  border:1px solid rgba(0,0,0,.06);
  border-radius:18px;
  padding:1.25rem 1.25rem 1rem;
  margin-bottom:1rem;
}
.k-hero h1{ margin:0 0 .25rem 0; letter-spacing:.3px; }
.k-hero p{ margin:.25rem 0 0 0; color:#5a5a5a; }

/* search bar */
.stTextInput>div>div{
  background:var(--bg2) !important;
  border:1px solid rgba(0,0,0,.08) !important;
  border-radius:16px !important;
  padding:.1rem .6rem !important;
}
.stTextInput input{ font-size:1rem; }

/* primary button */
.stButton>button{
  background:var(--primary);
  color:#fff;
  border:0;
  border-radius:14px;
  padding:.7rem 1.15rem;
  font-weight:600;
  box-shadow:0 1px 0 rgba(0,0,0,.06);
}
.stButton>button:hover{ filter:brightness(.93); }

/* secondary button helper class */
button.k-btn-secondary{
  background:transparent; color:var(--primary); border:1.5px solid var(--secondary);
  border-radius:14px; padding:.6rem 1.1rem; font-weight:600;
}
button.k-btn-secondary:hover{ background:rgba(146,183,165,.12); }

/* multiselect chips */
.stMultiSelect [data-baseweb="tag"]{
  background: var(--accent) !important;
  color:#434343 !important;
  border-radius:999px !important;
  border:0 !important;
  box-shadow:none !important;
}
.stMultiSelect [data-baseweb="tag"] svg{ opacity:.65; }

/* section titles */
.k-section-title{
  font-weight:600; font-size:1.05rem; margin:.75rem 0 .35rem 2px;
}

/* info and success banners softened */
.stAlert{ border-radius:14px; }

/* table */
[data-testid="stDataFrame"]{ border-radius:14px; overflow:hidden; }
</style>
""", unsafe_allow_html=True)

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

        # Show table with video title and clickable link
        from pytube import YouTube
        def get_video_title(url):
            try:
                yt = YouTube(url)
                return yt.title
            except:
                return "Unknown Title"

        showDf = df.copy()
        showDf["Video"] = showDf["Video"].apply(lambda url: f"[{get_video_title(url)}]({url})" if url else "")
        showDf["Link"] = showDf["Link"].apply(lambda u: f"[Go to time]({u})" if u else "")
        st.write(showDf.to_markdown(index=False), unsafe_allow_html=True)

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
