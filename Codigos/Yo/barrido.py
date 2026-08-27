"""
Calcula un barrido de frecuencias (inicio, fin, paso) y se lo manda,
paso a paso, al Arduino que tiene cargado 780
800
91140
11460adf4351_serial.ino. El Arduino
hace todo el cálculo de registros; este script solo le indica a qué
frecuencia moverse en cada paso.

Requisitos:
    pip install pyserial
"""

import time
import serial


# ------------------- Configuración -------------------

PUERTO = "COM3"          # Windows: "COM5", "COM7", etc.
                          
BAUDRATE = 115200

F_INICIO_MHZ = 600.000
F_FIN_MHZ = 2000.000
F_PASO_MHZ = 10.00

# Tiempo de espera en cada frecuencia antes de pasar a la siguiente,
# para llegar a régimen permanente (2 s es un margen conservador de sobra
# para el PLL en sí; ajustalo si tenés algún filtro analógico muy angosto
# en el camino).
TIEMPO_ASENTAMIENTO_S = 1.0

# Si es True, el script se detiene en cada paso y espera que apretes
# Enter. Con analizador de espectros en vivo no hace falta: dejalo en
# False y el barrido corre solo.
ESPERAR_ENTER = False


def generar_frecuencias(inicio, fin, paso):
    """Genera la lista de frecuencias evitando arrastre de error de punto flotante."""
    n_pasos = round((fin - inicio) / paso)
    return [inicio + i * paso for i in range(n_pasos + 1)]


def main():
    frecuencias = generar_frecuencias(F_INICIO_MHZ, F_FIN_MHZ, F_PASO_MHZ)
    print(f"Barrido: {len(frecuencias)} pasos, de {F_INICIO_MHZ} a {F_FIN_MHZ} MHz "
          f"(paso {F_PASO_MHZ} MHz)")

    ser = serial.Serial(PUERTO, BAUDRATE, timeout=5)
    time.sleep(2)  # el Arduino se resetea al abrir el puerto serial; esperamos a que arranque
    ser.reset_input_buffer()

    # Esperamos el "READY" que manda el Arduino al terminar su setup()
    linea = ser.readline().decode(errors="ignore").strip()
    if linea:
        print(f"Arduino: {linea}")

    for i, f in enumerate(frecuencias):
        comando = f"{f:.6f}\n"
        ser.write(comando.encode())

        respuesta = ser.readline().decode(errors="ignore").strip()
        while respuesta and not respuesta.startswith("OK") and not respuesta.startswith("ERROR"):
            print("  (Arduino):", respuesta)
            respuesta = ser.readline().decode(errors="ignore").strip()

        if respuesta.startswith("ERROR"):
            print(f"[{i + 1}/{len(frecuencias)}] {respuesta} -- se aborta el barrido.")
            break

        print(f"[{i + 1}/{len(frecuencias)}] {respuesta}  (ADF2 = {f + 0.001:.6f} MHz)")

        time.sleep(TIEMPO_ASENTAMIENTO_S)

        if ESPERAR_ENTER:
            input("  Grabá con Audacity y presioná Enter para el siguiente paso...")

    ser.close()
    print("Barrido completo.")


if __name__ == "__main__":
    main()