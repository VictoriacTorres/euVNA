"""
Victoria Torres, 27/8/2026.
Analizador de archivos WAV estereo mediante FFT.

Flujo general:
    1. Permite elegir un WAV estereo o dos WAV mono y normaliza sus muestras.
    2. Asigna los canales izquierdo y derecho como referencia y medicion.
    3. Aplica una ventana configurable, por defecto flattop, y calcula la FFT
       con correccion de ganancia coherente y amplitud unilateral.
    4. Limita el espectro al rango indicado, por defecto hasta 16 kHz.
    5. Detecta los picos principales y grafica ambos espectros en dB o escala
       lineal, etiquetando las frecuencias y amplitudes de los picos.

Requisitos:
    pip install numpy matplotlib scipy
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.signal import find_peaks
from scipy.signal.windows import get_window
import tkinter as tk
from tkinter import filedialog


FREC_MAX_PLOT = 16000  # límite del eje X en Hz


def elegir_archivos_wav():
    """
    Abre el explorador de archivos
    Devuelve una lista de paths.
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    paths = filedialog.askopenfilenames(
        title="Seleccioná 1 WAV estéreo, o 2 WAV mono (izquierdo y derecho)",
        filetypes=[("Archivos WAV", "*.wav"), ("Todos los archivos", "*.*")],
    )

    root.destroy()

    if not paths:
        raise SystemExit("No se seleccionó ningún archivo.")

    if len(paths) > 2:
        raise SystemExit(
            "Seleccionaste más de 2 archivos. Elegí 1 WAV estéreo o 2 WAV mono."
        )

    return list(paths)


def normalizar_audio(data):
    """Convierte a float [-1, 1] si el audio viene en formato entero."""
    if np.issubdtype(data.dtype, np.integer):
        max_val = np.iinfo(data.dtype).max
        return data.astype(np.float64) / max_val
    return data.astype(np.float64)


def cargar_canales(paths):
    """
    Carga izquierdo/derecho a partir de 1 archivo estéreo o 2 archivos mono.
    Devuelve (fs, canal_izq, canal_der).
    """
    if len(paths) == 1:
        fs, data = wavfile.read(paths[0])
        data = normalizar_audio(data)

        if data.ndim == 1:
            raise ValueError(
                "El WAV seleccionado es mono. Si separaste los canales en "
                "Audacity, seleccioná los DOS archivos (izquierdo y derecho) "
                "a la vez en el explorador (Ctrl/Cmd + click)."
            )

        canal_izq = data[:, 0]
        canal_der = data[:, 1]

    else:  # 2 archivos mono
        fs1, data1 = wavfile.read(paths[0])
        fs2, data2 = wavfile.read(paths[1])

        if fs1 != fs2:
            raise ValueError(
                f"Los dos archivos tienen distinta frecuencia de muestreo "
                f"({fs1} Hz vs {fs2} Hz). Deben ser del mismo audio."
            )

        data1 = normalizar_audio(data1)
        data2 = normalizar_audio(data2)

        # Si alguno no es mono, nos quedamos con su primer canal y avisamos
        if data1.ndim > 1:
            print(f"Aviso: '{paths[0]}' no es mono, se usa solo su canal 0.")
            data1 = data1[:, 0]
        if data2.ndim > 1:
            print(f"Aviso: '{paths[1]}' no es mono, se usa solo su canal 0.")
            data2 = data2[:, 0]

        canal_izq = data1  # primer archivo elegido -> Referencia
        canal_der = data2  # segundo archivo elegido -> Medición
        fs = fs1

    return fs, canal_izq, canal_der


def calcular_fft(señal, fs, ventana="flattop"):
    """
    Calcula la FFT de una señal y devuelve frecuencias y magnitud (solo parte positiva).

    ventana: nombre de la ventana a aplicar antes de la FFT (ver scipy.signal.windows).
             - "flattop": mejor precisión de AMPLITUD del pico (recomendada para medir
               el nivel de un tono, como el batido de 1 kHz entre los dos ADF4351).
               A cambio tiene peor resolución en frecuencia (lóbulo principal ancho).
             - "hann": buen compromiso general, mejor resolución que flattop pero con
               algo más de error de amplitud si el tono no cae justo en un bin.
             - "boxcar" o None: sin ventana (rectangular), máxima resolución pero
               con más leakage espectral.
    """
    n = len(señal)

    if ventana is None or ventana == "boxcar":
        w = np.ones(n)
    else:
        w = get_window(ventana, n)

    señal_ventaneada = señal * w

    fft_vals = np.fft.fft(señal_ventaneada)
    fft_freqs = np.fft.fftfreq(n, d=1 / fs)

    # Nos quedamos solo con la mitad positiva del espectro
    mitad = n // 2
    freqs_pos = fft_freqs[:mitad]

    # Ganancia coherente de la ventana: al multiplicar la señal por la ventana,
    # la amplitud efectiva se reduce en promedio por este factor. Lo compensamos
    # dividiendo por él, para que la magnitud siga representando la amplitud real
    # del tono (necesario para que las mediciones de nivel sean comparables).
    ganancia_coherente = np.sum(w) / n
    magnitud = np.abs(fft_vals[:mitad]) / (n * ganancia_coherente)

    # Compensamos la energía que "tiraríamos" de la mitad negativa:
    # cada componente real se reparte entre el bin + y el bin -,
    # así que duplicamos todo menos DC (índice 0).
    magnitud[1:mitad] *= 2

    return freqs_pos, magnitud


