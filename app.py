# app.py - Flask 웹 서버 (10-2app.py 확장): 대시보드 + 급식 기록 API
import os, json
from flask import Flask, render_template, jsonify

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0          # 캐시 방지(교재와 동일)
FEED_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feed_log.json")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/feeds')                              # 새로고침해도 급식 기록 유지
def feeds():
    try:
        with open(FEED_LOG) as f:
            return jsonify(json.load(f)[::-1])        # 최신순
    except (OSError, ValueError):
        return jsonify([])

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=False)
