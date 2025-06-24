from flask import Flask, render_template, request, redirect, url_for, jsonify
import threading
import time
import os
import yt_dlp
import vlc

app = Flask(__name__)

# Video queue to store YouTube video information
video_queue = []
current_video = None
player = None
player_lock = threading.Lock()
queue_lock = threading.Lock()

# Thread for playing videos
player_thread = None
player_thread_running = False

def extract_video_info(url):
    """Extract video information from YouTube URL"""
    # Use the same improved options as in download_and_play_video
    ydl_opts = {
        # More specific format selection to target audio streams
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio[ext=webm]/bestaudio/best',
        'noplaylist': True,
        'quiet': False,  # Set to False for debugging
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        # Updated user-agent to a more recent browser version
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        },
        # Add youtube-dl specific options
        'youtube_include_dash_manifest': False,
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],
                'skip': ['hls', 'dash'],
            }
        }
    }

    try:
        print(f"Extracting info for URL: {url}")

        # First attempt with standard options
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # Check if we got actual audio formats
                if 'formats' in info:
                    audio_formats = [f for f in info.get('formats', []) 
                                    if f.get('acodec') != 'none' and f.get('vcodec') == 'none']

                    print("Available formats:")
                    for fmt in info.get('formats', []):
                        print(f"  {fmt.get('format_id')}: {fmt.get('ext')} - {fmt.get('format_note', 'N/A')}")

                    if not audio_formats:
                        print("Warning: No audio-only formats found")

                # Verify we have the necessary information
                if not info.get('id') or not info.get('title'):
                    print(f"Warning: Incomplete video information extracted: {info}")

                return {
                    'id': info.get('id'),
                    'title': info.get('title', 'Unknown Title'),
                    'url': url,
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': info.get('duration', 0),
                    'added_time': time.time()
                }

        except Exception as e:
            print(f"First info extraction attempt failed: {e}")
            print("Trying alternative extraction method...")

            # Second attempt with different options
            alt_opts = ydl_opts.copy()
            alt_opts['format'] = 'bestaudio/best'  # Simpler format selection
            alt_opts['youtube_include_dash_manifest'] = True  # Try including DASH

            try:
                with yt_dlp.YoutubeDL(alt_opts) as alt_ydl:
                    info = alt_ydl.extract_info(url, download=False)

                    # Verify we have the necessary information
                    if not info.get('id') or not info.get('title'):
                        print(f"Warning: Incomplete video information extracted (second attempt): {info}")

                    return {
                        'id': info.get('id'),
                        'title': info.get('title', 'Unknown Title'),
                        'url': url,
                        'thumbnail': info.get('thumbnail', ''),
                        'duration': info.get('duration', 0),
                        'added_time': time.time()
                    }
            except Exception as e:
                print(f"Second info extraction attempt failed: {e}")
                print("Trying third extraction method...")

                # Third attempt with completely different approach
                third_opts = {
                    'format': 'bestaudio',
                    'quiet': False,
                    'no_warnings': False,
                    'nocheckcertificate': True,
                    'ignoreerrors': False,
                    'logtostderr': False,
                    'geo_bypass': True,  # Try to bypass geo-restrictions
                    'geo_bypass_country': 'US',  # Pretend to be in the US
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    },
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['web'],  # Try web client instead
                            'skip': [],  # Don't skip any formats
                        }
                    }
                }

                try:
                    with yt_dlp.YoutubeDL(third_opts) as third_ydl:
                        info = third_ydl.extract_info(url, download=False)

                        # Verify we have the necessary information
                        if not info.get('id') or not info.get('title'):
                            print(f"Warning: Incomplete video information extracted (third attempt): {info}")
                            raise Exception("Incomplete video information")

                        return {
                            'id': info.get('id'),
                            'title': info.get('title', 'Unknown Title'),
                            'url': url,
                            'thumbnail': info.get('thumbnail', ''),
                            'duration': info.get('duration', 0),
                            'added_time': time.time()
                        }
                except Exception as e:
                    print(f"Third info extraction attempt failed: {e}")
                    print("Trying fourth extraction method with invidious API...")

                    # Fourth attempt using invidious API as a fallback
                    try:
                        import requests
                        import json
                        import random

                        # List of public invidious instances
                        invidious_instances = [
                            "https://invidious.snopyta.org",
                            "https://yewtu.be",
                            "https://invidious.kavin.rocks",
                            "https://vid.puffyan.us",
                            "https://invidious.namazso.eu"
                        ]

                        # Select a random instance
                        instance = random.choice(invidious_instances)
                        video_id = url.split('v=')[1].split('&')[0] if 'v=' in url else url.split('/')[-1]
                        api_url = f"{instance}/api/v1/videos/{video_id}"

                        print(f"Trying invidious API for info extraction: {api_url}")

                        response = requests.get(api_url, timeout=10)
                        if response.status_code == 200:
                            data = response.json()

                            return {
                                'id': video_id,
                                'title': data.get('title', 'Unknown Title (Invidious)'),
                                'url': url,
                                'thumbnail': data.get('thumbnailUrl', ''),
                                'duration': data.get('lengthSeconds', 0),
                                'added_time': time.time()
                            }
                        else:
                            print(f"Invidious API returned status code: {response.status_code}")
                    except Exception as e:
                        print(f"Invidious API info extraction failed: {e}")

                    # If all methods fail, return minimal info
                    return {
                        'id': 'unknown',
                        'title': f"Unknown Title (URL: {url})",
                        'url': url,
                        'thumbnail': '',
                        'duration': 0,
                        'added_time': time.time()
                    }

    except Exception as e:
        print(f"Error extracting video info: {e}")
        # Return minimal info so the queue still works
        return {
            'id': 'error',
            'title': f"Error: {str(e)[:50]}...",
            'url': url,
            'thumbnail': '',
            'duration': 0,
            'added_time': time.time()
        }

