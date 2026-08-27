"""
Barrido de RF + adquisición.

Por cada frecuencia del barrido:
    1. Se le manda la frecuencia al Arduino por serial.
    2. Se graba una captura corta desde la entrada line-in.
    3. Se calcula la FFT compleja de ambos canales sin filtrar.
    5. Se busca el pico del tono de batido en ambos canales de forma independiente.
    6. Se calcula el módulo en dB de cada canal.

    Al terminar el barrido, se grafica el módulo sin filtrar de cada canal (Referencia y Medido) 
en función de la frecuencia de RF.

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

F_INICIO_MHZ = 1650.000
F_FIN_MHZ = 1670.000
F_PASO_MHZ = 0.100
FRECUENCIAS_EXCLUIDAS_MHZ = [] #400.00,  550.0, 560.0, 800.0, 1700.0, 1100.0, 1600.0, 1240.0, 720.0, 1540.0, 1570.0, 550.0, 850.0]

ARCHIVO_CSV = f"s11_{F_INICIO_MHZ:.3f}_{F_FIN_MHZ:.3f}_{F_PASO_MHZ:.3f}_sinfiltrar.csv"

# ==================== Configuración: adquisición de audio ====================

FS_AUDIO = 44100
DURACION_CAPTURA_S = 0.3

DISPOSITIVO_AUDIO = None

# ==================== Configuración: filtro FIR + FFT ====================

F_CENTRO_FILTRO = 1000       # Hz, tono de batido esperado
ANCHO_BANDA_FILTRO = 200     # Hz
NUMTAPS_FILTRO = 1001        # debe ser menor que la cantidad de muestras por captura

VENTANA_FFT = "flattop"

BANDA_BUSQUEDA_PICO = (F_CENTRO_FILTRO - ANCHO_BANDA_FILTRO / 2,
                        F_CENTRO_FILTRO + ANCHO_BANDA_FILTRO / 2)

# ==================== Arduino / serial ====================

def generar_frecuencias(inicio, fin, paso):
    n_pasos = round((fin - inicio) / paso)
    return [inicio + i * paso for i in range(n_pasos + 1)]


def conectar_arduino(puerto, baudrate):
    ser = serial.Serial(puerto, baudrate, timeout=5)
    time.sleep(2)
    ser.reset_input_buffer()

    linea = ser.readline().decode(errors="ignore").strip()
    if linea:
        print(f"Arduino: {linea}")

    return ser


def setear_frecuencia(ser, f_mhz):
    comando = f"{f_mhz:.6f}\n"
    ser.write(comando.encode())

    respuesta = ser.readline().decode(errors="ignore").strip()
    while respuesta and not respuesta.startswith("OK") and not respuesta.startswith("ERROR"):
        print("  (Arduino):", respuesta)
        respuesta = ser.readline().decode(errors="ignore").strip()

    return respuesta


# ==================== Adquisición ====================

def capturar_audio(duracion_s, fs, dispositivo=None):
    n_muestras = int(duracion_s* fs)
    grabacion_con_ruido = sd.rec(n_muestras, samplerate=fs, channels=2,
                        dtype="float64", device=dispositivo)
    sd.wait()

    grabacion=grabacion_con_ruido[int(fs * 0.001):]
    canal_ref = grabacion[:, 0]
    canal_med = grabacion[:, 1]

    return canal_ref, canal_med


# ==================== Filtro FIR + FFT ====================

def diseñar_filtro_pasabanda(fs, f_centro, ancho_banda, numtaps):
    n_muestras_captura = int(DURACION_CAPTURA_S * fs)
    if numtaps >= n_muestras_captura:
        raise ValueError(
            f"NUMTAPS_FILTRO ({numtaps}) debe ser menor que la cantidad de "
            f"muestras por captura ({n_muestras_captura})."
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
    f_baja, f_alta = banda
    i0 = np.searchsorted(freqs, f_baja)
    i1 = np.searchsorted(freqs, f_alta)

    if i1 <= i0:
        raise ValueError("La banda de búsqueda no contiene ningún bin de frecuencia.")

    magnitud = np.abs(espectro[i0:i1])
    return i0 + np.argmax(magnitud)


def medir_canales_punto(canal_ref, canal_med, fs, coef_filtro):
    # Calcular el espectro directamente sobre las señales sin filtrar.
    freqs_ref, espectro_ref = calcular_espectro_complejo(canal_ref, fs, VENTANA_FFT)
    freqs_med, espectro_med = calcular_espectro_complejo(canal_med, fs, VENTANA_FFT)

    # Buscar índices de los picos
    idx_pico_ref = buscar_indice_pico(freqs_ref, espectro_ref, BANDA_BUSQUEDA_PICO)
    idx_pico_med = buscar_indice_pico(freqs_med, espectro_med, BANDA_BUSQUEDA_PICO)

    # Calcular módulos en dB
    mod_ref_db = 20 * np.log10(np.abs(espectro_ref[idx_pico_ref]) + 1e-12)
    mod_med_db = 20 * np.log10(np.abs(espectro_med[idx_pico_med]) + 1e-12)

    return mod_ref_db, mod_med_db, freqs_ref[idx_pico_ref], freqs_med[idx_pico_med]


# ==================== Barrido ====================

def barrido(ser, frecuencias_rf, coef_filtro):
    resultados_freq_rf = []
    resultados_mod_ref = []
    resultados_mod_med = []
    resultados_f_pico_ref = []
    resultados_f_pico_med = []
    
    for i, f_rf in enumerate(frecuencias_rf):
        if any(abs(f_rf - fx) < 1e-6 for fx in FRECUENCIAS_EXCLUIDAS_MHZ):
            print(f"[{i + 1}/{len(frecuencias_rf)}] {f_rf:.3f} MHz -- excluida, se saltea.")
            continue

        respuesta = setear_frecuencia(ser, f_rf)
    
        if respuesta.startswith("ERROR"):
            print(f"[{i + 1}/{len(frecuencias_rf)}] {respuesta} -- se aborta el barrido.")
            break
    
        canal_ref, canal_med = capturar_audio(DURACION_CAPTURA_S, FS_AUDIO, DISPOSITIVO_AUDIO)
    
        mod_ref_db, mod_med_db, f_pico_ref, f_pico_med = medir_canales_punto(canal_ref, canal_med, FS_AUDIO, coef_filtro)
    
        resultados_freq_rf.append(f_rf)
        resultados_mod_ref.append(mod_ref_db)
        resultados_mod_med.append(mod_med_db)
        resultados_f_pico_ref.append(f_pico_ref)
        resultados_f_pico_med.append(f_pico_med)
    
        print(f"[{i + 1}/{len(frecuencias_rf)}] RF={f_rf:.3f} MHz | "
              f"Ref: {f_pico_ref:.1f} Hz ({mod_ref_db:.2f} dB) | "
              f"Medido: {f_pico_med:.1f} Hz ({mod_med_db:.2f} dB)")

    return (np.array(resultados_freq_rf), np.array(resultados_mod_ref),
            np.array(resultados_mod_med), np.array(resultados_f_pico_ref),
            np.array(resultados_f_pico_med))


def graficar_resultado(freq_x, mod_ref_db, mod_med_db):
    plt.figure(figsize=(10, 6))

    plt.plot(freq_x, mod_ref_db, color="blue", linewidth=1.5, marker=".", label="Referencia")
    plt.plot(freq_x, mod_med_db, color="red", linewidth=1.5, marker=".", label="Medido")

    plt.title("Módulo de las señales adquiridas (Sin filtrar)")
    plt.xlabel("Frecuencia de RF (MHz)")
    plt.ylabel("Módulo (dB)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

def guardar_csv(path, frecuencias_rf, f_pico_ref, mod_ref_db, f_pico_med, mod_med_db):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "paso", "freq_rf_MHz", "freq_audio_ref_Hz", "modulo_ref_dB",
            "freq_audio_medido_Hz", "modulo_medido_dB"
        ])
        for i in range(len(frecuencias_rf)):
            writer.writerow([
                i + 1,
                f"{frecuencias_rf[i]:.3f}",
                f"{f_pico_ref[i]:.1f}",
                f"{mod_ref_db[i]:.2f}",
                f"{f_pico_med[i]:.1f}",
                f"{mod_med_db[i]:.2f}",
            ])
    print(f"Resultados guardados en {path}")

def main():
    frecuencias_rf = generar_frecuencias(F_INICIO_MHZ, F_FIN_MHZ, F_PASO_MHZ)
    print(f"Barrido: {len(frecuencias_rf)} pasos, de {F_INICIO_MHZ} a {F_FIN_MHZ} MHz "
          f"(paso {F_PASO_MHZ} MHz)")
    
    coef_filtro = diseñar_filtro_pasabanda(
        FS_AUDIO, F_CENTRO_FILTRO, ANCHO_BANDA_FILTRO, NUMTAPS_FILTRO
    )

    ser = conectar_arduino(PUERTO, BAUDRATE)
    
    freq_rf, mod_ref_db, mod_med_db, f_pico_ref, f_pico_med = barrido(ser, frecuencias_rf, coef_filtro)
    ser.close()
    guardar_csv(ARCHIVO_CSV, freq_rf, f_pico_ref, mod_ref_db, f_pico_med, mod_med_db)
    graficar_resultado(freq_rf, mod_ref_db, mod_med_db)

if __name__ == "__main__":
    main()