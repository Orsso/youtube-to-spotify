# YouTube to Spotify Playlist Migrator

Export any YouTube playlist to Spotify with intelligent song matching.

## Features

- **One-click migration** from YouTube playlists to Spotify
- **Smart matching** using video titles and channel names
- **High success rate** with fuzzy matching and multiple search strategies
- **Detailed reports** showing matched and unmatched tracks
- **Rate limit handling** for both YouTube and Spotify APIs

## Quick Start

### Requirements

- Python 3.8+
- YouTube Data API v3 key (free)
- Spotify Web API credentials (free)


1. **Clone and setup**
   ```bash
   git clone https://github.com/orsso/youtube-to-spotify.git
   cd youtube-to-spotify
   python setup.py
   ```

2. **Get API credentials**
   - YouTube: [Google Cloud Console](https://console.cloud.google.com/) → Enable YouTube Data API v3
   - Spotify: [Developer Dashboard](https://developer.spotify.com/dashboard/) → Create app → Add redirect URI: `http://127.0.0.1:8888/callback`

3. **Configure and run**
   ```bash
   # Edit .env with your API keys
   source venv/bin/activate
   python youtube_to_spotify.py
   ```

## How It Works

1. **Extracts** video titles and channel names from YouTube playlists
2. **Parses** titles to identify artist and song information
3. **Searches** Spotify using multiple strategies:
   - Parsed artist + song title
   - YouTube channel name + song title
   - Song title only
4. **Creates** new Spotify playlist with matched tracks
5. **Generates** detailed CSV report of results

## Configuration

Create a `.env` file:
```env
YOUTUBE_API_KEY=your_api_key
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_USER_ID=auto_detect
```

## License

MIT License - see LICENSE file for details.
# youtube-to-spotify
