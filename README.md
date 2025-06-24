# Junie-Pie: Raspberry Pi YouTube Queue Player

Junie-Pie is a web application that turns your Raspberry Pi 4 into a shared YouTube audio playback device. Multiple users can add videos to a shared queue, and the Raspberry Pi will play them in the order they were added through the 3.5mm audio port connected to a stereo system.

## Features

- Add YouTube videos to a shared playback queue
- Low-latency streaming of YouTube audio (no download required)
- Automatically plays videos in the order they were added
- Simple web interface accessible from any device on the same network
- Displays currently playing video and upcoming queue
- Skip current video functionality
- Audio playback through the Raspberry Pi's 3.5mm audio port

## Requirements

- Raspberry Pi 4 (or newer)
- Stereo system connected to the Raspberry Pi's 3.5mm audio port
- VLC media player installed on the Raspberry Pi
- Python 3.7 or newer

## Installation

1. Clone this repository to your Raspberry Pi:

```bash
git clone https://github.com/yourusername/Junie-Pie.git
cd Junie-Pie
```

2. Install VLC media player if not already installed:

```bash
sudo apt update
sudo apt install vlc
```

3. Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:

```bash
python app.py
```

2. Access the web interface by navigating to `http://[raspberry-pi-ip]:5000` in a web browser from any device on the same network.

3. Add YouTube videos to the queue by pasting the YouTube URL and clicking "Add to Queue".

4. The Raspberry Pi will automatically play the videos in the order they were added.

5. You can skip the current video by clicking the "Skip Current" button.

## How It Works

- The application uses Flask to create a web server that hosts the user interface.
- YouTube videos are streamed directly using yt-dlp to extract the streaming URL and VLC media player to play the audio stream.
- This streaming approach eliminates the need to download videos first, reducing latency and providing a smoother experience.
- A background thread continuously checks the queue and plays videos as they are added.
- The web interface updates in real-time to show the current playing video and the queue.

## Troubleshooting

- If you encounter audio issues, make sure your Raspberry Pi's audio output is set to the 3.5mm jack:
  ```bash
  sudo raspi-config
  ```
  Then navigate to System Options > Audio > 3.5mm jack.

- If videos aren't playing or there's no audio output:
  - Make sure VLC is properly installed: `sudo apt install vlc`
  - Ensure your Raspberry Pi has internet access
  - Update yt-dlp to the latest version: `pip install -U yt-dlp`
  - Check the console output for errors when videos are added to the queue
  - Test audio output directly with: `aplay /usr/share/sounds/alsa/Front_Center.wav`
  - Try playing a YouTube video directly with VLC to verify your setup: `vlc https://www.youtube.com/watch?v=dQw4w9WgXcQ`
  - Verify that your 3.5mm jack is working by connecting headphones and testing

- If you see YouTube API errors or "Precondition check failed" messages:
  - YouTube may be blocking requests from your IP or the Raspberry Pi
  - The application will automatically try multiple extraction methods with different configurations
  - If all extraction methods fail, try these solutions:
    - Restart the application (sometimes temporary issues resolve themselves)
    - Update yt-dlp to the latest version: `pip install -U yt-dlp`
    - Try a different YouTube video (some videos have more restrictions than others)
    - Consider using a VPN or proxy if YouTube is blocking your region

- If you see "Signature extraction failed" or "Only images are available" errors:
  - This is a known issue with some YouTube videos and yt-dlp
  - The application includes multiple fallback methods to try different extraction approaches
  - If all methods fail, try a different YouTube video or update yt-dlp

- If you see "HTTP 404 error" messages:
  - The application will validate URLs before attempting playback to avoid this issue
  - If you still see these errors, it may indicate that YouTube has changed their API
  - Update yt-dlp to the latest version: `pip install -U yt-dlp`

- If the web interface isn't accessible, ensure you're using the correct IP address and that the Raspberry Pi is on the same network as your device.

- For more detailed debugging, check the application logs in the terminal where you started the app. The application includes comprehensive logging to help diagnose issues.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
