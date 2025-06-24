import time
import requests
from flask import Flask, request
from threading import Thread
from Adafruit_IO import MQTTClient

# ------------------- CONFIGURACIÓN -------------------

ADAFRUIT_IO_USERNAME = "doctorhouse"
ADAFRUIT_IO_KEY = "aio_UwyK493ilX13uOIw21bmorXEW5cL"
FEED_ESTADO = "estado"
FEED_ALERTA = "alerta"

TELEGRAM_BOT_TOKEN = "8084980297:AAGaQcduzT1BrkPX03ojtSEBGxVyXoA-tWg"
TELEGRAM_USER_ID = "7088673190"

# ------------------- FUNCIONES -------------------

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_USER_ID, "text": text}
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("✅ Mensaje enviado a Telegram.")
        else:
            print("⚠️ Error al enviar a Telegram:", response.text)
    except Exception as e:
        print("🚫 Excepción al enviar a Telegram:", e)

def enviar_a_adafruit(valor):
    url = f"https://io.adafruit.com/api/v2/{ADAFRUIT_IO_USERNAME}/feeds/{FEED_ALERTA}/data"
    headers = {"X-AIO-Key": ADAFRUIT_IO_KEY, "Content-Type": "application/json"}
    data = {"value": valor}
    try:
        r = requests.post(url, json=data, headers=headers)
        if r.status_code == 200:
            print(f"📤 Enviado a Adafruit IO: {valor}")
        else:
            print("❌ Error al enviar a Adafruit:", r.text)
    except Exception as e:
        print("🚫 Excepción al enviar a Adafruit:", e)

# ------------------- MQTT CALLBACKS -------------------

def connected(client):
    print("✅ Conectado a Adafruit IO!")
    client.subscribe(FEED_ESTADO)

def message(client, feed_id, payload):
    print(f"📨 Mensaje recibido en {feed_id}: {payload}")
    send_telegram_message(f"📡 Estado de la maceta: {payload}")

def iniciar_mqtt():
    client = MQTTClient(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)
    client.on_connect = connected
    client.on_message = message
    client.connect()
    client.loop_blocking()

# ------------------- FLASK -------------------

app = Flask(__name__)

@app.route("/")
def home():
    return "🌐 Backend activo - Adafruit IO ↔ Telegram"

@app.route(f"/webhook/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    print("📥 Datos recibidos:", data)

    try:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]

        if str(chat_id) == TELEGRAM_USER_ID:
            cmd = text.lower().strip()

            print("💬 Comando recibido de Telegram:", cmd)

            if cmd in ["/riego_on", "/regar"]:
                enviar_a_adafruit("riego_on")
                send_telegram_message("💧 Riego activado.")
            elif cmd == "/riego_off":
                enviar_a_adafruit("riego_off")
                send_telegram_message("🚿 Riego desactivado.")
            elif cmd == "/ok":
                enviar_a_adafruit("ok")
                send_telegram_message("✅ Estado 'ok' enviado.")
            else:
                send_telegram_message("❓ Comando no reconocido. Usa:\n/riego_on\n/riego_off\n/ok")
        else:
            send_telegram_message("❌ Usuario no autorizado.")

    except Exception as e:
        print("❌ Error procesando mensaje:", e)

    return "OK", 200

def iniciar_web():
    app.run(host="0.0.0.0", port=8080)

# ------------------- MAIN -------------------

if __name__ == "__main__":
    Thread(target=iniciar_web).start()
    time.sleep(1)
    iniciar_mqtt()
