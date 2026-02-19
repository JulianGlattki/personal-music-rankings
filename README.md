# My Music Rankings

Personal music rankings site — powered by GitHub Pages + Spotify API. \
Vibe coded with Claude. \
I know you can also just embed Spotify playlists, but that's boring :^)

## Setup

### 1. GitHub Secrets
Go to **Settings → Secrets and variables → Actions** and add:
- `SPOTIFY_CLIENT_ID` — from [developer.spotify.com](https://developer.spotify.com/dashboard)
- `SPOTIFY_CLIENT_SECRET` — same place

### 2. Enable GitHub Actions write permissions
Go to **Settings → Actions → General → Workflow permissions** → select **Read and write permissions**

### 3. Enable GitHub Pages
Go to **Settings → Pages** → Source: `Deploy from branch` → Branch: `main` / `root`

---

## Managing Categories

Everything is controlled by **`playlists.json`** — this is the only file you need to edit to add, remove, or rename categories. The website and the GitHub Action both read from it automatically.

```json
[
  {
    "id": "country_songs",
    "name": "Country Songs",
    "icon": "🤠",
    "type": "tracks",
    "playlist_url": "https://open.spotify.com/playlist/..."
  },
  {
    "id": "country_albums",
    "name": "Country Albums",
    "icon": "🤠",
    "type": "albums",
    "playlist_url": "https://open.spotify.com/playlist/..."
  }
]
```

| Field | Description |
|---|---|
| `id` | Unique key — used as the CSV filename (`data/<id>.csv`) |
| `name` | Display name on the website |
| `icon` | Emoji shown in the header and sidebar |
| `type` | `tracks` or `albums` |
| `playlist_url` | Your Spotify playlist URL |

---

## Running a Sync

1. Go to **Actions → Sync Spotify Playlist → Run workflow**
2. Enter a **Category ID** from `playlists.json` — or type `all` to sync everything
3. A PR will be created with the updated CSV(s)
4. Review the diff, apply any overrides (see below), then merge

---

## Overrides

Some fields can be manually overridden in the CSV. They are preserved on every future sync — the script never overwrites them.

| Field | When to use |
|---|---|
| `year_override` | Spotify's release year is wrong — e.g. a remaster showing a later year |
| `title_override` | Title has unwanted suffixes — e.g. "Crazy Arms - Remastered 2004" → "Crazy Arms" |

Just fill in the value directly in the PR diff before merging.

---

## Albums vs Tracks

- **type: "tracks"** — add the tracks directly to your Spotify playlist
- **type: "albums"** — add **one track per album** to the playlist; the script reads the album metadata and de-duplicates automatically
