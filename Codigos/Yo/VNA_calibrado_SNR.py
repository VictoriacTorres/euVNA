"""
Barrido de RF + adquisición + cálculo de S11.

Por cada frecuencia del barrido:
    1. Se le manda la frecuencia al Arduino (adf4351_serial.ino) por serial.
    2. Se graba una captura corta desde la entrada line-in (ref = canal
       izquierdo, medición = canal derecho).
    3. Se filtra cada canal con un FIR pasabanda alrededor de 1 kHz.
    4. Se calcula la FFT compleja de ambos canales.
    5. Se busca el pico del tono de batido en el canal de referencia, y
       se toma el mismo bin en el canal de medición.
    6. S11_punto = medición[bin] / referencia[bin].

Al terminar se grafica y se guardan los resultados en un .csv.

Requisitos:
    pip install pyserial sounddevice numpy scipy matplotlib
"""

import csv
import time
import os
import pickle

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
F_PASO_MHZ = 5.000
FRECUENCIAS_EXCLUIDAS_MHZ = [200.00, 204.00, 208.00, 212.00, 216.00, 217.00, 221.00, 226.00, 256.00, 260.00, 280.00, 
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
                             2324.00, 2325.00, 2327.00, 2328.00, 2329.00, 2370.00, 2374.00, 2421.00, 2463.00]
# ==================== Configuración: adquisición de audio ====================

FS_AUDIO = 44100
DURACION_CAPTURA_S = 0.2

# Índice del dispositivo de audio a usar (line-in). None = dispositivo de
# entrada por defecto del sistema. Si tenés dudas de cuál es, corré:
#   python -c "import sounddevice as sd; print(sd.query_devices())"
# y poné acá el índice que corresponda a tu placa de sonido / line-in.
DISPOSITIVO_AUDIO = None

# ==================== Configuración: filtro FIR + FFT ====================

F_CENTRO_FILTRO = 1000       # Hz, tono de batido esperado
ANCHO_BANDA_FILTRO = 200     # Hz
NUMTAPS_FILTRO = 1001        # debe ser menor que la cantidad de muestras por captura

VENTANA_FFT = "flattop"

# Banda donde se busca el pico del tono de batido (Hz)
BANDA_BUSQUEDA_PICO = (F_CENTRO_FILTRO - ANCHO_BANDA_FILTRO / 2,
                        F_CENTRO_FILTRO + ANCHO_BANDA_FILTRO / 2)

# ==================== Salida ====================

ARCHIVO_CSV = f"s11_{F_INICIO_MHZ:.3f}_{F_FIN_MHZ:.3f}_{F_PASO_MHZ:.3f}.csv"
ARCHIVO_FIGURA = f"s11_{F_INICIO_MHZ:.3f}_{F_FIN_MHZ:.3f}_{F_PASO_MHZ:.3f}.pkl"

# ==================== Control de calidad: SNR ====================

# Umbral mínimo de SNR (dB) del tono de batido para considerar válido un
# punto de medición. Por debajo de esto, se descarta (se marca NaN en
# vez de saltearlo, para no desalinear los índices entre los barridos
# de calibración SOL y el del DUT).
UMBRAL_SNR_DB = 30

# Separación (Hz) alrededor del pico que se excluye al estimar el piso
# de ruido, para no confundir los lóbulos laterales de la ventana
# flattop con ruido real.
ANCHO_GUARDIA_SNR_HZ = 15

# ==================== Calibración ====================
def calculo_errores (GM_CC, GM_CA, GM_50, n):
    e_00=np.empty(n,dtype=complex)   #inicializo un vector de long n vacio con valores complejos
    e_11=np.empty(n,dtype=complex)
    delta_e=np.empty(n,dtype=complex)

    for i in range(n):
        # Si algún patrón de calibración tuvo SNR pobre en este punto
        # (marcado NaN en el barrido), no tiene sentido resolver el
        # sistema -- np.linalg.solve directamente explota con NaN en
        # vez de propagarlo. Lo dejamos NaN también acá.
        if np.isnan(GM_CC[i]) or np.isnan(GM_CA[i]) or np.isnan(GM_50[i]):
            e_00[i] = complex(np.nan, np.nan)
            e_11[i] = complex(np.nan, np.nan)
            delta_e[i] = complex(np.nan, np.nan)
            continue

        A=np.array([
            [1, -GM_CC[i], 1], #CC
            [1, 0, 0],         #50
            [1, GM_CA[i], -1]  #CA
        ],dtype=complex)
        B=np.array([GM_CC[i], GM_50[i], GM_CA[i]])
        sol=np.linalg.solve(A,B)
        e_00[i]=sol[0]
        e_11[i]=sol[1]
        delta_e[i]=sol[2] 
    return e_00, e_11, delta_e

