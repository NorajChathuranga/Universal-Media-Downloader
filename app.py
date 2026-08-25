import os
import re
import shutil
import tempfile

import streamlit as st
import yt_dlp

st.set_page_config(page_title="Universal Downloader", page_icon="⬇️", layout="centered")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

VIDEO_QUALITY_MAP = {
    "Best available": "bestvideo+bestaudio/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
}

AUDIO_FORMATS = ["mp3", "m4a", "wav"]
AUDIO_QUALITIES = {"High (~192 kbps)": "192", "Medium (~128 kbps)": "128", "Low (~96 kbps)": "96"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sizeof_fmt(num):
    if not num:
        return "unknown size"
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(num) < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


def duration_fmt(seconds):
    if not seconds:
        return "unknown length"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)


@st.cache_data(show_spinner=False, ttl=600)
def fetch_info(url: str, cookie_bytes: bytes | None):
    """Pull metadata only — no media is downloaded here."""
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    tmp_cookie_path = None
    if cookie_bytes:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        tmp.write(cookie_bytes)
        tmp.close()
        tmp_cookie_path = tmp.name
        ydl_opts["cookiefile"] = tmp_cookie_path
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    finally:
        if tmp_cookie_path:
            os.unlink(tmp_cookie_path)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("⬇️ Universal Media Downloader")
st.caption(
    "Powered by yt-dlp — works with YouTube, Instagram, TikTok, X/Twitter, "
    "SoundCloud, Facebook, Vimeo and 1000+ other sites."
)

with st.expander("⚠️ Before you use this"):
    st.markdown(
        "- Only download content you own, have permission to use, or that's licensed "
        "for reuse (Creative Commons, public domain, your own uploads).\n"
        "- Respect the terms of service of the platform you're downloading from.\n"
        "- If you deploy this publicly, consider adding your own usage disclaimer for visitors."
    )

url = st.text_input("Paste a video/audio URL", placeholder="https://...")

with st.expander("Advanced options"):
    cookies_file = st.file_uploader(
        "Cookies file, Netscape format (optional — needed for age-restricted or private content)",
        type=["txt"],
    )

if url:
    if st.button("🔍 Fetch info", use_container_width=True):
        with st.spinner("Fetching metadata..."):
            try:
                cookie_bytes = cookies_file.read() if cookies_file else None
                info = fetch_info(url, cookie_bytes)
                st.session_state["info"] = info
                st.session_state["cookie_bytes"] = cookie_bytes
                st.session_state["url"] = url
            except Exception as e:
                st.error(f"Couldn't fetch info: {e}")
                st.session_state.pop("info", None)

info = st.session_state.get("info")
if info and st.session_state.get("url") == url:
    col1, col2 = st.columns([1, 2])
    with col1:
        thumb = info.get("thumbnail")
        if thumb:
            st.image(thumb, use_container_width=True)
    with col2:
        st.subheader(info.get("title", "Untitled"))
        st.write(f"**Uploader:** {info.get('uploader', 'unknown')}")
        st.write(f"**Duration:** {duration_fmt(info.get('duration'))}")

    st.divider()
    mode = st.radio("Download as", ["Video", "Audio only"], horizontal=True)

    if mode == "Video":
        quality_label = st.selectbox("Quality", list(VIDEO_QUALITY_MAP.keys()))
        format_selector = VIDEO_QUALITY_MAP[quality_label]
        audio_format = audio_quality = None
    else:
        audio_format = st.selectbox("Format", AUDIO_FORMATS)
        quality_label = st.selectbox("Quality", list(AUDIO_QUALITIES.keys()))
        audio_quality = AUDIO_QUALITIES[quality_label]
        format_selector = "bestaudio/best"

    if st.button("⬇️ Download", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def progress_hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                if total:
                    progress_bar.progress(min(downloaded / total, 1.0))
                speed = d.get("speed")
                eta = d.get("eta")
                msg = f"Downloading... {sizeof_fmt(downloaded)}"
                if total:
                    msg += f" / {sizeof_fmt(total)}"
                if speed:
                    msg += f" @ {sizeof_fmt(speed)}/s"
                if eta:
                    msg += f" (ETA {eta}s)"
                status_text.text(msg)
            elif d["status"] == "finished":
                progress_bar.progress(1.0)
                status_text.text("Processing (merging/converting)...")

        tmp_dir = tempfile.mkdtemp()
        tmp_cookie_path = None
        cookie_bytes = st.session_state.get("cookie_bytes")

        ydl_opts = {
            "format": format_selector,
            "outtmpl": os.path.join(tmp_dir, "%(title).150s.%(ext)s"),
            "noplaylist": True,
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
        }

        if mode == "Video":
            ydl_opts["merge_output_format"] = "mp4"
        else:
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": audio_quality,
                }
            ]

        if cookie_bytes:
            tmp_cookie = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
            tmp_cookie.write(cookie_bytes)
            tmp_cookie.close()
            tmp_cookie_path = tmp_cookie.name
            ydl_opts["cookiefile"] = tmp_cookie_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            files = os.listdir(tmp_dir)
            if not files:
                st.error("Download finished but no output file was found.")
            else:
                out_path = os.path.join(tmp_dir, files[0])
                with open(out_path, "rb") as f:
                    data = f.read()
                status_text.text("Done!")
                st.success(f"Ready: {files[0]} ({sizeof_fmt(len(data))})")
                st.download_button(
                    "💾 Save file",
                    data=data,
                    file_name=sanitize_filename(files[0]),
                    use_container_width=True,
                )
        except Exception as e:
            st.error(f"Download failed: {e}")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            if tmp_cookie_path:
                os.unlink(tmp_cookie_path)
else:
    st.info("Paste a URL above and click **Fetch info** to get started.")
