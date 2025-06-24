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
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'noplaylist': True,
        'quiet': False,  # Set to False for debugging
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        # Add user-agent to avoid restrictions
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
    }

    try:
        print(f"Extracting info for URL: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # Verify we have the necessary information
            if not info.get('id') or not info.get('title'):
                print(f"Warning: Incomplete video information extracted: {info}")

            # For debugging, print available formats
            if 'formats' in info:
                print("Available formats:")
                for fmt in info.get('formats', []):
                    print(f"  {fmt.get('format_id')}: {fmt.get('ext')} - {fmt.get('format_note', 'N/A')}")

            return {
                'id': info.get('id'),
                'title': info.get('title', 'Unknown Title'),
                'url': url,
                'thumbnail': info.get('thumbnail', ''),
                'duration': info.get('duration', 0),
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
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'quiet': False,  # Set to False to see detailed output for debugging
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        # Add user-agent to avoid restrictions
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
    }

    try:
        # Get the direct streaming URL
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Extracting audio from: {video_info['url']}")
            info = ydl.extract_info(video_info['url'], download=False)

            # Make sure we have a valid URL
            if 'url' not in info:
                print("Error: No URL found in extracted info")
                return

            url = info['url']
            print(f"Extracted audio URL: {url}")

        # Play the audio directly from the URL
        with player_lock:
            if player:
                player.stop()
                player.release()
                player = None

            # Create a new VLC instance with verbose logging and audio output configuration
            vlc_args = [
                '--verbose=2',                # Verbose logging
                '--aout=alsa',                # Use ALSA audio output
                '--alsa-audio-device=default' # Use default ALSA device (3.5mm jack if configured)
            ]
            instance = vlc.Instance(' '.join(vlc_args))
            player = instance.media_player_new()

            # Try to set audio output device explicitly
            try:
                # Get list of audio output devices
                audio_output = instance.audio_output_enumerate_devices()
                if audio_output:
                    print("Available audio output devices:")
                    for device in audio_output:
                        print(f"  - {device.description} ({device.device})")

                    # Try to find and use the 3.5mm jack
                    for device in audio_output:
                        if "analog" in device.description.lower() or "headphones" in device.description.lower():
                            print(f"Setting audio output to: {device.description}")
                            player.audio_output_device_set(None, device.device)
                            break
            except Exception as e:
                print(f"Error setting audio output device: {e}")

            # Create media with proper options
            media = instance.media_new(url)
            media.add_option('network-caching=1000')  # Increase network buffer

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
    global player

    with player_lock:
        if player:
            player.stop()

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
