"""
vna_core.py
============
Nucleo de adquisicion y calculo para el VNA casero (2x ADF4351 + Arduino +
placa de sonido). Adaptado de VNA_calibrado.py para poder ser llamado desde
una interfaz grafica: sin input()/tkinter bloqueantes, con callback de
progreso por punto y posibilidad de abortar un barrido en curso.

La logica de senales (filtro FIR, FFT, deteccion del tono de batido,
algebra de calibracion SOL) es la misma que la del script original; lo
unico que cambia es como se invoca.

Requisitos:
    pip install pyserial sounddevice numpy scipy
"""

import csv
import time

import numpy as np
import serial
import sounddevice as sd
from scipy.signal import firwin, lfilter
from scipy.signal.windows import get_window


# ==================== Lista por defecto de frecuencias excluidas ====================
# (copiada de VNA_calibrado.py; se puede editar/reemplazar desde la GUI)

FRECUENCIAS_EXCLUIDAS_MHZ_DEFAULT = [
    200.00, 204.00, 208.00, 212.00, 216.00, 217.00, 221.00, 226.00, 256.00, 260.00, 280.00,
    285.00, 291.00, 320.00, 347.00, 353.00, 354.00, 359.00, 360.00, 365.00, 366.00, 371.00,
    372.00, 378.00, 379.00, 385.00, 386.00, 392.00, 393.00, 400.00, 401.00, 408.00, 409.00,
    416.00, 417.00, 424.00, 425.00, 433.00, 434.00, 443.00, 452.00, 512.00, 559.00, 560.00,
    570.00, 571.00, 581.00, 582.00, 617.00, 640.00, 678.00, 694.00, 705.00, 706.00, 707.00,
    708.00, 717.00, 718.00, 719.00, 720.00, 730.00, 731.00, 732.00, 742.00, 743.00, 744.00,
    745.00, 756.00, 757.00, 758.00, 759.00, 770.00, 771.00, 772.00, 773.00, 784.00, 785.00,
    786.00, 787.00, 799.00, 800.00, 801.00, 802.00, 815.00, 816.00, 817.00, 818.00, 831.00,
    832.00, 833.00, 834.00, 848.00, 849.00, 850.00, 851.00, 865.00, 866.00, 867.00, 868.00,
    883.00, 886.00, 904.00, 927.00, 929.00, 955.00, 1009.00, 1024.00, 1075.00, 1118.00, 1119.00,
    1120.00, 1140.00, 1142.00, 1162.00, 1164.00, 1185.00, 1187.00, 1234.00, 1280.00, 1283.00,
    1304.00, 1333.00, 1356.00, 1383.00, 1388.00, 1410.00, 1411.00, 1412.00, 1413.00, 1414.00,
    1415.00, 1416.00, 1434.00, 1435.00, 1436.00, 1437.00, 1438.00, 1439.00, 1440.00, 1459.00,
    1460.00, 1461.00, 1462.00, 1463.00, 1464.00, 1465.00, 1484.00, 1485.00, 1486.00, 1487.00,
    1488.00, 1489.00, 1490.00, 1491.00, 1511.00, 1512.00, 1513.00, 1514.00, 1515.00, 1516.00,
    1517.00, 1518.00, 1539.00, 1540.00, 1541.00, 1542.00, 1543.00, 1544.00, 1545.00, 1546.00,
    1568.00, 1569.00, 1570.00, 1571.00, 1572.00, 1573.00, 1574.00, 1575.00, 1598.00, 1599.00,
    1600.00, 1601.00, 1602.00, 1603.00, 1604.00, 1605.00, 1629.00, 1630.00, 1631.00, 1632.00,
    1633.00, 1634.00, 1635.00, 1636.00, 1662.00, 1663.00, 1664.00, 1665.00, 1666.00, 1667.00,
    1668.00, 1669.00, 1696.00, 1697.00, 1698.00, 1700.00, 1701.00, 1702.00, 1730.00, 1731.00,
    1732.00, 1734.00, 1735.00, 1736.00, 1766.00, 1767.00, 1771.00, 1772.00, 1803.00, 1829.00,
    1833.00, 1854.00, 1858.00, 1910.00, 1937.00, 2018.00, 2150.00, 2235.00, 2236.00,
    2237.00, 2238.00, 2239.00, 2240.00, 2241.00, 2279.00, 2280.00, 2281.00, 2283.00, 2284.00,
    2324.00, 2325.00, 2327.00, 2328.00, 2329.00, 2370.00, 2374.00, 2421.00, 2463.00,
]


# ==================== Configuracion por defecto ====================

def config_por_defecto():
    """Devuelve un dict de configuracion editable desde la GUI."""
    return {
        "fs_audio": 44100,
        "duracion_captura_s": 0.6,
        "recorte_inicial_s": 0.150,
        "dispositivo_audio": None,
        "f_centro_filtro": 10000,      # Hz, tono de batido esperado
        "ancho_banda_filtro": 200,     # Hz
        "numtaps_filtro": 1001,
        "ventana_fft": "flattop",
        "frecuencias_excluidas": list(FRECUENCIAS_EXCLUIDAS_MHZ_DEFAULT),
    }