def detectar_picos(freqs, magnitud, n_picos=5, altura_min=None, distancia_min_hz=20):
    """
    Detecta los picos más relevantes del espectro (dentro del rango ya
    recortado en frecuencia que se le pase).
    """
    if len(freqs) == 0:
        return np.array([], dtype=int)

    if altura_min is None:
        altura_min = np.max(magnitud) * 0.02  # 2% del pico máximo, ajustable

    resolucion_hz = freqs[1] - freqs[0]
    distancia_min_bins = max(1, int(distancia_min_hz / resolucion_hz))

    indices, _ = find_peaks(magnitud, height=altura_min, distance=distancia_min_bins)
    indices_ordenados = indices[np.argsort(magnitud[indices])[::-1]][:n_picos]

    return indices_ordenados


def marcar_picos(ax, freqs, magnitud_plot, indices_picos):
    """Dibuja un marcador y una etiqueta (freq, amplitud) sobre cada pico."""
    for idx in indices_picos:
        f = freqs[idx]
        m = magnitud_plot[idx]
        ax.plot(f, m, "o", color="black", markersize=4)
        ax.annotate(
            f"{f:.0f} Hz\n{m:.2f}",
            xy=(f, m),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", alpha=0.8),
        )

#modificar True por False si quiero escala lineal

def graficar_fft(paths_wav, escala_db=True, n_picos=5, frec_max=FREC_MAX_PLOT, ventana="flattop"):
    fs, canal_izq, canal_der = cargar_canales(paths_wav)

    freqs_izq, mag_izq = calcular_fft(canal_izq, fs, ventana=ventana)
    freqs_der, mag_der = calcular_fft(canal_der, fs, ventana=ventana)

    # Recortamos al rango de interés (0 a frec_max) antes de graficar y buscar picos
    idx_max_izq = np.searchsorted(freqs_izq, frec_max)
    idx_max_der = np.searchsorted(freqs_der, frec_max)
    freqs_izq, mag_izq = freqs_izq[:idx_max_izq], mag_izq[:idx_max_izq]
    freqs_der, mag_der = freqs_der[:idx_max_der], mag_der[:idx_max_der]

    if escala_db:
        mag_izq_plot = 20 * np.log10(mag_izq + 1e-12)
        mag_der_plot = 20 * np.log10(mag_der + 1e-12)
        ylabel = "Magnitud (dB)"
    else:
        mag_izq_plot = mag_izq
        mag_der_plot = mag_der
        ylabel = "Magnitud"

    picos_izq = detectar_picos(freqs_izq, mag_izq, n_picos=n_picos)
    picos_der = detectar_picos(freqs_der, mag_der, n_picos=n_picos)

    fig, axs = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    axs[0].plot(freqs_izq, mag_izq_plot, color="steelblue", linewidth=0.8)
    axs[0].set_title("FFT - Referencia (canal izquierdo)")
    axs[0].set_ylabel(ylabel)
    axs[0].set_xlim(0, frec_max)
    axs[0].grid(True, alpha=0.3)
    marcar_picos(axs[0], freqs_izq, mag_izq_plot, picos_izq)

    axs[1].plot(freqs_der, mag_der_plot, color="indianred", linewidth=0.8)
    axs[1].set_title("FFT - Medición (canal derecho)")
    axs[1].set_xlabel("Frecuencia (Hz)")
    axs[1].set_ylabel(ylabel)
    axs[1].set_xlim(0, frec_max)
    axs[1].grid(True, alpha=0.3)
    marcar_picos(axs[1], freqs_der, mag_der_plot, picos_der)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    paths = elegir_archivos_wav()
    graficar_fft(paths, escala_db=True, n_picos=5, frec_max=FREC_MAX_PLOT, ventana="flattop")