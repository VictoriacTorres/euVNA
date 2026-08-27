"""
Barrido de RF + adquisición + cálculo de S11, todo en un solo script.

Por cada frecuencia del barrido:
    1. Se le manda la frecuencia al Arduino (adf4351_serial.ino) por serial.
    2. Se graba una captura corta desde la entrada line-in (ref = canal
       izquierdo, medición = canal derecho).
    3. Se filtra cada canal con un FIR pasabanda alrededor de 1 kHz.
    4. Se calcula la FFT compleja de ambos canales.
     5. Se toma el bin de FFT más cercano a 1 kHz en el canal de referencia,
         y se toma el mismo bin en el canal de medición.
    6. S11_punto = medición[bin] / referencia[bin].

Al terminar el barrido, se desenrolla la fase acumulada y se grafica
|S11| (dB) y fase (grados) en función de la frecuencia de RF. También se
guardan los resultados crudos en un .csv para post-procesar con el
algoritmo de calibración.

Requisitos:
    pip install pyserial sounddevice numpy scipy matplotlib
"""

import csv
import time

import numpy as np
import matplotlib.pyplot as plt
import serial
import sounddevice as sd
from scipy.signal import firwin, lfilter
from scipy.signal.windows import get_window


# ==================== Configuración: Arduino / barrido de RF ====================

PUERTO = "COM3"          # Windows: "COM3", "COM5", etc. Linux/Mac: "/dev/ttyACM0"
BAUDRATE = 115200

F_INICIO_MHZ = 1700.000
F_FIN_MHZ = 2300.000
F_PASO_MHZ = 1.000
FRECUENCIAS_EXCLUIDAS_MHZ = [] #400.00,  550.0, 560.0, 800.0, 1700.0, 1100.0, 1600.0, 1240.0, 720.0, 1540.0, 1570.0, 550.0, 850.0
# ==================== Configuración: adquisición de audio ====================

FS_AUDIO = 44100
DURACION_CAPTURA_S = 1.0  # 1 seg

# Índice del dispositivo de audio a usar (line-in). None = dispositivo de
# entrada por defecto del sistema. Si tenés dudas de cuál es, corré:
#   python -c "import sounddevice as sd; print(sd.query_devices())"
# y poné acá el índice que corresponda a tu placa de sonido / line-in.
DISPOSITIVO_AUDIO = None

# ==================== Configuración: filtro FIR + FFT ====================

F_CENTRO_FILTRO = 10000       # Hz, tono de batido esperado
ANCHO_BANDA_FILTRO = 200     # Hz
NUMTAPS_FILTRO = 1001        # debe ser menor que la cantidad de muestras por captura

VENTANA_FFT = "flattop"

# Banda donde se busca el pico del tono de batido (Hz)
BANDA_BUSQUEDA_PICO = (F_CENTRO_FILTRO - ANCHO_BANDA_FILTRO / 2,
                        F_CENTRO_FILTRO + ANCHO_BANDA_FILTRO / 2)

# ==================== Salida ====================

ARCHIVO_CSV = "S11_sincalibracion_sinsaltear_10k.csv"

# ==================== Arduino / serial ====================

def generar_frecuencias(inicio, fin, paso):
    """Genera la lista de frecuencias evitando arrastre de error de punto flotante."""
    n_pasos = round((fin - inicio) / paso)
    return [inicio + i * paso for i in range(n_pasos + 1)]


def conectar_arduino(puerto, baudrate):
    ser = serial.Serial(puerto, baudrate, timeout=5)
    time.sleep(2)  # el Arduino se resetea al abrir el puerto; esperamos a que arranque
    ser.reset_input_buffer()

    linea = ser.readline().decode(errors="ignore").strip()
    if linea:
        print(f"Arduino: {linea}")

    return ser


def setear_frecuencia(ser, f_mhz):
    """Manda la frecuencia al Arduino y espera la confirmación."""
    comando = f"{f_mhz:.6f}\n"
    ser.write(comando.encode())

    respuesta = ser.readline().decode(errors="ignore").strip()
    while respuesta and not respuesta.startswith("OK") and not respuesta.startswith("ERROR"):
        print("  (Arduino):", respuesta)
        respuesta = ser.readline().decode(errors="ignore").strip()

    return respuesta


