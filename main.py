import time
import requests
from flask import Flask, request
from multiprocessing import Process
from Adafruit_IO import MQTTClient
import os

# ------------------- CONFIGURACIÓN -------------------

ADAFRUIT_IO_USERNAME = "doctorhouse"
ADAFRUIT_IO_KEY = os.getenv("ADAFRUIT_IO_KEY")

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
        print("✅ Mensaje enviado" if response.status_code == 200 else f"⚠️ Telegram error: {response.text}")
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
            print(f"❌ Error Adafruit: {r.text}")
            send_telegram_message(f"❌ Error enviando a Adafruit: {r.text}")
    except Exception as e:
        print("🚫 Excepción al enviar a Adafruit:", e)
        send_telegram_message("🚫 No se pudo enviar a Adafruit.")

# ------------------- MQTT -------------------

def mqtt_loop():
    def connected(client):
        print("✅ Conectado a Adafruit IO!")
        client.subscribe(FEED_ESTADO)

    def message(client, feed_id, payload):
        print(f"📨 Mensaje en {feed_id}: {payload}")
        send_telegram_message(f"📡 Estado de la maceta: {payload}")

    while True:
        try:
            client = MQTTClient(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)
            client.on_connect = connected
            client.on_message = message
            client.connect()
            client.loop_blocking()  # Espera bloqueante (más confiable que loop_background)
        except Exception as e:
            print("🔁 Error en MQTT, reconectando en 5 segundos:", e)
            time.sleep(5)

# ------------------- FLASK -------------------

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def telegram_webhook():
    if request.method == "GET":
        return "🌐 Backend activo - Adafruit IO ↔ Telegram"

    print("📥 Encabezados recibidos:", dict(request.headers))
    print("📥 Cuerpo crudo:", request.data)

    try:
        data = request.get_json(force=True)
        print("📥 Datos recibidos (JSON):", data)

  
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"].lower().strip()
        if str(chat_id) == TELEGRAM_USER_ID:
            if text in ["/riego_on", "/regar"]:
                enviar_a_adafruit("riego_on")
                send_telegram_message("💧 Riego activado.")
            elif text == "/riego_off":
                enviar_a_adafruit("riego_off")
                send_telegram_message("🚿 Riego desactivado.")
            elif text == "/ok":
                enviar_a_adafruit("ok")
                send_telegram_message("✅ Estado 'ok' enviado.")
            else:
                send_telegram_message("❓ Comando no reconocido. Usa:\n/riego_on\n/riego_off\n/ok")
        else:
            send_telegram_message("❌ Usuario no autorizado.")
    except Exception as e:
        print("❌ Error procesando mensaje:", e)
    return "OK", 200

# ------------------- MAIN -------------------

if __name__ == "__main__":
    # Ejecutar MQTT en proceso separado (más robusto que hilo)
    mqtt_process = Process(target=mqtt_loop)
    mqtt_process.start()

    # Ejecutar Flask
    app.run(host="0.0.0.0", port=8080)
