"""
Calcula un barrido de frecuencias (inicio, fin, paso) y se lo manda,
paso a paso, al Arduino que tiene cargado adf4351_serial.ino. 
Requisitos:
    pip install pyserial
"""

import time
import serial

PUERTO = "COM3"          # Windows: "COM5", "COM7", etc.                          
BAUDRATE = 115200
F_INICIO_MHZ = 600.000
F_FIN_MHZ = 2000.000
F_PASO_MHZ = 10.00
TIEMPO_ASENTAMIENTO_S = 1.0 # Tiempo de espera en cada frecuencia antes de pasar a la siguiente
ESPERAR_ENTER = False # True, se detiene en cada paso y espera un Enter. False y corre solo.

def generar_frecuencias(inicio, fin, paso):
    n_pasos = round((fin - inicio) / paso)
    return [inicio + i * paso for i in range(n_pasos + 1)]

def main():
    frecuencias = generar_frecuencias(F_INICIO_MHZ, F_FIN_MHZ, F_PASO_MHZ)
    print(f"Barrido: {len(frecuencias)} pasos, de {F_INICIO_MHZ} a {F_FIN_MHZ} MHz "
          f"(paso {F_PASO_MHZ} MHz)")

    ser = serial.Serial(PUERTO, BAUDRATE, timeout=5)
    time.sleep(2)  # el Arduino se resetea al abrir el puerto serial; esperamos a que arranque
    ser.reset_input_buffer() # limpia el buffer

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
            input("Grabá con Audacity y presioná Enter para el siguiente paso...")

    ser.close()
    print("Barrido completo.")

"""if __name__ == "__main__":
    main() 
  se usa si quiero llamar a la función main() desde otro script """