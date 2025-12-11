import json
import queue
import threading
import pandas as pd
import streamlit as st
import paho.mqtt.client as mqtt
from datetime import datetime

# ============================
# MQTT CONFIG
# ============================
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

TOPIC_SENSOR = "alat/data/complete"     # sesuai ESP32
TOPIC_OUTPUT = "iot/sic/output"         # sesuai ESP32

GLOBAL_MQ = queue.Queue()


# ============================
# MQTT CALLBACK
# ============================
def on_connect(client, userdata, flags, rc):
    print("Connected:", rc)
    client.subscribe(TOPIC_SENSOR)
    print("Subscribed to", TOPIC_SENSOR)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except:
        print("Invalid JSON:", msg.payload)
        return

    data = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "asap": payload.get("asap"),
        "cahaya": payload.get("cahaya"),
        "suhu": payload.get("suhu"),
    }

    GLOBAL_MQ.put(data)


# ============================
# MQTT BACKGROUND THREAD
# ============================
def mqtt_worker():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()


# ============================
# STREAMLIT PAGE SETUP
# ============================
st.set_page_config("IoT Sensor Dashboard", layout="wide")
st.title("📡 IoT Sensor Dashboard — ESP32")


# ============================
# SESSION STATE INIT
# ============================
if "msg_queue" not in st.session_state:
    st.session_state.msg_queue = GLOBAL_MQ

for key in ["logs_asap", "logs_cahaya", "logs_suhu",
            "latest_asap", "latest_cahaya", "latest_suhu",
            "mqtt_started"]:
    if key not in st.session_state:
        st.session_state[key] = [] if "logs" in key else None

# start MQTT only once
if not st.session_state.mqtt_started:
    thread = threading.Thread(target=mqtt_worker, daemon=True)
    thread.start()
    st.session_state.mqtt_started = True
# ============================
# PROCESS INCOMING MQTT DATA
# ============================
while not st.session_state.msg_queue.empty():
    row = st.session_state.msg_queue.get()

    # update "latest"
    st.session_state.latest_asap = row["asap"]
    st.session_state.latest_cahaya = row["cahaya"]
    st.session_state.latest_suhu = row["suhu"]

    # append to history logs
    st.session_state.logs_asap.append(row["asap"])
    st.session_state.logs_cahaya.append(row["cahaya"])
    st.session_state.logs_suhu.append(row["suhu"])
# ============================
# LAYOUT — REALTIME SENSOR DISPLAY
# ============================
col1, col2 = st.columns(2)

with col1:
    st.subheader("📟 Real-time Sensor Data")

    asap_val = st.session_state.latest_asap
    cahaya_val = st.session_state.latest_cahaya
    suhu_val = st.session_state.latest_suhu

    st.metric("Asap", f"{asap_val if asap_val is not None else '-'}")
    st.metric("Cahaya", f"{cahaya_val if cahaya_val is not None else '-'}")
    st.metric("Suhu", f"{suhu_val if suhu_val is not None else '-'} °C")

    st.write("---")
    # ============================
    # SEND OUTPUT TO ESP32
    # ============================
    st.subheader("🔊 Kirim Perintah ke ESP32 (Buzzer)")

    client_pub = mqtt.Client()
    client_pub.connect(MQTT_BROKER, MQTT_PORT, 60)

    if st.button("Nyalakan Buzzer"):
        msg = {"buzzer": 1}
        client_pub.publish(TOPIC_OUTPUT, json.dumps(msg))
        st.success("Buzzer ON terkirim!")

    if st.button("Matikan Buzzer"):
        msg = {"buzzer": 0}
        client_pub.publish(TOPIC_OUTPUT, json.dumps(msg))
        st.info("Buzzer OFF terkirim!")
# ============================
# LAYOUT — CHARTS
# ============================
st.subheader("📊 Grafik Sensor")

if len(st.session_state.logs_asap) > 0:

    df = pd.DataFrame({
        "Asap": st.session_state.logs_asap,
        "Cahaya": st.session_state.logs_cahaya,
        "Suhu": st.session_state.logs_suhu,
    })

    st.line_chart(df)

else:
    st.info("Menunggu data dari ESP32...")

st.write("---")

# ============================
# LAYOUT — LOG TABLE
# ============================
st.subheader("📋 Log Data Sensor (History)")

if len(st.session_state.logs_asap) > 0:

    df_table = pd.DataFrame({
        "Asap": st.session_state.logs_asap,
        "Cahaya": st.session_state.logs_cahaya,
        "Suhu": st.session_state.logs_suhu,
    })

    st.dataframe(df_table, use_container_width=True)

else:
    st.info("Belum ada data yang tersimpan.")

st.write("---")
st.caption("Sistem IoT Fire Detection — SIC Project")
