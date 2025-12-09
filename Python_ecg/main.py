import asyncio
import socket
import numpy as np
import neurokit2 as nk
import time
import keyboard 
import random

# --- CONFIGURATION ---
USE_SIMULATION = True  # <--- False if you want to use a real Movesense sensor
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
SAMPLING_RATE = 250

# --- SETUP UDP ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ecg_buffer = []
last_analysis_time = 0 # Variable to limit calculation frequency

# --- CONDITIONAL DRIVER IMPORT ---
if not USE_SIMULATION:
    try:
        from ifch_drivers.movesense_gatt import MovesenseGatt
    except ImportError:
        print("❌ ERREUR : Driver 'ifch_drivers' manquant. Passage forcé en SIMULATION.")
        USE_SIMULATION = True

# ==========================================
# 🧠 SYSTEM CORE
# ==========================================
def process_incoming_data(samples):
    """
    Function called very often by Bluetooth (every ~50ms).
    OPTIMIZATION: We store everything, but only calculate once per second.
    """
    global ecg_buffer, last_analysis_time
    
    # 1. ACQUISITION (Fast): We always store data to avoid losing anything
    ecg_buffer.extend(samples)

    # 2. MEMORY CLEANUP (Fast): Keep max 20 sec
    if len(ecg_buffer) > SAMPLING_RATE * 20:
        ecg_buffer = ecg_buffer[-(SAMPLING_RATE * 10):]

    # 3. TIME LOCK (Throttling)
    # If it's been less than a second since the last calculation, stop here.
    # This frees up the CPU to handle Bluetooth.
    current_time = time.time()
    if current_time - last_analysis_time < 1.0:
        return

    # If we get here, it's time for the calculation!
    last_analysis_time = current_time

    # 4. HEAVY ANALYSIS (Slow)
    WINDOW_SIZE = SAMPLING_RATE * 10
    if len(ecg_buffer) >= WINDOW_SIZE:
        try:
            data_chunk = np.array(ecg_buffer[-WINDOW_SIZE:])
            
            # NeuroKit: This step consumes CPU
            ecg_clean = nk.ecg_clean(data_chunk, sampling_rate=SAMPLING_RATE)
            peaks, _ = nk.ecg_peaks(ecg_clean, sampling_rate=SAMPLING_RATE)
            hrv = nk.hrv_time(peaks, sampling_rate=SAMPLING_RATE)
            rmssd = hrv["HRV_RMSSD"].values[0]

            if np.isnan(rmssd): rmssd = 0.0

            # Envoi UDP
            send_to_unity(rmssd)

        except Exception:
            pass 

def send_to_unity(rmssd_score):
    """Sends the score and displays feedback"""
    try:
        # Console Feedback with newline (\r) for cleanliness
        bar_len = int(rmssd_score / 5)
        visual = "█" * bar_len
        state = "🟢 ZEN" if rmssd_score > 40 else "🔴 STRESS"
        
        # Trailing spaces help erase previous characters
        print(f"UDP -> {rmssd_score:.2f} ms | {state} | {visual}      ", end="\r")

        sock.sendto(str(rmssd_score).encode(), (UDP_IP, UDP_PORT))
    except Exception as e:
        print(f"UDP Error: {e}")

# ==========================================
# MODE 1 : Real SENSOR
# ==========================================
def real_sensor_callback(device, data):
    timestamps, samples, sensor = data
    if samples and len(samples) > 0:
        process_incoming_data(samples)

async def run_real_sensor():
    print("🔵 Searching for Movesense sensor...")
    found = await MovesenseGatt.detect_devices()
    if not found:
        print("❌ No sensor found. Check Bluetooth.")
        return

    print(f"✅ Sensor: {found[0][0]}")
    device = MovesenseGatt(found[0][0], found[0][1], stream_callback=real_sensor_callback)
    
    await device.start()
    await device.subscribe("/Meas/ECG/250")
    
    print("🚀 Streaming Real ECG in progress... (Ctrl+C to stop)")
    try:
        while True: await asyncio.sleep(1)
    finally:
        await device.unsubscribe_all()
        await device.stop()

# ==========================================
# MODE 2 
# ==========================================
async def run_simulation():
    print("\n MODE WIZARD OF OZ (Keyboard) ACTIVATED\n")
    print("   [SPACE] Tap quickly = STRESS")
    print("   [NONE]  Wait = ZEN\n")
    
    clicks_history = []
    WINDOW_SECONDS = 5 
    
    while True:
        current_time = time.time()
        
        if keyboard.is_pressed('space'):
            if not clicks_history or current_time - clicks_history[-1] > 0.1:
                clicks_history.append(current_time)

        clicks_history = [t for t in clicks_history if current_time - t <= WINDOW_SECONDS]
        
        click_count = len(clicks_history)
        target_rmssd = 90 - (click_count * 6)
        pseudo_rmssd = max(10, min(100, target_rmssd)) + random.uniform(-1.5, 1.5)

        send_to_unity(pseudo_rmssd)
        await asyncio.sleep(0.05)

# --- MAIN ---
if __name__ == "__main__":
    try:
        if USE_SIMULATION:
            asyncio.run(run_simulation())
        else:
            asyncio.run(run_real_sensor())
    except KeyboardInterrupt:
        print("\nArrêt.")