def download_and_play_video(video_info):
    """Stream and play a YouTube video"""
    global player, current_video

    # Streaming options with improved configuration
    ydl_opts = {
        # More specific format selection to target audio streams
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio[ext=webm]/bestaudio/best',
        'quiet': False,  # Set to False to see detailed output for debugging
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        # Updated user-agent to a more recent browser version
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        },
        # Add youtube-dl specific options
        'youtube_include_dash_manifest': False,  # Skip DASH manifests that might cause issues
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],  # Try android client which might be more reliable
                'skip': ['hls', 'dash'],  # Skip HLS and DASH formats which might cause issues
            }
        }
    }

    try:
        # Get the direct streaming URL
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Extracting audio from: {video_info['url']}")

            # First attempt with standard options
            try:
                info = ydl.extract_info(video_info['url'], download=False)

                # Check if we got actual audio formats or just images
                if 'formats' in info:
                    audio_formats = [f for f in info.get('formats', []) 
                                    if f.get('acodec') != 'none' and f.get('vcodec') == 'none']

                    if not audio_formats and 'url' in info:
                        # If no specific audio formats but we have a direct URL, check if it's not an image
                        if any(img_ext in info['url'] for img_ext in ['.jpg', '.jpeg', '.png', '.webp']):
                            print("Warning: URL appears to be an image, not an audio stream")
                            raise Exception("No valid audio stream found, only images")

                # Make sure we have a valid URL
                if 'url' not in info:
                    print("Error: No URL found in extracted info")
                    raise Exception("No URL found in extracted info")

                url = info['url']

                # Check if URL is an image (storyboard)
                if any(img_ext in url for img_ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    print(f"Warning: Extracted URL appears to be an image: {url}")
                    raise Exception("Extracted URL is an image, not an audio stream")

                print(f"Extracted audio URL: {url}")

            except Exception as e:
                print(f"First extraction attempt failed: {e}")
                print("Trying alternative extraction method...")

                # Second attempt with different options
                alt_opts = ydl_opts.copy()
                alt_opts['format'] = 'bestaudio/best'  # Simpler format selection
                alt_opts['youtube_include_dash_manifest'] = True  # Try including DASH

                try:
                    with yt_dlp.YoutubeDL(alt_opts) as alt_ydl:
                        info = alt_ydl.extract_info(video_info['url'], download=False)

                        # Make sure we have a valid URL
                        if 'url' not in info:
                            print("Error: No URL found in second extraction attempt")
                            raise Exception("No URL found in second extraction attempt")

                        url = info['url']
                        print(f"Extracted audio URL (second attempt): {url}")
                except Exception as e:
                    print(f"Second extraction attempt failed: {e}")
                    print("Trying third extraction method...")

                    # Third attempt with completely different approach
                    third_opts = {
                        'format': 'bestaudio',
                        'quiet': False,
                        'no_warnings': False,
                        'nocheckcertificate': True,
                        'ignoreerrors': False,
                        'logtostderr': False,
                        'geo_bypass': True,  # Try to bypass geo-restrictions
                        'geo_bypass_country': 'US',  # Pretend to be in the US
                        'http_headers': {
                            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
                            'Accept-Language': 'en-US,en;q=0.5',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                        },
                        'extractor_args': {
                            'youtube': {
                                'player_client': ['web'],  # Try web client instead
                                'skip': [],  # Don't skip any formats
                            }
                        }
                    }

                    with yt_dlp.YoutubeDL(third_opts) as third_ydl:
                        info = third_ydl.extract_info(video_info['url'], download=False)

                        # Make sure we have a valid URL
                        if 'url' not in info:
                            print("Error: No URL found in third extraction attempt")
                            print("Trying fourth extraction method with invidious API...")

                            # Fourth attempt using invidious API as a fallback
                            try:
                                import requests
                                import json
                                import random

                                # List of public invidious instances
                                invidious_instances = [
                                    "https://invidious.snopyta.org",
                                    "https://yewtu.be",
                                    "https://invidious.kavin.rocks",
                                    "https://vid.puffyan.us",
                                    "https://invidious.namazso.eu"
                                ]

                                # Select a random instance
                                instance = random.choice(invidious_instances)
                                video_id = video_info['url'].split('v=')[1].split('&')[0]
                                api_url = f"{instance}/api/v1/videos/{video_id}"

                                print(f"Trying invidious API: {api_url}")

                                response = requests.get(api_url, timeout=10)
                                if response.status_code == 200:
                                    data = response.json()

                                    # Find audio streams
                                    audio_formats = [f for f in data.get('adaptiveFormats', []) 
                                                    if f.get('type', '').startswith('audio/')]

                                    if audio_formats:
                                        # Sort by bitrate (highest first)
                                        audio_formats.sort(key=lambda x: x.get('bitrate', 0), reverse=True)
                                        url = audio_formats[0]['url']
                                        print(f"Extracted audio URL (invidious API): {url}")
                                        return url
                                    else:
                                        print("No audio formats found in invidious API response")
                            except Exception as e:
                                print(f"Invidious API extraction failed: {e}")

                            # If we get here, all extraction methods have failed
                            print("All extraction methods failed, cannot play this video")
                            return

                        url = info['url']
                        print(f"Extracted audio URL (third attempt): {url}")

        # Final validation check for the URL
        if not url:
            print("Error: No URL extracted after all attempts")
            return

        # Check if URL is an image or storyboard
        if any(img_ext in url.lower() for img_ext in ['.jpg', '.jpeg', '.png', '.webp', 'storyboard']):
            print(f"Error: Invalid audio URL detected: {url}")
            print("URL appears to be an image or storyboard, not an audio stream")

            # Try one more approach - direct YouTube embed URL
            try:
                print("Attempting to use YouTube embed URL as a last resort...")
                video_id = None

                # Extract video ID from the original URL
                if "youtube.com/watch?v=" in video_info['url']:
                    video_id = video_info['url'].split("v=")[1].split("&")[0]
                elif "youtu.be/" in video_info['url']:
                    video_id = video_info['url'].split("youtu.be/")[1].split("?")[0]

                if video_id:
                    # Try to use the YouTube embed URL which sometimes works when the API fails
                    embed_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1&controls=0"
                    print(f"Using YouTube embed URL: {embed_url}")

                    # This is a workaround - VLC might be able to extract the audio from the embed page
                    url = embed_url
                else:
                    print("Could not extract video ID from URL")
                    return
            except Exception as e:
                print(f"Error creating embed URL: {e}")
                return

        # Check if URL is accessible
        try:
            import urllib.request
            import urllib.error

            print(f"Validating URL accessibility: {url}")
            req = urllib.request.Request(
                url, 
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Range': 'bytes=0-1000'  # Just request the first 1000 bytes to check accessibility
                }
            )
            response = urllib.request.urlopen(req, timeout=5)
            content_type = response.headers.get('Content-Type', '')

            print(f"URL validation successful. Content-Type: {content_type}")

            # Check if content type is audio or video
            if not any(media_type in content_type.lower() for media_type in ['audio', 'video', 'mp4', 'mp3', 'ogg', 'webm']):
                print(f"Warning: Content-Type does not appear to be audio/video: {content_type}")
                # Continue anyway as VLC might still be able to handle it

        except urllib.error.HTTPError as e:
            print(f"HTTP Error validating URL: {e.code} - {e.reason}")
            if e.code == 404:
                print("URL returns 404 Not Found, cannot play this stream")
                return
            # For other HTTP errors, we'll still try to play
            print("Continuing despite HTTP error...")
        except Exception as e:
            print(f"Error validating URL: {e}")
            print("Continuing anyway...")

        # Play the audio directly from the URL
        with player_lock:
            if player:
                player.stop()
                player.release()
                player = None

            # Create a new VLC instance with verbose logging and audio output configuration
            vlc_args = [
                '--verbose=3',                # More verbose logging for debugging
                '--aout=alsa',                # Use ALSA audio output
                '--alsa-audio-device=default', # Use default ALSA device (3.5mm jack if configured)
                '--audio-filter=compressor',  # Add audio compression to normalize volume
                '--file-caching=3000',        # Increase file cache
                '--network-caching=3000',     # Increase network cache
                '--sout-mux-caching=3000',    # Increase mux cache
                '--no-video',                 # Disable video output since we only need audio
                '--audio-replay-gain-mode=track' # Apply replay gain
            ]
            instance = vlc.Instance(' '.join(vlc_args))
            player = instance.media_player_new()

            # Set audio output volume to maximum
            player.audio_set_volume(100)

            # Try to set audio output device explicitly
            try:
                # Get list of audio output devices
                audio_output = instance.audio_output_enumerate_devices()
                if audio_output:
                    print("Available audio output devices:")
                    for device in audio_output:
                        try:
                            print(f"  - {device.description} ({device.device})")
                        except:
                            print(f"  - Device info unavailable")

                    # First try to find and use the headphones/analog output
                    headphones_device = None
                    for device in audio_output:
                        try:
                            desc = str(device.description).lower()
                            if "analog" in desc or "headphones" in desc or "3.5" in desc or "bcm2835" in desc:
                                headphones_device = device
                                print(f"Found headphones/analog device: {device.device}")
                                break
                        except:
                            continue

                    # If headphones device found, use it
                    if headphones_device:
                        try:
                            print(f"Setting audio output to: {headphones_device.device}")
                            player.audio_output_device_set(None, headphones_device.device)
                        except Exception as e:
                            print(f"Error setting headphones device: {e}")
                    else:
                        print("No headphones/analog device found, using default")
            except Exception as e:
                print(f"Error enumerating audio output devices: {e}")
                print("Falling back to default audio device")

            # Create media with proper options
            media = instance.media_new(url)

            # Add media options for better streaming
            media.add_option(':network-caching=3000')  # Increase network buffer
            media.add_option(':file-caching=3000')     # Increase file buffer
            media.add_option(':sout-mux-caching=3000') # Increase mux buffer
            media.add_option(':no-video')              # Disable video
            media.add_option(':audio-filter=compressor') # Add audio compression

            # Set up event manager to monitor playback
            events = player.event_manager()

            # Set media to player and start playback
            player.set_media(media)
            print("Starting playback...")
            result = player.play()
            print(f"Play command result: {result}")

            # Wait for the player to start and check if it's actually playing
            time.sleep(3)
            state = player.get_state()
            print(f"Player state after 3 seconds: {state}")

            if state == vlc.State.Error:
                print("VLC player reported an error state")
                return

            if state != vlc.State.Playing:
                print(f"VLC player is not in playing state, current state: {state}")
                # Try to play again
                player.stop()
                player.play()
                time.sleep(2)
                state = player.get_state()
                print(f"Player state after retry: {state}")

                if state != vlc.State.Playing:
                    print("Failed to start playback after retry")
                    return

            # Get the duration and wait for it to finish
            duration = player.get_length() / 1000  # Convert to seconds
            print(f"Media duration from VLC: {duration} seconds")

            # If duration is not available, use the one from video_info
            if duration <= 0 and video_info.get('duration'):
                duration = video_info['duration']
                print(f"Using duration from video info: {duration} seconds")

            if duration <= 0:
                print("Warning: Could not determine media duration, using default")
                duration = 300  # Default to 5 minutes if we can't determine duration

            # Wait for the video to finish, checking periodically if it's still playing
            elapsed = 0
            check_interval = 5  # Check every 5 seconds
            while elapsed < duration:
                time.sleep(check_interval)
                elapsed += check_interval

                state = player.get_state()
                if state != vlc.State.Playing:
                    print(f"Player is no longer playing, state: {state}")
                    break

                print(f"Still playing... {elapsed}/{duration} seconds elapsed")

            # Clean up
            print("Stopping playback")
            player.stop()
            player.release()

    except Exception as e:
        print(f"Error playing video: {e}")

    finally:
        with queue_lock:
            current_video = None

