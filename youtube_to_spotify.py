#!/usr/bin/env python3
"""
YouTube to Spotify Playlist Migrator

Exports YouTube playlists to Spotify with intelligent song matching.
Uses video titles and channel names for accurate track identification.
"""

import os
import re
import csv
import time
import base64
import logging
import urllib.parse
import webbrowser
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from fuzzywuzzy import fuzz # type: ignore

import requests
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Song:
    """Represents a song with metadata"""
    original_title: str
    channel_name: str = ""
    artist: str = ""
    title: str = ""
    spotify_uri: str = ""
    match_confidence: float = 0.0
    error: str = ""
    found: bool = False

@dataclass
class MigrationStats:
    """Migration statistics"""
    total_songs: int = 0
    successful_matches: int = 0
    not_found: int = 0
    errors: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class YouTubeExtractor:
    """Handles YouTube playlist extraction using YouTube Data API v3"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"
        
    def extract_playlist_id(self, url: str) -> Optional[str]:
        """Extract playlist ID from various YouTube URL formats"""
        patterns = [
            r'list=([a-zA-Z0-9_-]+)',
            r'playlist\?list=([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_playlist_videos(self, playlist_id: str) -> List[Dict[str, str]]:
        """Get all video titles and channel names from a YouTube playlist with pagination"""
        videos = []
        next_page_token = None

        while True:
            params = {
                'part': 'snippet',
                'playlistId': playlist_id,
                'maxResults': 50,
                'key': self.api_key
            }

            if next_page_token:
                params['pageToken'] = next_page_token

            try:
                response = requests.get(f"{self.base_url}/playlistItems", params=params)
                response.raise_for_status()
                data = response.json()

                for item in data.get('items', []):
                    title = item['snippet']['title']
                    channel_name = item['snippet'].get('videoOwnerChannelTitle', '').replace(' - Topic', '')

                    if title != "Deleted video" and title != "Private video":
                        videos.append({
                            'title': title,
                            'channel': channel_name
                        })

                next_page_token = data.get('nextPageToken')
                if not next_page_token:
                    break

                # Rate limiting - YouTube allows 100 requests per 100 seconds
                time.sleep(1)

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching playlist videos: {e}")
                break

        logger.info(f"Extracted {len(videos)} videos from YouTube playlist")
        return videos

class TitleParser:
    """Parses video titles to extract artist and song information"""
    
    def __init__(self):
        self.patterns = [
            # Artist - Song
            r'^(.+?)\s*-\s*(.+)$',
            # Artist: Song
            r'^(.+?)\s*:\s*(.+)$',
            # Song by Artist
            r'^(.+?)\s+by\s+(.+)$',
            # Artist | Song
            r'^(.+?)\s*\|\s*(.+)$',
            # Artist "Song"
            r'^(.+?)\s*["\u201c](.+?)["\u201d]$',
        ]
    
    def clean_text(self, text: str) -> str:
        """Clean common artifacts from titles"""
        # Remove common prefixes/suffixes
        text = re.sub(r'\[.*?\]', '', text)  # Remove [Official Video], etc.
        text = re.sub(r'\(.*?\)', '', text)  # Remove (Official Video), etc.
        text = re.sub(r'(feat\.|ft\.|featuring)\s+.+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
        return text
    
    def parse_title(self, title: str) -> Tuple[str, str]:
        """Parse video title to extract artist and song name"""
        title = self.clean_text(title)
        
        for pattern in self.patterns:
            match = re.match(pattern, title, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    # For "Song by Artist" pattern, swap the order
                    if 'by' in pattern:
                        return groups[1].strip(), groups[0].strip()  # artist, song
                    else:
                        return groups[0].strip(), groups[1].strip()  # artist, song
        
        # Fallback: assume the whole title is the song name
        return "", title

class SpotifyManager:
    """Handles Spotify Web API operations"""

    def __init__(self, client_id: str, client_secret: str, user_id: str = ""):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_id = user_id
        self.access_token = None
        self.base_url = "https://api.spotify.com/v1"
        self._authenticate()

        # Auto-detect user ID if not provided or is placeholder
        if not self.user_id or self.user_id in ["auto_detect", "your_spotify_username_here"]:
            self.user_id = self._get_current_user_id()
    
    def _authenticate(self):
        """Authenticate using Authorization Code flow for playlist creation"""
        print("\n🔐 Spotify Authentication Required")
        print("To create playlists, we need your permission.")
        print("This will open a browser window for you to authorize the app.")

        # Authorization URL
        auth_url = "https://accounts.spotify.com/authorize"
        redirect_uri = "http://127.0.0.1:8888/callback"  
        scope = "playlist-modify-public playlist-modify-private"

        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'scope': scope,
            'show_dialog': 'true'
        }

        auth_request_url = f"{auth_url}?" + urllib.parse.urlencode(params)

        print(f"\n🌐 Opening browser for Spotify authorization...")
        print("If the browser doesn't open automatically, visit this URL:")
        print(f"{auth_request_url}")

        # Open browser automatically
        try:
            webbrowser.open(auth_request_url)
        except Exception:
            print("Could not open browser automatically.")

        print("\n📋 After authorization, you'll be redirected to a URL like:")
        print("http://127.0.0.1:8888/callback?code=XXXXXXX")
        print("\nCopy the ENTIRE URL from your browser and paste it here.")

        # Get authorization code from user
        while True:
            callback_url = input("\nPaste the callback URL here: ").strip()
            if 'code=' in callback_url:
                # Extract code from URL
                code = callback_url.split('code=')[1].split('&')[0]
                print("✅ Authorization code received!")
                break
            else:
                print("❌ Invalid URL. Please make sure you copied the entire callback URL.")

        # Exchange code for access token
        self._exchange_code_for_token(code, redirect_uri)

    def _exchange_code_for_token(self, code: str, redirect_uri: str):
        """Exchange authorization code for access token"""
        token_url = "https://accounts.spotify.com/api/token"

        # Encode credentials
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri
        }

        try:
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data["access_token"]
            logger.info("✅ Successfully authenticated with Spotify (with playlist permissions)")
        except requests.exceptions.RequestException as e:
            logger.error(f"Token exchange failed: {e}")
            raise

    def _get_current_user_id(self) -> str:
        """Get current user ID using the authenticated token"""
        print("\n🔍 Getting your Spotify User ID...")

        user_data = self._make_request('GET', 'me')
        if user_data and 'id' in user_data:
            user_id = user_data['id']
            display_name = user_data.get('display_name', 'Unknown')
            print(f"✅ Found User ID: {user_id} (Display name: {display_name})")
            return user_id
        else:
            print("❌ Could not retrieve user ID automatically")
            print("Please enter your User ID manually:")
            print("1. Go to https://open.spotify.com and log in")
            print("2. Click your profile picture → Profile")
            print("3. Copy the part after '/user/' in the URL")

            while True:
                user_id = input("\nEnter your Spotify User ID: ").strip()
                if user_id:
                    print(f"✅ Using User ID: {user_id}")
                    return user_id
                else:
                    print("❌ User ID cannot be empty")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make authenticated request to Spotify API with retry logic"""
        url = f"{self.base_url}/{endpoint}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        for attempt in range(3):
            try:
                response = requests.request(method, url, headers=headers, **kwargs)
                
                if response.status_code == 429:  # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 1))
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    time.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                return response.json() if response.content else {}
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt == 2:  # Last attempt
                    logger.error(f"All attempts failed for {endpoint}")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return None

    def search_track(self, artist: str, title: str) -> Optional[Dict]:
        """Search for a track on Spotify with intelligent search strategies"""
        # Strategy 1: Exact artist and track search
        if artist and title:
            query = f'artist:"{artist}" track:"{title}"'
            result = self._search_with_query(query)
            if result:
                return result

        # Strategy 2: General search with both artist and title
        if artist and title:
            query = f'"{artist}" "{title}"'
            result = self._search_with_query(query)
            if result:
                return result

        # Strategy 3: Search with just the title
        if title:
            query = f'"{title}"'
            result = self._search_with_query(query)
            if result:
                return result

        return None

    def _search_with_query(self, query: str) -> Optional[Dict]:
        """Execute search query and return best match"""
        params = {
            'q': query,
            'type': 'track',
            'limit': 10
        }

        data = self._make_request('GET', 'search', params=params)
        if not data or 'tracks' not in data:
            return None

        tracks = data['tracks']['items']
        if not tracks:
            return None

        # Return the first (most relevant) track
        return tracks[0]

    def create_playlist(self, name: str, description: str = "", public: bool = True) -> Optional[str]:
        """Create a new Spotify playlist"""
        data = {
            'name': name,
            'description': description,
            'public': public
        }

        result = self._make_request('POST', f'users/{self.user_id}/playlists', json=data)
        if result:
            logger.info(f"Created playlist: {name}")
            return result['id']
        return None

    def add_tracks_to_playlist(self, playlist_id: str, track_uris: List[str]) -> bool:
        """Add tracks to a Spotify playlist in batches"""
        # Spotify allows max 100 tracks per request
        batch_size = 100

        for i in range(0, len(track_uris), batch_size):
            batch = track_uris[i:i + batch_size]
            data = {'uris': batch}

            result = self._make_request('POST', f'playlists/{playlist_id}/tracks', json=data)
            if not result:
                return False

            time.sleep(0.1)  # Small delay between batches

        logger.info(f"Added {len(track_uris)} tracks to playlist")
        return True

