// mqttio.js - 교재 mqttio1.js를 자동 접속/재접속 + 명령 전송이 되도록 확장
let client = null;
const CLIENT_ID = "web-" + Math.floor(Math.random() * 1e9).toString(16);

function mqttConnect(onMessage, onState) {
  client = new Paho.MQTT.Client(location.hostname, 9001, CLIENT_ID);   // 웹 서버 IP = 브로커 IP
  client.onMessageArrived = (m) => onMessage(m.destinationName, m.payloadString);
  client.onConnectionLost = () => { onState(false); setTimeout(() => mqttConnect(onMessage, onState), 2000); };
  client.connect({
    onSuccess: () => { client.subscribe("pet/status"); client.subscribe("pet/feed"); onState(true); },
    onFailure: () => { onState(false); setTimeout(() => mqttConnect(onMessage, onState), 2000); }
  });
}

function mqttSend(topic, payload) {            // 웹 -> 라즈베리파이 명령 전송
  if (!client || !client.isConnected()) return;
  const m = new Paho.MQTT.Message(String(payload));
  m.destinationName = topic;
  client.send(m);
}
