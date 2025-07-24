#!/usr/bin/env python3
"""
Example usage demonstrating core functionality.
"""

from youtube_to_spotify import TitleParser, FuzzyMatcher

def demo_title_parsing():
    """Demonstrate title parsing functionality"""
    print("🎵 Title Parsing Demo")
    print("=" * 40)
    
    parser = TitleParser()
    
    test_titles = [
        "The Beatles - Hey Jude",
        "Queen: Bohemian Rhapsody",
        "Imagine by John Lennon",
        "Pink Floyd | Wish You Were Here",
        "Led Zeppelin \"Stairway to Heaven\"",
        "Adele - Rolling in the Deep (Official Video)",
        "Ed Sheeran - Shape of You [Official Video]",
        "Taylor Swift - Anti-Hero (feat. Bleachers)"
    ]
    
    for title in test_titles:
        artist, song = parser.parse_title(title)
        print(f"Original: {title}")
        print(f"  Artist: '{artist}'")
        print(f"  Song:   '{song}'")
        print()

def demo_fuzzy_matching():
    """Demonstrate fuzzy matching functionality"""
    print("🔍 Fuzzy Matching Demo")
    print("=" * 40)
    
    matcher = FuzzyMatcher()
    
    test_cases = [
        # (original_artist, original_song, spotify_artist, spotify_song)
        ("The Beatles", "Hey Jude", "The Beatles", "Hey Jude"),
        ("Queen", "Bohemian Rhapsody", "Queen", "Bohemian Rhapsody"),
        ("Led Zeppelin", "Stairway to Heaven", "Led Zeppelin", "Stairway To Heaven"),
        ("Pink Floyd", "Wish You Were Here", "Pink Floyd", "Wish You Were Here"),
        ("Adele", "Rolling in the Deep", "Adele", "Rolling In the Deep"),
        ("Ed Sheeran", "Shape of You", "Ed Sheeran", "Shape Of You"),
        ("The Beatles", "Hey Jude", "Beatles", "Hey Jude"),  # Slight artist difference
        ("Queen", "Bohemian Rhapsody", "Queen", "Bohemian Rhap"),  # Truncated title
    ]
    
    for orig_artist, orig_song, spot_artist, spot_song in test_cases:
        confidence = matcher.calculate_match_confidence(
            orig_artist, orig_song, spot_artist, spot_song
        )
        is_good = matcher.is_good_match(confidence)
        
        print(f"Original: {orig_artist} - {orig_song}")
        print(f"Spotify:  {spot_artist} - {spot_song}")
        print(f"Confidence: {confidence:.2f} ({'✅ Good match' if is_good else '❌ Poor match'})")
        print()

def demo_url_extraction():
    """Demonstrate YouTube URL parsing"""
    print("🔗 YouTube URL Parsing Demo")
    print("=" * 40)
    
    from youtube_to_spotify import YouTubeExtractor
    
    # Create extractor (API key not needed for URL parsing)
    extractor = YouTubeExtractor("dummy_key")
    
    test_urls = [
        "https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "https://youtube.com/watch?v=dQw4w9WgXcQ&list=PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx&index=1",
        "https://music.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "invalid_url",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # No playlist
    ]
    
    for url in test_urls:
        playlist_id = extractor.extract_playlist_id(url)
        print(f"URL: {url}")
        print(f"Playlist ID: {playlist_id if playlist_id else 'Not found'}")
        print()

if __name__ == "__main__":
    print("🎵 YouTube to Spotify Migration Tool - Component Demo")
    print("=" * 60)
    print()
    
    demo_title_parsing()
    print()
    demo_fuzzy_matching()
    print()
    demo_url_extraction()
    
    print("Demo completed! 🎉")
    print("\nTo run the full migration, use: python youtube_to_spotify.py")
