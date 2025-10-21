from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import yt_dlp
import subprocess
import logging

# === ✅ yt-dlp ロガー定義 ===
class YTDLPLogger:
    def debug(self, msg):
        logging.debug(msg)

    def warning(self, msg):
        logging.warning(msg)

    def error(self, msg):
        logging.error(msg)

# === ✅ Flask 設定 ===
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.DEBUG)  # DEBUGログ有効化

@app.route('/get-audio', methods=['POST'])
def get_audio():
    data = request.get_json()
    logging.info(f"📩 Received data: {data}")

    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL missing'}), 400

    if not url.startswith("https://www.youtube.com") and not url.startswith("https://youtu.be"):
        return jsonify({'error': 'Invalid URL'}), 400

    # === ✅ yt-dlp オプション（Cookieなし）===
    ydl_opts = {
        'quiet': False,
        'no_warnings': False,
        'cachedir': False,
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'verbose': True,
        'logger': YTDLPLogger()
    }

    try:
        results = []

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            uploader = info.get('uploader_id')
            if uploader:
                logging.info(f"✅ 動画のアップロード者: {uploader}")
            else:
                logging.warning("⚠️ ログインしていないか、uploader_id が取得できませんでした")

            if 'entries' in info:
                video_urls = [
                    f"https://www.youtube.com/watch?v={e['id']}"
                    for e in info['entries']
                    if isinstance(e, dict) and e.get('id')
                ]
            else:
                video_urls = [info['webpage_url']]

        # === ✅ 実際の音声URLを取得 ===
        audio_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio',
            'quiet': False,
            'no_warnings': False,
            'cachedir': False,
            'logger': YTDLPLogger(),
            'verbose': True
        }

        with yt_dlp.YoutubeDL(audio_opts) as ydl:
            for v_url in video_urls:
                try:
                    info = ydl.extract_info(v_url, download=False)
                    audio_url = info.get('url')
                    title = info.get('title', 'No title')
                    duration = int(info.get('duration', 0))
                    if audio_url:
                        results.append({
                            'title': title,
                            'url': audio_url,
                            'duration': duration
                        })
                except Exception as e:
                    logging.error(f"❌ Failed to process {v_url}: {e}")

        return jsonify({'tracks': results})

    except Exception as e:
        logging.error(f"❌ Extraction error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/stream', methods=['GET'])
def stream_audio():
    url = request.args.get('url')
    if not url:
        return Response("Missing audio URL", status=400)

    try:
        ffmpeg_cmd = [
            'ffmpeg',
            '-re',
            '-reconnect', '1',
            '-reconnect_streamed', '1',
            '-reconnect_delay_max', '5',
            '-i', url,
            '-vn',
            '-c:a', 'libmp3lame',
            '-b:a', '192k',
            '-f', 'mp3',
            'pipe:1'
        ]

        logging.info(f"▶️ Streaming via ffmpeg: {url}")
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        return Response(
            process.stdout,
            mimetype='audio/mpeg',
            headers={
                'Content-Disposition': 'inline; filename="stream.mp3"',
                'Accept-Ranges': 'bytes',
                'Access-Control-Allow-Origin': '*'
            }
        )
    except Exception as e:
        logging.error(f"❌ Streaming error: {e}")
        return Response(f"Error: {e}", status=500)
