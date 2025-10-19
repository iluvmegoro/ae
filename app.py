from flask import Flask, request, jsonify
import yt_dlp

app = Flask(__name__)


@app.route('/get-audio', methods=['POST'])
def get_audio():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL missing'}), 400

    results = []
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',
        'force_generic_extractor': False,
        'skip_download': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # 単曲 or プレイリスト判定
            if 'entries' in info:
                entries = info['entries']
                video_urls = [f"https://www.youtube.com/watch?v={e['id']}" for e in entries]
            else:
                video_urls = [info['webpage_url']]

        # 各URLの音声URL取得（形式限定で品質安定）
        audio_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio',
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(audio_opts) as ydl:
            for v_url in video_urls:
                try:
                    info = ydl.extract_info(v_url, download=False)
                    audio_url = info.get('url')
                    title = info.get('title', 'No title')
                    duration = info.get('duration', 0)
                    if audio_url:
                        results.append({
                            'title': title,
                            'url': audio_url,
                            'duration': duration
                        })
                except Exception as e:
                    print(f"Error on {v_url}: {e}")

        return jsonify({'tracks': results})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