# ==================== Adquisición ====================

def capturar_audio(duracion_s, fs, dispositivo=None):
    """
    Graba desde la entrada configurada. Devuelve (canal_ref, canal_med)
    como arrays float64, con canal_ref = izquierdo, canal_med = derecho.
    """

    n_muestras = int(duracion_s* fs)
    grabacion_con_ruido = sd.rec(n_muestras, samplerate=fs, channels=2,
                        dtype="float64", device=dispositivo)
    sd.wait()

    grabacion=grabacion_con_ruido[int(fs * 0.25):] # recorto el primer milisegundo # 250 milis
    canal_ref = grabacion[:, 0]
    canal_med = grabacion[:, 1]

    return canal_ref, canal_med


# ==================== Filtro FIR + FFT + S11 ====================

def diseñar_filtro_pasabanda(fs, f_centro, ancho_banda, numtaps):
    n_muestras_captura = int(DURACION_CAPTURA_S * fs)
    if numtaps >= n_muestras_captura:
        raise ValueError(
            f"NUMTAPS_FILTRO ({numtaps}) debe ser menor que la cantidad de "
            f"muestras por captura ({n_muestras_captura}, con DURACION_CAPTURA_S="
            f"{DURACION_CAPTURA_S}s y FS_AUDIO={fs}Hz). Bajá NUMTAPS_FILTRO o "
            f"subí DURACION_CAPTURA_S."
        )

    f_baja = f_centro - ancho_banda / 2
    f_alta = f_centro + ancho_banda / 2
    return firwin(numtaps, [f_baja, f_alta], pass_zero=False, fs=fs, window="hamming")


def aplicar_filtro(señal, coeficientes):
    return lfilter(coeficientes, 1.0, señal)


def calcular_espectro_complejo(señal, fs, ventana):
    n = len(señal)
    w = get_window(ventana, n)
    fft_vals = np.fft.fft(señal * w)
    fft_freqs = np.fft.fftfreq(n, d=1 / fs)
    mitad = n // 2
    return fft_freqs[:mitad], fft_vals[:mitad]

def buscar_indice_pico(freqs, espectro, banda):
    """Devuelve el índice del bin de mayor magnitud dentro de la banda dada."""
    f_baja, f_alta = banda
    i0 = np.searchsorted(freqs, f_baja)
    i1 = np.searchsorted(freqs, f_alta)

    if i1 <= i0:
        raise ValueError("La banda de búsqueda no contiene ningún bin de frecuencia.")

    magnitud = np.abs(espectro[i0:i1])
    return i0 + np.argmax(magnitud)

"""def buscar_indice_frecuencia(freqs, frecuencia_objetivo):
   Devuelve el índice del bin de FFT más cercano a la frecuencia objetivo
    return np.argmin(np.abs(freqs - frecuencia_objetivo))"""


def medir_s11_punto(canal_ref, canal_med, fs, coef_filtro):
    """
    A partir de una captura de referencia y medición, devuelve un único
    valor complejo de S11 correspondiente al tono de batido.
    """
    ref_filtrada = aplicar_filtro(canal_ref, coef_filtro)
    med_filtrada = aplicar_filtro(canal_med, coef_filtro)

    freqs_ref, espectro_ref = calcular_espectro_complejo(ref_filtrada, fs, VENTANA_FFT)
    freqs_med, espectro_med = calcular_espectro_complejo(med_filtrada, fs, VENTANA_FFT)

    idx_pico = buscar_indice_pico(freqs_ref, espectro_ref, BANDA_BUSQUEDA_PICO)

    epsilon = np.max(np.abs(espectro_ref)) * 1e-9
    s11 = espectro_med[idx_pico] / (espectro_ref[idx_pico] + epsilon)

    return s11, freqs_ref[idx_pico]


# ==================== Barrido ====================