def correccion(GM,e_00,e_11,delta_e,n):
    Gamma=np.empty(n,dtype=complex)
    for i in range(n):
        denominador = (GM[i]*e_11[i]-delta_e[i])
        if abs(denominador) < 1e-15:
            denominador = 1e-15 + 1e-15j
        Gamma[i]=(GM[i]-e_00[i])/denominador
    return Gamma

def guardar_calibracion_csv(path, freqs, e_00, e_11, delta_e):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["freq_MHz", "e_00_real", "e_00_imag", "e_11_real", "e_11_imag", "delta_e_real", "delta_e_imag"])
        for i in range(len(freqs)):
            writer.writerow([f"{freqs[i]:.6f}", 
                             f"{e_00[i].real:.10e}", f"{e_00[i].imag:.10e}",
                             f"{e_11[i].real:.10e}", f"{e_11[i].imag:.10e}",
                             f"{delta_e[i].real:.10e}", f"{delta_e[i].imag:.10e}"])
    print(f"Matriz de error guardada en {path}")

def cargar_calibracion_csv(path): #rearma los valores complejos
    freqs, e_00, e_11, delta_e = [], [], [], []
    with open(path, "r", encoding="utf-8") as f:
        reader=csv.DictReader(f)
        for row in reader:
            freqs.append(float(row["freq_MHz"]))
            e_00.append(complex(float(row["e_00_real"]), float(row["e_00_imag"])))
            e_11.append(complex(float(row["e_11_real"]), float(row["e_11_imag"])))
            delta_e.append(complex(float(row["delta_e_real"]), float(row["delta_e_imag"])))
    return np.array(freqs), np.array(e_00), np.array(e_11), np.array(delta_e)

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

    grabacion=grabacion_con_ruido[int(fs * 0.001):] # recorto el primer milisegundo
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


def calcular_snr_db(freqs, espectro, banda, idx_pico, ancho_guardia_hz=ANCHO_GUARDIA_SNR_HZ):
    """
    Estima el SNR (dB) del tono en idx_pico, comparando su magnitud
    contra el piso de ruido dentro de la misma banda de búsqueda
    (excluyendo una zona de guardia alrededor del pico, para no tomar
    los lóbulos laterales de la ventana como si fueran ruido).
    """
    f_baja, f_alta = banda
    i0 = np.searchsorted(freqs, f_baja)
    i1 = np.searchsorted(freqs, f_alta)

    magnitud_banda = np.abs(espectro[i0:i1])
    idx_pico_local = idx_pico - i0

    resolucion_hz = freqs[1] - freqs[0]
    guardia_bins = max(1, int(round(ancho_guardia_hz / resolucion_hz)))

    mascara = np.ones(len(magnitud_banda), dtype=bool)
    lo = max(0, idx_pico_local - guardia_bins)
    hi = min(len(magnitud_banda), idx_pico_local + guardia_bins + 1)
    mascara[lo:hi] = False

    if not np.any(mascara):
        # Banda demasiado angosta para estimar ruido de forma confiable;
        # no descartamos el punto por esto, dejamos pasar.
        return np.inf

    piso_ruido = np.median(magnitud_banda[mascara])
    pico = magnitud_banda[idx_pico_local]

    return 20 * np.log10(pico / (piso_ruido + 1e-15))


