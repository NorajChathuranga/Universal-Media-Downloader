# Universal Media Downloader

A Streamlit UI on top of [yt-dlp](https://github.com/yt-dlp/yt-dlp) — paste a URL, preview the
title/thumbnail, choose video or audio, pick a quality, and download.

## Run locally

```bash
pip install -r requirements.txt
# ffmpeg is required for merging video+audio and for audio extraction
# macOS: brew install ffmpeg | Ubuntu/Debian: sudo apt install ffmpeg | Windows: https://ffmpeg.org/download.html
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this folder to a GitHub repo (needs `app.py`, `requirements.txt`, `packages.txt`).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → point it at the repo/branch and `app.py`.
3. Streamlit Cloud reads `packages.txt` automatically and apt-installs `ffmpeg` for you — no extra config needed.

## Known limitations to plan around

- **Cloud IPs get rate-limited/blocked by some sites.** YouTube in particular is more aggressive about
  throttling or blocking requests from shared datacenter IP ranges (which is what Streamlit Cloud uses)
  than from a home connection. If downloads start failing with 403s only on the deployed version, this
  is usually why — a VPS with a residential/dedicated IP, or a proxy, mitigates it. This has nothing to
  do with your code.
- **Age-restricted / login-required / private content** needs a cookies file. The app has an "Advanced
  options" uploader for a Netscape-format `cookies.txt` (export it from your browser with an extension
  like "Get cookies.txt LOCALLY") — there's no browser on the server to pull cookies from automatically.
- **Streamlit Community Cloud free tier** caps memory (~1GB) and has request timeouts, so very large or
  very long videos may fail or time out. Fine for typical clips; not built for feature-length 4K files.
- **yt-dlp needs updating over time.** Sites change their internals and yt-dlp ships frequent fixes —
  pin a version you've tested, but expect to bump `yt-dlp` in `requirements.txt` periodically if
  extraction starts failing for a specific site.
- **Legal use.** Only download content you own, have permission to use, or that's licensed for reuse.
  Respect each platform's Terms of Service — this tool doesn't bypass DRM or paywalls, it just wraps
  yt-dlp's public extraction of content the site already serves to you.

## Customizing

- `VIDEO_QUALITY_MAP` / `AUDIO_FORMATS` / `AUDIO_QUALITIES` in `app.py` control the dropdown options —
  add or remove entries there.
- Swap `noplaylist: True` to `False` in the `ydl_opts` if you later want playlist/batch support; you'd
  also want to switch the single `st.download_button` to zip up multiple files first.