def barrido(ser,frecuencias_rf, coef_filtro):
    resultados_freq_rf = []
    resultados_modulo_db = []
    resultados_fase_rad = []  # sin desenrollar todavía
    
    for i, f_rf in enumerate(frecuencias_rf):
        if any(abs(f_rf - fx) < 1e-6 for fx in FRECUENCIAS_EXCLUIDAS_MHZ):
            print(f"[{i + 1}/{len(frecuencias_rf)}] {f_rf:.3f} MHz -- excluida, se saltea.")
            continue

        respuesta = setear_frecuencia(ser, f_rf)
    
        if respuesta.startswith("ERROR"):
            print(f"[{i + 1}/{len(frecuencias_rf)}] {respuesta} -- se aborta el barrido.")
            break
    
        canal_ref, canal_med = capturar_audio(DURACION_CAPTURA_S, FS_AUDIO, DISPOSITIVO_AUDIO)
    
        s11, f_batido = medir_s11_punto(canal_ref, canal_med, FS_AUDIO, coef_filtro)
    
        modulo_db = 20 * np.log10(np.abs(s11) + 1e-12)
        fase_rad = np.angle(s11)
    
        resultados_freq_rf.append(f_rf)
        resultados_modulo_db.append(modulo_db)
        resultados_fase_rad.append(fase_rad)
    
        print(f"[{i + 1}/{len(frecuencias_rf)}] RF={f_rf:.3f} MHz  "
                f"batido={f_batido:.1f} Hz  |S11|={modulo_db:.2f} dB  "
                f"fase={np.degrees(fase_rad):.1f}°")
    return np.array(resultados_freq_rf), np.array(resultados_modulo_db), np.array(resultados_fase_rad)


def guardar_csv(path, freq_rf, modulo_db, fase_deg):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["freq_rf_MHz", "modulo_S11_dB", "fase_S11_deg"])
        for f_rf, m, fa in zip(freq_rf, modulo_db, fase_deg):
            writer.writerow([f"{f_rf:.6f}", f"{m:.4f}", f"{fa:.4f}"])
    print(f"Resultados guardados en {path}")


def graficar_resultado(freq_rf, modulo_db, fase_deg):
    fig, axs = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    axs[0].plot(freq_rf, modulo_db, color="deeppink", linewidth=1, marker=".")
    axs[0].set_title("S11 - Módulo")
    axs[0].set_ylabel("|S11| (dB)")
    axs[0].grid(True, alpha=0.3)

    axs[1].plot(freq_rf, fase_deg, color="darkmagenta", linewidth=1, marker=".")
    axs[1].set_title("S11 - Fase")
    axs[1].set_xlabel("Frecuencia de RF (MHz)")
    axs[1].set_ylabel("Fase (grados)")
    axs[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

def main():
    frecuencias_rf = generar_frecuencias(F_INICIO_MHZ, F_FIN_MHZ, F_PASO_MHZ)
    print(f"Barrido: {len(frecuencias_rf)} pasos, de {F_INICIO_MHZ} a {F_FIN_MHZ} MHz "
          f"(paso {F_PASO_MHZ} MHz)")
    
    coef_filtro = diseñar_filtro_pasabanda(
        FS_AUDIO, F_CENTRO_FILTRO, ANCHO_BANDA_FILTRO, NUMTAPS_FILTRO
    )

    ser = conectar_arduino(PUERTO, BAUDRATE)
    resultados_freq_rf, resultados_modulo_db, resultados_fase_rad = barrido(ser, frecuencias_rf, coef_filtro)
    ser.close()

    fase_deg = np.degrees(resultados_fase_rad)
    # fase_deg = np.degrees(np.unwrap(resultados_fase_rad)) # Desenrollo la fase
    modulo_db = np.array(resultados_modulo_db)
    freq_rf = np.array(resultados_freq_rf)

    graficar_resultado(freq_rf, modulo_db, fase_deg)
    guardar_csv(ARCHIVO_CSV, freq_rf, modulo_db, fase_deg)


main()