def medir_s11_punto(canal_ref, canal_med, fs, coef_filtro):
    """
    A partir de una captura de referencia y medición, devuelve un único
    valor complejo de S11 correspondiente al tono de batido, la
    frecuencia real donde se encontró ese pico, y el SNR (dB) más bajo
    entre referencia y medición (el "cuello de botella" de la medición).
    """
    ref_filtrada = aplicar_filtro(canal_ref, coef_filtro)
    med_filtrada = aplicar_filtro(canal_med, coef_filtro)

    freqs_ref, espectro_ref = calcular_espectro_complejo(ref_filtrada, fs, VENTANA_FFT)
    freqs_med, espectro_med = calcular_espectro_complejo(med_filtrada, fs, VENTANA_FFT)

    idx_pico = buscar_indice_pico(freqs_ref, espectro_ref, BANDA_BUSQUEDA_PICO)

    snr_ref_db = calcular_snr_db(freqs_ref, espectro_ref, BANDA_BUSQUEDA_PICO, idx_pico)
    snr_med_db = calcular_snr_db(freqs_med, espectro_med, BANDA_BUSQUEDA_PICO, idx_pico)
    snr_db = min(snr_ref_db, snr_med_db)

    epsilon = np.max(np.abs(espectro_ref)) * 1e-9
    s11 = espectro_med[idx_pico] / (espectro_ref[idx_pico] + epsilon)

    return s11, freqs_ref[idx_pico], snr_db


# ==================== Barrido ====================

def barrido(ser,frecuencias_rf, coef_filtro, nombre_medida=""):
    print(f"\n---> Iniciando adquisición: {nombre_medida}")
    resultados_freq_rf = []
    resultados_s11_complejo = []
    descartados_por_snr = 0

    for i, f_rf in enumerate(frecuencias_rf):
        if any(abs(f_rf - fx) < 1e-6 for fx in FRECUENCIAS_EXCLUIDAS_MHZ):
            print(f"[{i + 1}/{len(frecuencias_rf)}] {f_rf:.3f} MHz -- excluida, se saltea.")
            continue

        respuesta = setear_frecuencia(ser, f_rf)
    
        if respuesta.startswith("ERROR"):
            print(f"[{i + 1}/{len(frecuencias_rf)}] {respuesta} -- se aborta el barrido.")
            break
    
        canal_ref, canal_med = capturar_audio(DURACION_CAPTURA_S, FS_AUDIO, DISPOSITIVO_AUDIO)
    
        s11, f_batido, snr_db = medir_s11_punto(canal_ref, canal_med, FS_AUDIO, coef_filtro)

        modulo_db = 20 * np.log10(np.abs(s11) + 1e-12)
        fase_rad = np.angle(s11)

        if snr_db < UMBRAL_SNR_DB:
            # No lo salteamos con continue: lo dejamos como NaN para que
            # freq_rf mantenga la misma longitud/posición en todos los
            # barridos (calibración y DUT), y así calculo_errores /
            # correccion sigan alineados índice a índice.
            resultados_freq_rf.append(f_rf)
            resultados_s11_complejo.append(complex(np.nan, np.nan))
            descartados_por_snr += 1

            print(f"[{i + 1}/{len(frecuencias_rf)}] RF={f_rf:.3f} MHz  "
                  f"SNR={snr_db:.1f} dB < {UMBRAL_SNR_DB} dB -- DESCARTADO (NaN)")
            continue

        resultados_freq_rf.append(f_rf)
        resultados_s11_complejo.append(s11)

        #Mostrar resultados parciales en la consola
        print(f"[{i + 1}/{len(frecuencias_rf)}] RF={f_rf:.3f} MHz  "
                f"batido={f_batido:.1f} Hz  |S11|={modulo_db:.2f} dB  "
                f"fase={np.degrees(fase_rad):.1f}°  SNR={snr_db:.1f} dB")

    if descartados_por_snr:
        print(f"\n({nombre_medida}) {descartados_por_snr} punto(s) descartado(s) "
              f"por SNR < {UMBRAL_SNR_DB} dB.")

    return np.array(resultados_freq_rf), np.array(resultados_s11_complejo)


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

    # Guardamos la figura completa (no una imagen) ANTES de mostrarla,
    # que es el momento más confiable para que pickle la capture bien.
    try:
        with open(ARCHIVO_FIGURA, "wb") as f:
            pickle.dump(fig, f)
        print(f"Figura interactiva guardada en {ARCHIVO_FIGURA} "
              f"(reabrila con abrir_figura.py)")
    except Exception as e:
        print(f"AVISO: no se pudo guardar la figura con pickle ({e}). "
              f"El CSV con los datos crudos sigue disponible igual.")

    plt.show()