def banda_busqueda_pico(config):
    fc = config["f_centro_filtro"]
    bw = config["ancho_banda_filtro"]
    return (fc - bw / 2, fc + bw / 2)


# ==================== Arduino / serial ====================

class ErrorArduino(Exception):
    pass


def conectar_arduino(puerto, baudrate=115200, timeout=5):
    """Abre el puerto serie y devuelve (objeto_serial, primera_linea_recibida)."""
    ser = serial.Serial(puerto, baudrate, timeout=timeout)
    time.sleep(2)  # el Arduino se resetea al abrir el puerto; esperamos a que arranque
    ser.reset_input_buffer()
    linea = ser.readline().decode(errors="ignore").strip()
    return ser, linea


def setear_frecuencia(ser, f_mhz):
    """Manda la frecuencia al Arduino y espera la confirmacion (OK/ERROR)."""
    comando = f"{f_mhz:.6f}\n"
    ser.write(comando.encode())
    respuesta = ser.readline().decode(errors="ignore").strip()
    intentos_vacios = 0
    while respuesta and not respuesta.startswith("OK") and not respuesta.startswith("ERROR"):
        respuesta = ser.readline().decode(errors="ignore").strip()
        intentos_vacios += 1
        if intentos_vacios > 50:
            break
    return respuesta


def generar_frecuencias(inicio, fin, paso):
    """Genera la lista de frecuencias evitando arrastre de error de punto flotante."""
    if paso <= 0:
        raise ValueError("El paso de frecuencia debe ser mayor que 0.")
    n_pasos = round((fin - inicio) / paso)
    return [inicio + i * paso for i in range(n_pasos + 1)]


# ==================== Adquisicion de audio ====================

def capturar_audio(duracion_s, fs, dispositivo=None, recorte_inicial_s=0.150):
    """
    Graba desde la entrada configurada. Devuelve (canal_ref, canal_med) como
    arrays float64, con canal_ref = izquierdo, canal_med = derecho.
    """
    n_muestras = int(duracion_s * fs)
    grabacion_con_ruido = sd.rec(
        n_muestras, samplerate=fs, channels=2, dtype="float64", device=dispositivo
    )
    sd.wait()
    grabacion = grabacion_con_ruido[int(fs * recorte_inicial_s):]
    canal_ref = grabacion[:, 0]
    canal_med = grabacion[:, 1]
    return canal_ref, canal_med


# ==================== Filtro FIR + FFT + S11 ====================