def player_thread_function():
    """Thread function to continuously play videos from the queue"""
    global player_thread_running, current_video

    while player_thread_running:
        # Check if there are videos in the queue and no video is currently playing
        with queue_lock:
            if video_queue and current_video is None:
                current_video = video_queue.pop(0)

        # If we have a video to play, play it
        if current_video:
            download_and_play_video(current_video)

        # Sleep a bit to prevent high CPU usage
        time.sleep(1)

def start_player_thread():
    """Start the player thread if it's not already running"""
    global player_thread, player_thread_running

    if player_thread is None or not player_thread.is_alive():
        player_thread_running = True
        player_thread = threading.Thread(target=player_thread_function)
        player_thread.daemon = True
        player_thread.start()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/add', methods=['POST'])
def add_video():
    """Add a video to the queue"""
    url = request.form.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        # Extract video information
        video_info = extract_video_info(url)

        # Add to queue
        with queue_lock:
            video_queue.append(video_info)

        # Make sure the player thread is running
        start_player_thread()

        return redirect(url_for('index'))

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/queue', methods=['GET'])
def get_queue():
    """Get the current queue"""
    with queue_lock:
        queue_copy = video_queue.copy()

    return jsonify({
        'current': current_video,
        'queue': queue_copy
    })

@app.route('/skip', methods=['POST'])
def skip_video():
    """Skip the current video"""
    global player, current_video

    with player_lock:
        if player:
            player.stop()

    # Reset current_video so the player thread picks up the next video
    with queue_lock:
        current_video = None

    return redirect(url_for('index'))

