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
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            'id': info.get('id'),
            'title': info.get('title'),
            'url': url,
            'thumbnail': info.get('thumbnail'),
            'duration': info.get('duration'),
            'added_time': time.time()
        }

def download_and_play_video(video_info):
    """Stream and play a YouTube video"""
    global player, current_video

    # Streaming options
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
    }

    try:
        # Get the direct streaming URL
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_info['url'], download=False)
            url = info['url']

        # Play the audio directly from the URL
        with player_lock:
            if player:
                player.stop()

            instance = vlc.Instance()
            player = instance.media_player_new()
            media = instance.media_new(url)
            player.set_media(media)
            player.play()

            # Wait for the player to start
            time.sleep(1)

            # Get the duration and wait for it to finish
            duration = player.get_length() / 1000  # Convert to seconds

            # If duration is not available, use the one from video_info
            if duration <= 0 and video_info.get('duration'):
                duration = video_info['duration']

            # Wait for the video to finish
            time.sleep(duration)

            # Clean up
            player.stop()

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

if __name__ == '__main__':
    # Start the player thread
    start_player_thread()

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
