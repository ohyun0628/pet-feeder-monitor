# 강아지 사료 모니터 (라즈베리파이)

2026학년도 모바일스마트시스템 라즈베리 프로젝트.

초음파·온습도·조도 센서로 사료 잔량을 재고, 웹 대시보드에서 급식 기록과 경고를 확인합니다.

## 파일 구조
```
mos.conf               Mosquitto 설정 (교재 10장과 동일)
circuit.py             센서/LED/버튼/카메라 제어
monitor.py             측정 + 경고 판단 + MQTT 전송
app.py                 Flask 웹 서버
templates/index.html   대시보드
static/mqttio.js       브라우저용 MQTT(웹소켓) 코드
```

보정값(`calib.json`), 급식 기록(`feed_log.json`), 촬영 사진은 저장소에 올리지 않습니다.

## 회로 (GPIO 번호 / BCM)
| 부품 | 핀 |
|---|---|
| LED (+220Ω) | GPIO6 |
| 버튼 | GPIO21 |
| 초음파 Trig / Echo | GPIO20 / GPIO16 (Echo는 교재 8.4 분압 회로 그대로) |
| HTU21D | GPIO2(SDA) / GPIO3(SCL) |
| MCP3202 + 조도 | MOSI 10, MISO 9, SCLK 11, CS 12 |
| USB 카메라 | USB 포트 |

## 준비 (한 번만)
1. `sudo raspi-config` 에서 I2C, SPI 활성화 (교재 9장)
2. 가상환경에서 설치 (myenv)
```
pip install -r requirements.txt
```

## 실행 (터미널 3개, 모두 source myenv/bin/activate)
```
터미널1: mosquitto -v -c mos.conf
터미널2: python monitor.py
터미널3: python app.py
```
PC/스마트폰 브라우저에서 `http://라즈베리파이IP:8080` 접속 (같은 공유기).

## 사료량 보정 (처음에 꼭)
1. 통에 사료를 가득 채우고 대시보드 > 사료량 보정 > "가득 참(100%)으로"
2. 사료를 비우고 "빈 통(0%)으로"
(기본값: 가득 5cm, 빈 통 20cm. 보정값은 calib.json에 저장됨)

## 조절할 값 (monitor.py 위쪽)
- LOW_LEVEL 20: 잔량 경고 기준(%)
- HUMID_LIMIT 70: 습도 경고 기준(%)
- NIGHT_LIGHT 800: 낮/밤 구분 기준 (9-3 예제로 밝기 값을 먼저 확인하고 조정)

## 문제 해결
- 거리가 계속 None: Trig/Echo 배선과 분압 회로 확인. 센서와 사료 사이 최소 거리 2cm 이상
- 온습도 오류: `i2cdetect -y 1` 에서 0x40 확인
- 사진이 안 찍힘: `ls /dev/video*` 로 카메라 인식 확인, 5장 예제 4-2 먼저 실행
- 웹은 뜨는데 값이 안 옴: mosquitto 실행 여부, 9001 포트 설정(mos.conf) 확인