def diseñar_filtro_pasabanda(fs, f_centro, ancho_banda, numtaps, duracion_captura_s):
    n_muestras_captura = int(duracion_captura_s * fs)
    if numtaps >= n_muestras_captura:
        raise ValueError(
            f"NUMTAPS_FILTRO ({numtaps}) debe ser menor que la cantidad de "
            f"muestras por captura ({n_muestras_captura}, con duracion_captura_s="
            f"{duracion_captura_s}s y fs={fs}Hz). Bajar numtaps o subir la duracion."
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
    """Devuelve el indice del bin de mayor magnitud dentro de la banda dada."""
    f_baja, f_alta = banda
    i0 = np.searchsorted(freqs, f_baja)
    i1 = np.searchsorted(freqs, f_alta)
    if i1 <= i0:
        raise ValueError("La banda de busqueda no contiene ningun bin de frecuencia.")
    magnitud = np.abs(espectro[i0:i1])
    return i0 + np.argmax(magnitud)


def medir_s11_punto(canal_ref, canal_med, fs, coef_filtro, ventana_fft, banda):
    """
    A partir de una captura de referencia y medicion, devuelve un unico
    valor complejo de S11 (sin corregir) correspondiente al tono de batido,
    y la frecuencia de batido detectada (Hz).
    """
    ref_filtrada = aplicar_filtro(canal_ref, coef_filtro)
    med_filtrada = aplicar_filtro(canal_med, coef_filtro)

    freqs_ref, espectro_ref = calcular_espectro_complejo(ref_filtrada, fs, ventana_fft)
    _, espectro_med = calcular_espectro_complejo(med_filtrada, fs, ventana_fft)

    idx_pico = buscar_indice_pico(freqs_ref, espectro_ref, banda)

    epsilon = np.max(np.abs(espectro_ref)) * 1e-9
    s11 = espectro_med[idx_pico] / (espectro_ref[idx_pico] + epsilon)

    return s11, freqs_ref[idx_pico]


# ==================== Barrido (con callback de progreso + aborto) ====================

class BarridoAbortado(Exception):
    """Se lanza cuando should_abort() devuelve True durante un barrido."""
    pass


def barrido(ser, frecuencias_rf, coef_filtro, config, on_point=None, should_abort=None):
    """
    Ejecuta un barrido completo de frecuencias, midiendo un punto de S11
    (sin corregir) por cada frecuencia.

    on_point(i, n, f_rf, s11, f_batido_hz): callback opcional, llamado
        despues de medir cada punto (i es 1-based).
    should_abort(): callable opcional; si devuelve True se aborta el
        barrido lanzando BarridoAbortado.

    Devuelve (freqs_medidas, s11_medidos) como arrays de numpy, salteando
    las frecuencias que esten en config["frecuencias_excluidas"].
    """
    resultados_freq_rf = []
    resultados_s11 = []
    excluidas = config.get("frecuencias_excluidas", [])
    banda = banda_busqueda_pico(config)

    for i, f_rf in enumerate(frecuencias_rf):
        if should_abort is not None and should_abort():
            raise BarridoAbortado()

        if any(abs(f_rf - fx) < 1e-6 for fx in excluidas):
            continue

        respuesta = setear_frecuencia(ser, f_rf)
        if respuesta.startswith("ERROR"):
            raise ErrorArduino(f"Arduino devolvio error en {f_rf:.3f} MHz: {respuesta}")

        canal_ref, canal_med = capturar_audio(
            config["duracion_captura_s"], config["fs_audio"], config.get("dispositivo_audio"),
            config.get("recorte_inicial_s", 0.150),
        )
        s11, f_batido = medir_s11_punto(
            canal_ref, canal_med, config["fs_audio"], coef_filtro,
            config["ventana_fft"], banda,
        )

        resultados_freq_rf.append(f_rf)
        resultados_s11.append(s11)

        if on_point is not None:
            on_point(i + 1, len(frecuencias_rf), f_rf, s11, f_batido)

    return np.array(resultados_freq_rf), np.array(resultados_s11)


# ==================== Calibracion SOL ====================

def calculo_errores(GM_CC, GM_CA, GM_50, n):
    """Resuelve, punto a punto, el sistema 3x3 de la calibracion SOL."""
    e_00 = np.empty(n, dtype=complex)
    e_11 = np.empty(n, dtype=complex)
    delta_e = np.empty(n, dtype=complex)

    for i in range(n):
        A = np.array([
            [1, -GM_CC[i], 1],  # CC (short)
            [1, 0, 0],          # 50 (load)
            [1, GM_CA[i], -1],  # CA (open)
        ], dtype=complex)
        B = np.array([GM_CC[i], GM_50[i], GM_CA[i]])
        sol = np.linalg.solve(A, B)
        e_00[i] = sol[0]
        e_11[i] = sol[1]
        delta_e[i] = sol[2]

    return e_00, e_11, delta_e


def correccion(GM, e_00, e_11, delta_e, n):
    """Aplica la correccion de error de la calibracion SOL a un array de GM medidos."""
    Gamma = np.empty(n, dtype=complex)
    for i in range(n):
        denominador = (GM[i] * e_11[i] - delta_e[i])
        if abs(denominador) < 1e-15:
            denominador = 1e-15 + 1e-15j
        Gamma[i] = (GM[i] - e_00[i]) / denominador
    return Gamma


def correccion_punto(gm, e_00_i, e_11_i, delta_e_i):
    """Version de correccion() para un unico punto (usada para graficar en vivo)."""
    denominador = gm * e_11_i - delta_e_i
    if abs(denominador) < 1e-15:
        denominador = 1e-15 + 1e-15j
    return (gm - e_00_i) / denominador


def guardar_calibracion_csv(path, freqs, e_00, e_11, delta_e):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["freq_MHz", "e_00_real", "e_00_imag", "e_11_real", "e_11_imag",
                          "delta_e_real", "delta_e_imag"])
        for i in range(len(freqs)):
            writer.writerow([
                f"{freqs[i]:.6f}",
                f"{e_00[i].real:.10e}", f"{e_00[i].imag:.10e}",
                f"{e_11[i].real:.10e}", f"{e_11[i].imag:.10e}",
                f"{delta_e[i].real:.10e}", f"{delta_e[i].imag:.10e}",
            ])


def cargar_calibracion_csv(path):
    """Rearma los valores complejos guardados por guardar_calibracion_csv()."""
    freqs, e_00, e_11, delta_e = [], [], [], []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            freqs.append(float(row["freq_MHz"]))
            e_00.append(complex(float(row["e_00_real"]), float(row["e_00_imag"])))
            e_11.append(complex(float(row["e_11_real"]), float(row["e_11_imag"])))
            delta_e.append(complex(float(row["delta_e_real"]), float(row["delta_e_imag"])))
    return np.array(freqs), np.array(e_00), np.array(e_11), np.array(delta_e)


def guardar_resultados_csv(path, freq_rf, modulo_db, fase_deg):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["freq_rf_MHz", "modulo_S11_dB", "fase_S11_deg"])
        for f_rf, m, fa in zip(freq_rf, modulo_db, fase_deg):
            writer.writerow([f"{f_rf:.6f}", f"{m:.4f}", f"{fa:.4f}"])


def modulo_fase(s11_array):
    """Convierte un array de S11 complejos a (modulo_dB, fase_grados)."""
    modulo_db = 20 * np.log10(np.abs(s11_array) + 1e-12)
    fase_deg = np.degrees(np.angle(s11_array))
    return modulo_db, fase_deg