def main():
    frecuencias_rf = generar_frecuencias(F_INICIO_MHZ, F_FIN_MHZ, F_PASO_MHZ)
    print(f"Barrido: {len(frecuencias_rf)} pasos, de {F_INICIO_MHZ} a {F_FIN_MHZ} MHz "
          f"(paso {F_PASO_MHZ} MHz)")
    
    coef_filtro = diseñar_filtro_pasabanda(
        FS_AUDIO, F_CENTRO_FILTRO, ANCHO_BANDA_FILTRO, NUMTAPS_FILTRO
    )

    # Nombre dinámico del archivo de calibración
    archivo_calibracion = f"calibracion_{F_INICIO_MHZ}_{F_FIN_MHZ}_{F_PASO_MHZ}.csv"
    hacer_cal = True

    # 1. Comprobar si existe la matriz de calibración para este barrido
    if os.path.exists(archivo_calibracion):
        print(f"\nSe encontró un archivo de calibración coincidente: '{archivo_calibracion}'")
        rta = input("¿Deseas usar esta calibración previa (s) o realizar una nueva calibración SOL (n)? [s/n]: ")
        if rta.strip().lower() == 's':
            hacer_cal = False

            freqs_cal, e_00, e_11, delta_e = cargar_calibracion_csv(archivo_calibracion)
            print("Matriz de error cargada correctamente.")
    
    ser = conectar_arduino(PUERTO, BAUDRATE)

 # 3. Procedimiento de calibración SOL si corresponde
    if hacer_cal:
        print("\n===========================================")
        print("   INICIANDO CALIBRACIÓN S.O.L.")
        print("===========================================")
        
        input("Paso 1/3: Conecte la carga SHORT (Cortocircuito) y presione Enter para barrer...")
        freqs_cal, gm_cc = barrido(ser, frecuencias_rf, coef_filtro, "CALIBRACIÓN SHORT")
        
        input("\nPaso 2/3: Conecte la carga OPEN (Circuito Abierto) y presione Enter para barrer...")
        _, gm_ca = barrido(ser, frecuencias_rf, coef_filtro, "CALIBRACIÓN OPEN")
        
        input("\nPaso 3/3: Conecte la carga LOAD (50 Ohms) y presione Enter para barrer...")
        _, gm_50 = barrido(ser, frecuencias_rf, coef_filtro, "CALIBRACIÓN LOAD")
        
        # Calcular los términos de error con la función de álgebra lineal
        n_puntos = len(freqs_cal)
        e_00, e_11, delta_e = calculo_errores(gm_cc, gm_ca, gm_50, n_puntos)
        
        # Guardar en archivo .csv
        guardar_calibracion_csv(archivo_calibracion, freqs_cal, e_00, e_11, delta_e)

    # 4. Medición del Dispositivo Bajo Prueba (DUT)
    print("\n===========================================")
    print("   MEDICIÓN DEL DISPOSITIVO (DUT)")
    print("===========================================")
    input("Conecte el dispositivo a medir y presione Enter para iniciar el barrido final...")
    
    freqs_dut, gm_dut = barrido(ser, frecuencias_rf, coef_filtro, "MEDICIÓN DUT")
    
    ser.close()

     # Chequeo de consistencia (por si cambiaron las frecuencias excluidas entre runs)
    if len(freqs_dut) != len(e_00):
        print("\n¡ADVERTENCIA! El número de puntos no coincide con la calibración. Mal el rango de frecuencias")

     # 6. Aplicar la corrección SOL al DUT
    gamma_corregido = correccion(gm_dut, e_00, e_11, delta_e, len(gm_dut))
    

    fase_deg = np.degrees(np.angle(gamma_corregido))
    # fase_deg = np.degrees(np.unwrap(np.angle(resultados_s11_complejo))) # Desenrollo la fase
    modulo_db = 20 * np.log10(np.abs(gamma_corregido) + 1e-12)

    # Sacamos del resultado final los puntos que quedaron NaN (por SNR
    # pobre en el DUT, o heredado de algún patrón de calibración con
    # SNR pobre en esa misma frecuencia).
    validos = ~np.isnan(modulo_db)
    cantidad_descartados = np.sum(~validos)
    if cantidad_descartados:
        print(f"\n{cantidad_descartados} punto(s) del resultado final descartado(s) "
              f"por SNR < {UMBRAL_SNR_DB} dB (DUT o heredado de la calibración).")

    freqs_dut = freqs_dut[validos]
    modulo_db = modulo_db[validos]
    fase_deg = fase_deg[validos]

    guardar_csv(ARCHIVO_CSV, freqs_dut, modulo_db, fase_deg)
    graficar_resultado(freqs_dut, modulo_db, fase_deg)

main()