class FuzzyMatcher:
    """Handles fuzzy matching for song identification"""

    @staticmethod
    def calculate_match_confidence(original_artist: str, original_title: str,
                                 spotify_artist: str, spotify_title: str) -> float:
        """Calculate confidence score for a Spotify match"""
        if not original_artist or not original_title:
            return 0.0

        # Calculate similarity scores
        artist_score = fuzz.ratio(original_artist.lower(), spotify_artist.lower())
        title_score = fuzz.ratio(original_title.lower(), spotify_title.lower())

        # Weighted average (title is more important)
        confidence = (title_score * 0.7) + (artist_score * 0.3)
        return confidence / 100.0

    @staticmethod
    def is_good_match(confidence: float, threshold: float = 0.5) -> bool:
        """Determine if a match meets the confidence threshold"""
        return confidence >= threshold

class MigrationReporter:
    """Generates migration reports and statistics"""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_csv_report(self, songs: List[Song], stats: MigrationStats) -> str:
        """Generate detailed CSV report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"migration_report_{timestamp}.csv"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'Original YouTube Title',
                'YouTube Channel',
                'Parsed Artist',
                'Parsed Song Title',
                'Spotify Match Found',
                'Spotify Track URI',
                'Match Confidence Score',
                'Error Details'
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for song in songs:
                writer.writerow({
                    'Original YouTube Title': song.original_title,
                    'YouTube Channel': song.channel_name,
                    'Parsed Artist': song.artist,
                    'Parsed Song Title': song.title,
                    'Spotify Match Found': 'Y' if song.found else 'N',
                    'Spotify Track URI': song.spotify_uri,
                    'Match Confidence Score': f"{song.match_confidence:.2f}",
                    'Error Details': song.error
                })

        logger.info(f"CSV report generated: {filepath}")
        return filepath

    def print_summary(self, stats: MigrationStats):
        """Print migration summary statistics"""
        duration = 0.0
        if stats.end_time and stats.start_time:
            duration = (stats.end_time - stats.start_time).total_seconds()
        success_rate = (stats.successful_matches / stats.total_songs * 100) if stats.total_songs > 0 else 0

        print("\n" + "="*60)
        print("MIGRATION SUMMARY")
        print("="*60)
        print(f"Total songs processed: {stats.total_songs}")
        print(f"Successfully matched: {stats.successful_matches}")
        print(f"Not found on Spotify: {stats.not_found}")
        print(f"Errors encountered: {stats.errors}")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Processing time: {duration:.1f} seconds")
        avg_time = (duration / stats.total_songs) if stats.total_songs > 0 else 0
        print(f"Average time per song: {avg_time:.2f} seconds")
        print("="*60)

class PlaylistMigrator:
    """Main orchestrator for playlist migration"""

    def __init__(self):
        # Validate environment variables
        youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        spotify_client_id = os.getenv('SPOTIFY_CLIENT_ID')
        spotify_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        spotify_user_id = os.getenv('SPOTIFY_USER_ID', '')  # Optional, can be auto-detected

        if not all([youtube_api_key, spotify_client_id, spotify_client_secret]):
            raise ValueError("Missing required environment variables")

        # Type assertions after validation
        assert youtube_api_key is not None
        assert spotify_client_id is not None
        assert spotify_client_secret is not None

        self.youtube = YouTubeExtractor(youtube_api_key)
        self.spotify = SpotifyManager(spotify_client_id, spotify_client_secret, spotify_user_id)
        self.parser = TitleParser()
        self.reporter = MigrationReporter()
        self.matcher = FuzzyMatcher()

    def migrate_playlist(self, youtube_url: str, playlist_name: str,
                        public: bool = True) -> Tuple[List[Song], MigrationStats]:
        """Main migration process"""
        stats = MigrationStats(start_time=datetime.now())
        songs = []

        try:
            # Extract YouTube playlist
            print("🎵 Extracting YouTube playlist...")
            playlist_id = self.youtube.extract_playlist_id(youtube_url)
            if not playlist_id:
                raise ValueError("Invalid YouTube playlist URL")

            video_titles = self.youtube.get_playlist_videos(playlist_id)
            stats.total_songs = len(video_titles)

            if not video_titles:
                raise ValueError("No videos found in playlist")

            print(f"📋 Found {len(video_titles)} videos to process")

            # Process each video
            print("🔍 Searching for matches on Spotify...")
            for i, video_data in enumerate(video_titles, 1):
                song = self._process_song(video_data)
                songs.append(song)

                # Update statistics
                if song.found:
                    stats.successful_matches += 1
                elif song.error:
                    stats.errors += 1
                else:
                    stats.not_found += 1

                # Progress indicator
                if i % 10 == 0 or i == len(video_titles):
                    progress = (i / len(video_titles)) * 100
                    print(f"Progress: {i}/{len(video_titles)} ({progress:.1f}%)")

            # Create Spotify playlist
            print("📝 Creating Spotify playlist...")
            successful_tracks = [song.spotify_uri for song in songs if song.found]

            if successful_tracks:
                description = f"Migrated from YouTube playlist • {stats.successful_matches} tracks"
                playlist_id = self.spotify.create_playlist(playlist_name, description, public)

                if playlist_id:
                    success = self.spotify.add_tracks_to_playlist(playlist_id, successful_tracks)
                    if success:
                        print(f"✅ Successfully created playlist '{playlist_name}' with {len(successful_tracks)} tracks")
                    else:
                        print("❌ Failed to add tracks to playlist")
                else:
                    print("❌ Failed to create Spotify playlist")
            else:
                print("❌ No tracks found to add to playlist")

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            print(f"❌ Migration failed: {e}")

        finally:
            stats.end_time = datetime.now()

        return songs, stats

    def _process_song(self, video_data: Dict[str, str]) -> Song:
        """Process a single song with title and channel information"""
        title = video_data['title']
        channel = video_data['channel']

        song = Song(original_title=title, channel_name=channel)

        try:
            # Parse title to extract artist and song
            parsed_artist, song_title = self.parser.parse_title(title)

            # Use channel name as artist if no artist was parsed from title
            if not parsed_artist and channel:
                # Clean up channel name (remove common suffixes)
                clean_channel = self._clean_channel_name(channel)
                artist = clean_channel
            else:
                artist = parsed_artist

            song.artist = artist
            song.title = song_title

            # Enhanced search strategy with channel information
            spotify_track = self._enhanced_spotify_search(artist, song_title, channel)

            if spotify_track:
                # Get Spotify track details
                spotify_artist = spotify_track['artists'][0]['name']
                spotify_title = spotify_track['name']

                # Calculate match confidence
                confidence = self.matcher.calculate_match_confidence(
                    artist, song_title, spotify_artist, spotify_title
                )

                song.match_confidence = confidence
                song.spotify_uri = spotify_track['uri']
                song.found = self.matcher.is_good_match(confidence)

                if not song.found:
                    song.error = f"Low confidence match ({confidence:.2f})"
            else:
                song.error = "No matches found on Spotify"

        except Exception as e:
            song.error = str(e)
            logger.error(f"Error processing '{title}': {e}")

        return song

    def _clean_channel_name(self, channel: str) -> str:
        """Clean channel name to make it more suitable as artist name"""
        if not channel:
            return ""

        # Remove common suffixes that aren't part of artist names
        suffixes_to_remove = [
            'Official', 'OFFICIAL', 'Records', 'RECORDS', 'Music', 'MUSIC',
            'Channel', 'CHANNEL', 'TV', 'VEVO', 'vevo'
        ]

        cleaned = channel
        for suffix in suffixes_to_remove:
            if cleaned.endswith(f' {suffix}'):
                cleaned = cleaned[:-len(f' {suffix}')]
            elif cleaned.endswith(suffix):
                cleaned = cleaned[:-len(suffix)]

        return cleaned.strip()

    def _enhanced_spotify_search(self, artist: str, title: str, channel: str) -> Optional[Dict]:
        """Enhanced Spotify search using multiple strategies"""
        # Strategy 1: Use parsed artist if available
        if artist and title:
            result = self.spotify.search_track(artist, title)
            if result:
                return result

        # Strategy 2: Use channel name as artist if different from parsed artist
        if channel and channel != artist and title:
            clean_channel = self._clean_channel_name(channel)
            if clean_channel:
                result = self.spotify.search_track(clean_channel, title)
                if result:
                    return result

        # Strategy 3: Search with just the title
        if title:
            result = self.spotify.search_track("", title)
            if result:
                return result

        return None

def validate_environment() -> bool:
    """Validate that all required environment variables are set"""
    required_vars = [
        'YOUTUBE_API_KEY',
        'SPOTIFY_CLIENT_ID',
        'SPOTIFY_CLIENT_SECRET'
    ]

    optional_vars = ['SPOTIFY_USER_ID']  # Can be auto-detected

    placeholder_values = [
        'your_youtube_api_key_here',
        'your_spotify_client_id_here',
        'your_spotify_client_secret_here',
        'your_spotify_username_here'
    ]

    missing_vars = []
    placeholder_vars = []

    # Check required variables
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        elif value in placeholder_values:
            placeholder_vars.append(var)

    # Check optional variables (warn but don't fail)
    for var in optional_vars:
        value = os.getenv(var)
        if not value or value in placeholder_values:
            print(f"ℹ️  {var} will be auto-detected during runtime")

    if missing_vars or placeholder_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var} (not set)")
        for var in placeholder_vars:
            print(f"   - {var} (placeholder value)")
        print("\nPlease check your .env file and ensure all variables are set.")
        return False

    return True

def get_user_input() -> Tuple[str, str, bool]:
    """Get user input for migration parameters"""
    print("🎵 YouTube to Spotify Playlist Migration Tool")
    print("=" * 50)

    # Get YouTube playlist URL
    while True:
        youtube_url = input("\nEnter YouTube playlist URL: ").strip()
        if youtube_url:
            # Basic URL validation
            if 'youtube.com' in youtube_url and ('playlist' in youtube_url or 'list=' in youtube_url):
                break
            else:
                print("❌ Please enter a valid YouTube playlist URL")
        else:
            print("❌ URL cannot be empty")

    # Get playlist name
    while True:
        playlist_name = input("Enter name for new Spotify playlist: ").strip()
        if playlist_name:
            break
        else:
            print("❌ Playlist name cannot be empty")

    # Get privacy setting
    while True:
        public_input = input("Make playlist public? (y/n) [default: y]: ").strip().lower()
        if public_input in ['', 'y', 'yes']:
            public = True
            break
        elif public_input in ['n', 'no']:
            public = False
            break
        else:
            print("❌ Please enter 'y' for yes or 'n' for no")

    return youtube_url, playlist_name, public

def main():
    """Main function"""
    print("🎵 YouTube to Spotify Playlist Migration Tool")
    print("=" * 50)

    # Validate environment
    if not validate_environment():
        return

    try:
        # Get user input
        youtube_url, playlist_name, public = get_user_input()

        # Initialize migrator
        migrator = PlaylistMigrator()

        # Perform migration
        print(f"\n🚀 Starting migration...")
        print(f"YouTube URL: {youtube_url}")
        print(f"Spotify playlist: {playlist_name}")
        print(f"Public: {'Yes' if public else 'No'}")

        songs, stats = migrator.migrate_playlist(youtube_url, playlist_name, public)

        # Generate report
        print("\n📊 Generating migration report...")
        report_path = migrator.reporter.generate_csv_report(songs, stats)

        # Print summary
        migrator.reporter.print_summary(stats)
        print(f"\n📄 Detailed report saved to: {report_path}")

    except KeyboardInterrupt:
        print("\n\n❌ Migration cancelled by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
