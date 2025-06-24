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

- If videos aren't playing, check that VLC is properly installed and that the Raspberry Pi has internet access.

- If the web interface isn't accessible, ensure you're using the correct IP address and that the Raspberry Pi is on the same network as your device.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
