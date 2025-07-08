import time
import requests
from flask import Flask, request
from threading import Thread
from Adafruit_IO import MQTTClient
import os

# ------------------- CONFIGURACIÓN -------------------

ADAFRUIT_IO_USERNAME = "doctorhouse"
ADAFRUIT_IO_KEY = os.getenv("ADAFRUIT_IO_KEY")

FEED_ESTADO = "estado"
FEED_ALERTA = "alerta"

TELEGRAM_BOT_TOKEN = "8084980297:AAGaQcduzT1BrkPX03ojtSEBGxVyXoA-tWg"
#TELEGRAM_USER_ID = "7088673190"

TELEGRAM_USER_IDS = ["7088673190", "7969804836"] 
AUTHORIZED_USERS = TELEGRAM_USER_IDS



if not ADAFRUIT_IO_KEY:
    print("🚫 ERROR: ADAFRUIT_IO_KEY no está definida. Verifica las variables de entorno.")
else:
    print("🔐 ADAFRUIT_IO_KEY cargada correctamente.")

# ------------------- FUNCIONES -------------------

#def send_telegram_message(text):
#    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
 #   data = {"chat_id": TELEGRAM_USER_ID, "text": text}
#    try:
#        response = requests.post(url, data=data)
#        print("✅ Mensaje enviado" if response.status_code == 200 else f"⚠️ Telegram error: {response.text}")
#    except Exception as e:
 #       print("🚫 Excepción al enviar a Telegram:", e)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for user_id in TELEGRAM_USER_IDS:
        data = {"chat_id": user_id, "text": text}
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
    print("🟡 mqtt_loop() iniciado...")

    def connected(client):
        print("✅ Conectado a Adafruit IO!")
        client.subscribe(FEED_ESTADO)
        print(f"📡 Suscrito al feed: {FEED_ESTADO}")

    def message(client, feed_id, payload):
        print(f"📨 Mensaje en {feed_id}: {payload}")
        send_telegram_message(f"📡 Estado de la maceta: {payload}")

    while True:
        try:
            print("🔌 Intentando conectar a MQTT...")
            client = MQTTClient(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)
            client.on_connect = connected
            client.on_message = message
            client.connect()
            print("🔄 Esperando mensajes de Adafruit IO (loop_blocking)...")
            client.loop_blocking()
        except Exception as e:
            print("🔁 Error en MQTT, reconectando en 5 segundos:", e)
            time.sleep(5)

# ------------------- FLASK -------------------

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def telegram_webhook():
    if request.method == "GET":
        return "🌐 Backend activo - Adafruit IO ↔ Telegram"

    data = request.get_json()
    print("📥 Datos recibidos:", data)
    try:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"].strip()

        #if str(chat_id) == TELEGRAM_USER_ID:
        if str(chat_id) in AUTHORIZED_USERS:
            lower_text = text.lower()

            if lower_text in ["/riego_on", "/regar"]:
                enviar_a_adafruit("riego_on")
                send_telegram_message("💧 Riego activado.")

            elif lower_text == "/riego_off":
                enviar_a_adafruit("riego_off")
                send_telegram_message("🚿 Riego desactivado.")

            elif lower_text == "/ok":
                enviar_a_adafruit("ok")
                send_telegram_message("✅ Estado 'ok' enviado.")

            elif lower_text.startswith("/set_umbrales:"):
                parametros = text[1:]  # Quita la barra inicial
                enviar_a_adafruit(parametros)
                send_telegram_message(f"📦 Parámetros enviados: `{parametros}`")
            else:
                send_telegram_message(
                    "❓ Comando no reconocido. Usa:\n"
                    "/riego_on\n"
                    "/riego_off\n"
                    "/set_umbrales:40,20,6.5,2000"
                )
        else:
            send_telegram_message("❌ Usuario no autorizado.")
    except Exception as e:
        print("❌ Error procesando mensaje:", e)
    return "OK", 200

# ------------------- INICIO AUTOMÁTICO (para Render) -------------------

print("🚀 Iniciando backend Flask + MQTT (con Thread)...")

mqtt_thread = Thread(target=mqtt_loop, daemon=True)
mqtt_thread.start()