def configure_audio_output():
    """Configure audio output to use 3.5mm jack on Raspberry Pi"""
    try:
        # Try to set the audio output to 3.5mm jack using amixer
        # This is specific to Raspberry Pi
        import subprocess

        print("Configuring audio output to 3.5mm jack...")

        # Check if we're running on a Raspberry Pi
        try:
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read()
                if 'Raspberry Pi' in model:
                    print(f"Detected Raspberry Pi: {model}")
                else:
                    print(f"Not running on a Raspberry Pi: {model}")
                    return
        except:
            print("Could not determine if running on Raspberry Pi, skipping audio configuration")
            return

        # Set audio output to 3.5mm jack
        subprocess.run(['amixer', 'cset', 'numid=3', '1'], check=True)
        print("Audio output set to 3.5mm jack")

        # Set volume to 100%
        subprocess.run(['amixer', 'set', 'Master', '100%'], check=True)
        print("Volume set to 100%")

        # Test audio output
        print("Testing audio output...")
        test_file = '/usr/share/sounds/alsa/Front_Center.wav'
        if os.path.exists(test_file):
            subprocess.run(['aplay', test_file], check=False)
            print("Audio test complete")
        else:
            print(f"Audio test file not found: {test_file}")

    except Exception as e:
        print(f"Error configuring audio output: {e}")
        print("Audio configuration failed, but continuing anyway")

if __name__ == '__main__':
    # Configure audio output
    configure_audio_output()

    # Start the player thread
    start_player_thread()

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
