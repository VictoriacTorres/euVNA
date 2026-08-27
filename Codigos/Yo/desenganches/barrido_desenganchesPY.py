import time
import serial
import csv

# ------------------- Configuración -------------------

PUERTO = "COM3"          # Cambiar según corresponda en tu PC
BAUDRATE = 115200

F_INICIO_MHZ = 200.000
F_FIN_MHZ = 2500.000
F_PASO_MHZ = 1.00

TIEMPO_ASENTAMIENTO_S = 1.0
ESPERAR_ENTER = False
NOMBRE_CSV = "frecuencias_desenganchadas_ADFizquierdo.csv"

def generar_frecuencias(inicio, fin, paso):
    n_pasos = round((fin - inicio) / paso)
    return [inicio + i * paso for i in range(n_pasos + 1)]

def main():
    frecuencias = generar_frecuencias(F_INICIO_MHZ, F_FIN_MHZ, F_PASO_MHZ)
    print(f"Barrido: {len(frecuencias)} pasos, de {F_INICIO_MHZ} a {F_FIN_MHZ} MHz (paso {F_PASO_MHZ} MHz)")

    try:
        ser = serial.Serial(PUERTO, BAUDRATE, timeout=5)
    except Exception as e:
        print(f"Error al abrir el puerto {PUERTO}: {e}")
        return

    time.sleep(2)  # Espera a que el Arduino se reinicie al abrir la conexión
    ser.reset_input_buffer()

    linea = ser.readline().decode(errors="ignore").strip()
    if linea:
        print(f"Arduino: {linea}")

    # Abrimos el archivo CSV en modo escritura ('w')
    with open(NOMBRE_CSV, mode='w', newline='') as archivo_csv:
        writer = csv.writer(archivo_csv)
        writer.writerow(["Frecuencia (MHz)", "Estado"]) # Encabezado del CSV

        for i, f in enumerate(frecuencias):
            comando = f"{f:.6f}\n"
            ser.write(comando.encode())

            # Leer la primera respuesta (esperamos el "OK ...")
            respuesta = ser.readline().decode(errors="ignore").strip()
            while respuesta and not respuesta.startswith("OK") and not respuesta.startswith("ERROR"):
                respuesta = ser.readline().decode(errors="ignore").strip()

            if respuesta.startswith("ERROR"):
                print(f"[{i + 1}/{len(frecuencias)}] {respuesta} -- se aborta el barrido.")
                break
            
            # Mostramos el OK
            print(f"[{i + 1}/{len(frecuencias)}] {respuesta}")

            # IMPORTANTE: Como tu Arduino tiene un delay(20) y luego envía "Unlocked"
            # si falla, debemos esperar un momento y leer si llegó ese mensaje.
            time.sleep(0.05) 
            
            desenganchado = False
            while ser.in_waiting > 0:
                extra_line = ser.readline().decode(errors="ignore").strip()
                if "Unlocked" in extra_line:
                    desenganchado = True

            # Si el Arduino reportó que se desenganchó, lo guardamos en el CSV
            if desenganchado:
                print(f"   >>> ALERTA: Desenganchado en {f:.6f} MHz (Guardado en CSV)")
                writer.writerow([f"{f:.6f}", "Unlocked"])
                archivo_csv.flush() # Forzamos a que se guarde en el disco enseguida

            time.sleep(TIEMPO_ASENTAMIENTO_S)

            if ESPERAR_ENTER:
                input("  Presioná Enter para el siguiente paso...")

    ser.close()
    print(f"\nBarrido completo. Revisá el archivo '{NOMBRE_CSV}'.")

if __name__ == "__main__":
    main()
