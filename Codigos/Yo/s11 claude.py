"""
Victoria Torres, 27/8/2026.
Calcula S11 a partir de un archivo WAV estereo.

Flujo general:
        1. Selecciona un WAV estereo con referencia en el canal izquierdo y
             medicion en el derecho, y normaliza sus muestras.
        2. Aplica a ambos canales el mismo filtro FIR pasabanda alrededor del
             tono de batido y calcula sus FFT complejas.
        3. Busca el pico de la fundamental en la referencia y usa el mismo bin
             para la medicion.
        4. Calcula S11 mediante cociente de amplitudes y diferencia de fases.
        5. Grafica las señales filtradas y los espectros, marcando la fundamental.

Requisitos:
        pip install numpy matplotlib scipy
"""

import numpy as np
import matplotlib.pyplot as plt
import pickle
from scipy.io import wavfile
from scipy.signal import firwin, lfilter
from scipy.signal.windows import get_window
import tkinter as tk
from tkinter import filedialog


FREC_MAX_PLOT = 16000  # límite del eje X en Hz, solo para el gráfico de verificación
ARCHIVO_FIGURA_TIEMPO = "s11_claude_senales.pkl"
ARCHIVO_FIGURA_S11 = "s11_claude_espectros.pkl"


def elegir_archivos_wav():
    """
    Abre el explorador de archivos permitiendo elegir 1 archivo estéreo.
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    paths = filedialog.askopenfilenames(
        title="Seleccioná 1 WAV estéreo",
        filetypes=[("Archivos WAV", "*.wav"), ("Todos los archivos", "*.*")],
    )

    root.destroy()

    if not paths:
        raise SystemExit("No se seleccionó ningún archivo.")

    if len(paths) > 1:
        raise SystemExit("Seleccionaste más de 1 archivo.")

    return list(paths)


def normalizar_audio(data):
    """Convierte a float [-1, 1] si el audio viene en formato entero."""
    if np.issubdtype(data.dtype, np.integer):
        max_val = np.iinfo(data.dtype).max
        return data.astype(np.float64) / max_val
    return data.astype(np.float64)


def cargar_canales(paths):
    """
    Carga izquierdo (referencia) / derecho (medición) a partir de 1 archivo
    estéreo. Devuelve (fs, canal_ref, canal_med).
    """
    fs, data = wavfile.read(paths[0])
    data = normalizar_audio(data)

    if data.ndim == 1:
        raise ValueError(
            "El WAV seleccionado es mono. Necesitás un WAV estéreo con "
            "referencia en el canal izquierdo y medición en el derecho."
        )

    canal_ref = data[:, 0]
    canal_med = data[:, 1]

    return fs, canal_ref, canal_med


def diseñar_filtro_pasabanda(fs, f_centro=1000, ancho_banda=200, numtaps=1001):
    """
    Diseña un filtro FIR pasabanda (ventana Hamming) centrado en f_centro,
    pensado para aislar el tono de batido antes de calcular S11.
    """
    f_baja = f_centro - ancho_banda / 2
    f_alta = f_centro + ancho_banda / 2

    if f_baja <= 0:
        raise ValueError(
            f"La banda pasante ({f_baja:.1f}-{f_alta:.1f} Hz) incluye o "
            "cruza 0 Hz. Reducí ancho_banda o aumentá f_centro."
        )

    return firwin(numtaps, [f_baja, f_alta], pass_zero=False, fs=fs, window="hamming")


def aplicar_filtro(señal, coeficientes):
    """Aplica el filtro FIR (convolución) a la señal."""
    return lfilter(coeficientes, 1.0, señal)


def calcular_espectro_complejo(señal, fs, ventana="flattop"):
    """
    Calcula la FFT compleja (sin tomar módulo) de una señal, aplicando la
    ventana indicada. No hace falta corregir por ganancia coherente: al
    dividir dos espectros calculados de la misma forma (mismo N, misma
    ventana), ese factor se cancela solo en el cociente S11.
    """
    n = len(señal)

    if ventana is None or ventana == "boxcar":
        w = np.ones(n)
    else:
        w = get_window(ventana, n)

    fft_vals = np.fft.fft(señal * w)
    fft_freqs = np.fft.fftfreq(n, d=1 / fs)

    mitad = n // 2
    return fft_freqs[:mitad], fft_vals[:mitad]


def encontrar_pico_fundamental(freqs, espectro, f_centro, ancho_busqueda=None):
    """
    Busca el bin de mayor magnitud dentro de una ventana alrededor de
    f_centro. Se usa para ubicar la fundamental (tono de batido) en el
    espectro ya filtrado, sin depender de que caiga exactamente en f_centro.

    ancho_busqueda: ancho total (Hz) de la ventana de búsqueda. Si es None,
    se busca en todo el espectro (no recomendado si hay otras señales fuertes
    fuera de la banda de interés).
    """
    if ancho_busqueda is not None:
        f_baja = f_centro - ancho_busqueda / 2
        f_alta = f_centro + ancho_busqueda / 2
        i0 = np.searchsorted(freqs, f_baja)
        i1 = np.searchsorted(freqs, f_alta)
    else:
        i0, i1 = 0, len(freqs)

    if i1 <= i0:
        raise ValueError(
            "Ventana de búsqueda de la fundamental vacía; revisá f_centro/ancho_busqueda."
        )

    sub_mag = np.abs(espectro[i0:i1])
    idx = i0 + int(np.argmax(sub_mag))
    return idx


def s_parameter(amp, phase_deg):
    """Reconstruye un fasor complejo a partir de amplitud y fase (en grados)."""
    return amp * np.exp(1j * np.radians(phase_deg))


def db_phase(sp):
    """Descompone un fasor complejo en magnitud lineal, magnitud en dB y fase en grados."""
    magnitude = np.abs(sp)
    magnitude_dB = 20.0 * np.log10(magnitude + 1e-12)
    phase_deg = np.angle(sp, deg=True)
    return magnitude, magnitude_dB, phase_deg


def calcular_s11_fundamental(freqs_ref, espectro_ref, freqs_med, espectro_med, f_centro, ancho_busqueda=None):
    """
    Calcula S11 = medición / referencia usando SOLO el bin de la fundamental
    (en vez de todo el espectro bin a bin).

    Ubica la fundamental buscando el pico de magnitud en el espectro de
    REFERENCIA dentro de una ventana alrededor de f_centro, y usa ese mismo
    índice de bin en el espectro de medición (así se comparan exactamente
    la misma frecuencia en ambos canales).

    Trabaja explícitamente en amplitud/fase por canal (en vez de dividir
    los complejos directamente): esto es matemáticamente equivalente,
    pero deja ver por separado amp_ref/fase_ref y amp_med/fase_med, útil
    para debuggear.

    Devuelve: f_fundamental (Hz), módulo S11 (dB), fase S11 (grados).
    """
    if len(freqs_ref) != len(freqs_med) or not np.allclose(freqs_ref, freqs_med):
        raise ValueError(
            "Los ejes de frecuencia de referencia y medición no coinciden. "
            "Verificá que ambas señales tengan la misma longitud y fs."
        )

    idx = encontrar_pico_fundamental(freqs_ref, espectro_ref, f_centro, ancho_busqueda)
    f_fundamental = freqs_ref[idx]

    # Amplitud y fase de cada canal en el bin de la fundamental
    amp_ref, _, fase_ref = db_phase(espectro_ref[idx])
    amp_med, _, fase_med = db_phase(espectro_med[idx])

    # S11 = (amp_med/amp_ref) * exp(j*(fase_med - fase_ref))
    s11 = s_parameter(amp_med / amp_ref, fase_med - fase_ref)
    _, modulo_db, fase_deg = db_phase(s11)

    return f_fundamental, modulo_db, fase_deg

def graficar_señales (
    canal_ref,
    canal_med,
    fs,
    num_muestras=1000,
    archivo_wav=""
):
    """
    Grafica las señales de referencia y medición en el dominio del tiempo.
    """
    t = np.arange(num_muestras) / fs
    plt.figure(figsize=(10, 5))
    plt.plot(t, canal_ref[:num_muestras], label='Referencia', color='steelblue')
    plt.plot(t, canal_med[:num_muestras], label='Medición', color='indianred')
    plt.title(f'Señales de Referencia y Medición, \n{archivo_wav}')
    plt.xlabel('Tiempo (s)')
    plt.ylabel('Amplitud')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    fig = plt.gcf()
    with open(ARCHIVO_FIGURA_TIEMPO, "wb") as f:
        pickle.dump(fig, f)
    print(f"Figura guardada en {ARCHIVO_FIGURA_TIEMPO}")
    # plt.pause(0.1)  # Forma original de mostrar sin bloquear

def graficar_s11(
    paths_wav,
    frec_max=FREC_MAX_PLOT,
    ventana="flattop",
    f_centro_filtro=1000,
    ancho_banda_filtro=200,
    numtaps_filtro=1001,
):
    fs, canal_ref, canal_med = cargar_canales(paths_wav)

    n_min = min(len(canal_ref), len(canal_med))
    canal_ref = canal_ref[:n_min]
    canal_med = canal_med[:n_min]

    if numtaps_filtro >= n_min:
        raise ValueError(
            f"numtaps_filtro ({numtaps_filtro}) debe ser menor que la "
            f"cantidad de muestras de la señal ({n_min})."
        )

    # Filtro FIR pasabanda: aísla el tono de batido antes de la FFT. Se
    # aplica el MISMO filtro a ambos canales, así que su respuesta se
    # cancela en el cociente S11 dentro de la banda pasante.
    coef_filtro = diseñar_filtro_pasabanda(
        fs, f_centro=f_centro_filtro, ancho_banda=ancho_banda_filtro, numtaps=numtaps_filtro
    )
    canal_ref = aplicar_filtro(canal_ref, coef_filtro)
    canal_med = aplicar_filtro(canal_med, coef_filtro)

    # Graficar las señales después de filtrar
    graficar_señales(canal_ref, canal_med, fs, num_muestras=1000, archivo_wav=paths_wav[0])
    freqs_ref, espectro_ref = calcular_espectro_complejo(canal_ref, fs, ventana=ventana)
    freqs_med, espectro_med = calcular_espectro_complejo(canal_med, fs, ventana=ventana)

    f_fundamental, modulo_db, fase_deg = calcular_s11_fundamental(
        freqs_ref, espectro_ref, freqs_med, espectro_med,
        f_centro=f_centro_filtro, ancho_busqueda=ancho_banda_filtro,
    )

    print(f"Fundamental detectada en {f_fundamental:.2f} Hz")
    print(f"S11 -> módulo: {modulo_db:.3f} dB | fase: {fase_deg:.3f}°")

    # Gráfico de verificación: magnitud de ambos espectros, marcando dónde
    # se tomó la fundamental usada para calcular S11.
    idx_max = np.searchsorted(freqs_ref, frec_max)
    freqs_plot = freqs_ref[:idx_max]
    mag_ref_db = 20 * np.log10(np.abs(espectro_ref[:idx_max]) + 1e-12)
    mag_med_db = 20 * np.log10(np.abs(espectro_med[:idx_max]) + 1e-12)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(freqs_plot, mag_ref_db, color="steelblue", linewidth=0.8, label="Referencia")
    ax.plot(freqs_plot, mag_med_db, color="indianred", linewidth=0.8, label="Medición")
    ax.axvline(f_fundamental, color="black", linestyle="--", linewidth=0.8,
               label=f"Fundamental ({f_fundamental:.1f} Hz)")
    ax.set_title(f"S11 en la fundamental: {modulo_db:.2f} dB, {fase_deg:.2f}°")
    ax.set_xlabel("Frecuencia (Hz)")
    ax.set_ylabel("Magnitud (dB)")
    ax.set_xlim(0, frec_max)
    ax.grid(True, alpha=0.3)
    ax.legend()

    plt.tight_layout()
    with open(ARCHIVO_FIGURA_S11, "wb") as f:
        pickle.dump(fig, f)
    print(f"Figura guardada en {ARCHIVO_FIGURA_S11}")
    # plt.pause(0.1)  # Forma original de mostrar sin bloquear

    return f_fundamental, modulo_db, fase_deg

# MAIN

if __name__ == "__main__":
    paths = elegir_archivos_wav()
    graficar_s11(
        paths,
        frec_max=FREC_MAX_PLOT,
        ventana="flattop",
        f_centro_filtro=1000,
        ancho_banda_filtro=200,
        numtaps_filtro=1001,
    )
    plt.show()
