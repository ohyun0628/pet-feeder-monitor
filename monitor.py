# monitor.py - 센서 측정 + 경고 판단 + MQTT 전송 (10-2mqtt.py 확장)
import os, json, time, queue
from datetime import datetime
from collections import deque
import paho.mqtt.client as mqtt
import circuit

BASE = os.path.dirname(os.path.abspath(__file__))
PHOTO_DIR = os.path.join(BASE, "static", "photos")
FEED_LOG = os.path.join(BASE, "feed_log.json")
CALIB_FILE = os.path.join(BASE, "calib.json")
os.makedirs(PHOTO_DIR, exist_ok=True)

LOW_LEVEL = 20      # 잔량(%)이 이 값 이하면 경고
HUMID_LIMIT = 70    # 습도(%)가 이 값 이상이면 경고
NIGHT_LIGHT = 800   # 조도값이 이 값 미만이면 밤 (환경에 맞게 조정)
PERIOD = 2          # 측정 주기(초)

def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default

def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False)

calib = load(CALIB_FILE, {"full": 5.0, "empty": 20.0})   # 센서~사료 거리(cm)
feeds = load(FEED_LOG, [])
actions = queue.Queue()                                   # 버튼/웹 명령을 메인 루프에서 처리

def to_level(dist):
    span = calib["empty"] - calib["full"]
    if span <= 0:
        return 0.0
    return max(0.0, min(100.0, (calib["empty"] - dist) / span * 100))

def eta_minutes(hist):
    # 최근 잔량 변화의 기울기(최소제곱법)로 소진까지 남은 시간(분)을 추정
    if len(hist) < 10:
        return None
    t0 = hist[0][0]
    xs = [h[0] - t0 for h in hist]
    ys = [h[1] for h in hist]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den   # %/초
    if slope > -0.002:                                               # 거의 안 줄면 추정 안 함
        return None
    return round(ys[-1] / (-slope) / 60, 1)

def on_connect(c, userdata, flags, rc, prop=None):
    c.subscribe("pet/led")      # 웹 -> LED 제어 (10-3 예제 방식)
    c.subscribe("pet/cmd")      # 웹 -> feed / calib_full / calib_empty

def on_message(c, userdata, msg):
    payload = msg.payload.decode()
    if msg.topic == "pet/led":
        circuit.led(1 if payload == "1" else 0)
    else:
        actions.put(payload)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883)
client.loop_start()

def do_feed(level):                       # 급식 기록: 사진 촬영 + 로그 저장 + 웹 전송
    now = datetime.now()
    name = "feed_%s.jpg" % now.strftime("%Y%m%d_%H%M%S")
    ok = circuit.capture_photo(os.path.join(PHOTO_DIR, name))
    rec = {"time": now.strftime("%m-%d %H:%M:%S"), "level": round(level),
           "photo": "photos/" + name if ok else None}
    feeds.append(rec)
    del feeds[:-50]
    save(FEED_LOG, feeds)
    client.publish("pet/feed", json.dumps(rec, ensure_ascii=False))

def handle(cmd, level, dist):
    if cmd == "feed":
        do_feed(level)
    elif cmd == "calib_full" and dist:    # 지금 거리 = 사료 가득 찼을 때
        calib["full"] = dist
        save(CALIB_FILE, calib)
    elif cmd == "calib_empty" and dist:   # 지금 거리 = 사료 비었을 때
        calib["empty"] = dist
        save(CALIB_FILE, calib)

circuit.on_button(lambda: actions.put("feed"))   # 물리 버튼 = 급식 기록

dist, level, temp, hum = None, 0.0, None, None
prev_alert = False
hist = deque(maxlen=60)
print("모니터링 시작 (Ctrl+C로 종료)")
try:
    while True:
        d = circuit.measure_median()
        if d is not None:
            dist, level = d, to_level(d)
        try:
            temp, hum = circuit.read_env()
        except Exception:
            pass                           # 가끔 I2C 읽기 실패 -> 이전 값 유지
        light = circuit.read_light()
        hist.append((time.time(), level))

        reasons = []
        if level <= LOW_LEVEL:
            reasons.append("사료가 %d%% 남았어요" % level)
        if hum is not None and hum >= HUMID_LIMIT:
            reasons.append("습도가 높아요 (%d%%)" % hum)
        alert = bool(reasons)
        if alert != prev_alert:            # 상태가 바뀔 때만 LED 변경(9-2 예제 방식)
            circuit.led(1 if alert else 0)
        prev_alert = alert

        while not actions.empty():
            handle(actions.get(), level, dist)

        status = {"t": datetime.now().strftime("%H:%M:%S"),
                  "level": round(level, 1),
                  "dist": round(dist, 1) if dist else None,
                  "temp": round(temp, 1) if temp is not None else None,
                  "hum": round(hum, 1) if hum is not None else None,
                  "light": light, "night": light < NIGHT_LIGHT,
                  "alerts": reasons, "led": circuit.led_state,
                  "eta_min": eta_minutes(hist)}
        client.publish("pet/status", json.dumps(status, ensure_ascii=False))
        time.sleep(PERIOD)
except KeyboardInterrupt:
    pass
finally:
    client.loop_stop()
    client.disconnect()
    circuit.cleanup()
