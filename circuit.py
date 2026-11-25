# circuit.py - 센서/LED/버튼/카메라 제어 모듈
# 핀 배치는 교재 8장(LED/스위치/초음파)과 9장(HTU21D/조도)을 그대로 사용
import time
import RPi.GPIO as GPIO
import board, busio, digitalio
import cv2
from adafruit_htu21d import HTU21D
import adafruit_mcp3xxx.mcp3008 as MCP        # 교재 9-3과 동일(MCP3202 연결)
from adafruit_mcp3xxx.analog_in import AnalogIn

LED, BUTTON, TRIG, ECHO = 6, 21, 20, 16       # GPIO 번호(BCM)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(LED, GPIO.OUT)
GPIO.setup(BUTTON, GPIO.IN, GPIO.PUD_DOWN)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

i2c = busio.I2C(board.SCL, board.SDA)         # GPIO3(SCL), GPIO2(SDA)
htu = HTU21D(i2c)
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
cs = digitalio.DigitalInOut(board.D12)        # GPIO12
light_ch = AnalogIn(MCP.MCP3008(spi, cs), MCP.P0)

led_state = 0

def led(on):                                  # LED 켜기/끄기 (0/1)
    global led_state
    led_state = 1 if on else 0
    GPIO.output(LED, led_state)

def on_button(callback):                      # 8-3 예제: 바운스 시간 + 콜백
    GPIO.add_event_detect(BUTTON, GPIO.RISING, callback=lambda ch: callback(), bouncetime=300)

def measure_distance():                       # 8-6 예제 + 무한루프 방지(타임아웃)
    time.sleep(0.06)
    GPIO.output(TRIG, 1)
    time.sleep(0.00001)
    GPIO.output(TRIG, 0)
    t0 = time.time()
    while GPIO.input(ECHO) == 0:
        if time.time() - t0 > 0.05:
            return None
    start = time.time()
    while GPIO.input(ECHO) == 1:
        if time.time() - start > 0.05:
            return None
    return (time.time() - start) * 340 * 100 / 2   # cm

def measure_median(n=5):                      # 5회 측정 후 중앙값 -> 튀는 값 제거
    vals = sorted(v for v in (measure_distance() for _ in range(n)) if v is not None)
    return vals[len(vals) // 2] if vals else None

def read_env():                               # 9-1 예제: (온도, 습도)
    return float(htu.temperature), float(htu.relative_humidity)

def read_light():                             # 9-3 예제: 0~4095, 클수록 밝음
    return light_ch.value // 16

def capture_photo(path):                      # 5장 OpenCV 사진 촬영
    cam = cv2.VideoCapture(0)
    try:
        for _ in range(5):                    # 노출 안정화용으로 몇 장 버림
            cam.read()
        ok, frame = cam.read()
        if ok:
            cv2.imwrite(path, frame)
        return ok
    finally:
        cam.release()

def cleanup():
    GPIO.cleanup()
