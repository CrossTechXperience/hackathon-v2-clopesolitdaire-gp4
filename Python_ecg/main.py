import asyncio
import socket
import numpy as np
import neurokit2 as nk
import time

# --- CONFIGURATION ---
USE_SIMULATION = True  # <--- METTRE SUR 'FALSE' SUR LE PC DU HACKATHON
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
SAMPLING_RATE = 250

# --- SETUP UDP ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ecg_buffer = []

# --- IMPORT CONDITIONNEL DU DRIVER ---
# Cela permet au script de se lancer chez toi même sans le driver installé
if not USE_SIMULATION:
    try:
        from ifch_drivers.movesense_gatt import MovesenseGatt
    except ImportError:
        print("❌ ERREUR : Driver 'ifch_drivers' manquant. Passez en USE_SIMULATION = True.")
        exit()

# --- COEUR DU SYSTÈME (Logique Partagée) ---
def process_incoming_data(samples):
    """
    Cette fonction est appelée par le Simulateur OU par le Vrai Capteur.
    C'est ici que se trouve ton intelligence.
    """
    global ecg_buffer
    
    # 1. Ajouter au buffer
    ecg_buffer.extend(samples)

    # 2. Nettoyage mémoire (Garde max 20 sec)
    if len(ecg_buffer) > SAMPLING_RATE * 20:
        ecg_buffer = ecg_buffer[-(SAMPLING_RATE * 10):]

    # 3. Analyse (Si on a assez de données - 10 sec)
    WINDOW_SIZE = SAMPLING_RATE * 10
    if len(ecg_buffer) >= WINDOW_SIZE:
        try:
            data_chunk = np.array(ecg_buffer[-WINDOW_SIZE:])
            
            # NeuroKit Magic
            ecg_clean = nk.ecg_clean(data_chunk, sampling_rate=SAMPLING_RATE)
            peaks, _ = nk.ecg_peaks(ecg_clean, sampling_rate=SAMPLING_RATE)
            hrv = nk.hrv_time(peaks, sampling_rate=SAMPLING_RATE)
            rmssd = hrv["HRV_RMSSD"].values[0]

            if np.isnan(rmssd): rmssd = 0.0

            # Feedback Console
            # On affiche une barre pour visualiser le stress (Court = Stress, Long = Zen)
            bar_len = int(rmssd / 5)
            visual = "█" * bar_len
            state = "🟢 ZEN" if rmssd > 40 else "🔴 STRESS"
            
            print(f"UDP -> {rmssd:.2f} ms | {state} | {visual}")

            # Envoi UDP
            sock.sendto(str(rmssd).encode(), (UDP_IP, UDP_PORT))

        except Exception:
            pass # Calcul impossible (signal trop court ou bruité)

# --- MODE 1 : LE VRAI CAPTEUR ---
def real_sensor_callback(device, data):
    timestamps, samples, sensor = data
    if samples and len(samples) > 0:
        process_incoming_data(samples)

async def run_real_sensor():
    print("🔵 Démarrage en mode VRAI CAPTEUR...")
    found = await MovesenseGatt.detect_devices()
    if not found:
        print("❌ Aucun capteur trouvé.")
        return

    print(f"✅ Capteur : {found[0][0]}")
    device = MovesenseGatt(found[0][0], found[0][1], stream_callback=real_sensor_callback)
    
    await device.start()
    await device.subscribe("/Meas/ECG/250")
    
    print("🚀 Streaming ECG Réel en cours...")
    try:
        while True: await asyncio.sleep(1)
    finally:
        await device.unsubscribe_all()
        await device.stop()

# --- MODE 2 : LE SIMULATEUR (Pour toi) ---
import keyboard # N'oublie pas d'ajouter cet import tout en haut du fichier !
import random
import time

async def run_simulation():
    print("🎹 MODE WIZARD OF OZ (Simulation Clavier) ACTIVÉ")
    print("   - Spammez la barre ESPACE pour simuler le STRESS.")
    print("   - Ne faites rien pour simuler le ZEN.")
    print("   - (L'app Unity va recevoir des valeurs de RMSSD simulées)")
    
    clicks_history = []
    WINDOW_SECONDS = 5 # On regarde la densité de clics sur 5 secondes
    
    while True:
        current_time = time.time()
        
        # 1. DÉTECTION DU CLICK
        # keyboard.is_pressed est non-bloquant, parfait pour une boucle async
        if keyboard.is_pressed('space'):
            # Petit anti-rebond pour éviter de compter 100 clics si on reste appuyé
            if not clicks_history or current_time - clicks_history[-1] > 0.1:
                clicks_history.append(current_time)

        # 2. NETTOYAGE (Fenêtre glissante)
        # On ne garde que les clics récents
        clicks_history = [t for t in clicks_history if current_time - t <= WINDOW_SECONDS]
        
        # 3. CALCUL DU "FAUX RMSSD"
        # Plus on clique, plus le RMSSD baisse (Stress)
        click_count = len(clicks_history)
        
        # Formule magique pour le Hackathon :
        # 0 clics = RMSSD 90 (Zen absolu)
        # 10 clics en 5s (2 clics/sec) = RMSSD 30 (Seuil Stress)
        # 15+ clics = RMSSD 10 (Panique)
        target_rmssd = 90 - (click_count * 6)
        
        # On borne entre 10ms et 100ms et on ajoute du "bruit" pour faire vivant
        pseudo_rmssd = max(10, min(100, target_rmssd)) + random.uniform(-1.5, 1.5)

        # 4. ENVOI UDP
        sock.sendto(str(pseudo_rmssd).encode(), (UDP_IP, UDP_PORT))
        
        # 5. FEEDBACK VISUEL CONSOLE
        bar = "█" * int(pseudo_rmssd / 5)
        status = "🟢 ZEN" if pseudo_rmssd > 40 else "🔴 STRESS"
        print(f"Clicks: {click_count} | RMSSD: {pseudo_rmssd:.1f} ms | {status} | {bar}   ", end="\r")

        # Pause asynchrone (très important pour ne pas figer le PC)
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