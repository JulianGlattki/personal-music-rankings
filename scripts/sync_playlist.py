#!/usr/bin/env python3
"""
Spotify Playlist -> CSV sync script.
Reads all config from playlists.json — no hardcoding needed.

Env vars required:
  SPOTIFY_CLIENT_ID
  SPOTIFY_CLIENT_SECRET
  CATEGORY_ID   — id from playlists.json, or "all"
"""

import os
import re
import csv
import json
import requests
from pathlib import Path

CLIENT_ID     = os.environ["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
CATEGORY_ID   = os.environ.get("CATEGORY_ID", "all").strip()

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

PLAYLISTS_FILE = Path("playlists.json")

CSV_COLUMNS = [
    "title", "artist", "year_spotify", "year_override",
    "title_override",
    "spotifyId", "type", "embed", "cover", "playlist_url",
]

# ── Spotify auth ──────────────────────────────────────────────────────────────

def get_token():
    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        auth=(CLIENT_ID, CLIENT_SECRET),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

# ── Spotify API helpers ───────────────────────────────────────────────────────

def extract_playlist_id(url):
    match = re.search(r"playlist/([A-Za-z0-9]+)", url)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Za-z0-9]+", url):
        return url
    raise ValueError(f"Cannot parse playlist ID from: {url!r}")


def get_playlist_tracks(playlist_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    params = {"limit": 100, "fields": "items,next"}
    items = []
    while url:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items.extend(data.get("items", []))
        url = data.get("next")
        params = {}
    return items


def parse_year(date_str):
    return (date_str or "")[:4]


def best_cover(images):
    return images[0]["url"] if images else ""

# ── Row builders ──────────────────────────────────────────────────────────────

def track_row(item, playlist_url):
    track = item.get("track")
    if not track or track.get("is_local"):
        return None
    album = track.get("album", {})
    return {
        "title":        track["name"],
        "artist":       ", ".join(a["name"] for a in track.get("artists", [])),
        "year_spotify": parse_year(album.get("release_date", "")),
        "year_override": "",
        "spotifyId":    track["id"],
        "type":         "track",
        "embed":        "true",
        "cover":        best_cover(album.get("images", [])),
        "title_override": "",
        "playlist_url": playlist_url,
    }


def album_row(item, playlist_url):
    track = item.get("track")
    if not track or track.get("is_local"):
        return None
    album = track.get("album", {})
    return {
        "title":        album["name"],
        "artist":       ", ".join(a["name"] for a in album.get("artists", [])),
        "year_spotify": parse_year(album.get("release_date", "")),
        "year_override": "",
        "spotifyId":    album["id"],
        "type":         "album",
        "embed":        "true",
        "cover":        best_cover(album.get("images", [])),
        "title_override": "",
        "playlist_url": playlist_url,
    }

# ── CSV helpers ───────────────────────────────────────────────────────────────

def load_overrides(path):
    """Return existing spotifyId -> {year_override, title_override} to preserve manual edits."""
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {
            row["spotifyId"]: {
                "year_override":  row.get("year_override", ""),
                "title_override": row.get("title_override", ""),
            }
            for row in csv.DictReader(f)
            if row.get("spotifyId")
        }


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

# ── Sync one entry ────────────────────────────────────────────────────────────

def sync_one(cfg, token):
    cat_id       = cfg["id"]
    playlist_url = cfg["playlist_url"]
    cat_type     = cfg.get("type", "tracks")
    csv_path     = DATA_DIR / f"{cat_id}.csv"

    print(f"\n-- {cat_id} ({cat_type})")
    print(f"   Playlist: {playlist_url}")

    playlist_id = extract_playlist_id(playlist_url)
    items = get_playlist_tracks(playlist_id, token)
    print(f"   Fetched {len(items)} items")

    overrides = load_overrides(csv_path)
    print(f"   Preserving {len(overrides)} year_override(s)")

    rows = []
    seen = set()
    for item in items:
        row = album_row(item, playlist_url) if cat_type == "albums" else track_row(item, playlist_url)
        if row is None:
            continue
        sid = row["spotifyId"]
        if sid in seen:
            continue
        seen.add(sid)
        if sid in overrides:
            row["year_override"]  = overrides[sid].get("year_override", "")
            row["title_override"] = overrides[sid].get("title_override", "")
        rows.append(row)

    write_csv(csv_path, rows)
    print(f"   Written {len(rows)} rows -> {csv_path}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not PLAYLISTS_FILE.exists():
        raise FileNotFoundError(f"{PLAYLISTS_FILE} not found.")

    with open(PLAYLISTS_FILE, encoding="utf-8") as f:
        all_playlists = json.load(f)

    if CATEGORY_ID == "all":
        to_sync = all_playlists
    else:
        to_sync = [p for p in all_playlists if p["id"] == CATEGORY_ID]
        if not to_sync:
            available = [p["id"] for p in all_playlists]
            raise ValueError(
                f"Category '{CATEGORY_ID}' not found in playlists.json.\n"
                f"Available: {available}"
            )

    print(f"Syncing {len(to_sync)} playlist(s)...")
    token = get_token()

    for cfg in to_sync:
        sync_one(cfg, token)

    print("\nAll done.")


if __name__ == "__main__":
    main()
