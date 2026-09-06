# VNA casero - GUI (PyQt6)

Interfaz grafica para controlar el VNA casero (2x ADF4351 + Arduino + placa
de sonido), basada en la logica de `VNA_calibrado.py`.

## Archivos

- `vna_core.py` - Toda la logica de adquisicion, filtrado FIR, FFT, deteccion
  del tono de batido y algebra de calibracion SOL. Es el mismo calculo que
  el script original, solo que sin `input()`/`tkinter` bloqueantes: expone
  callbacks de progreso y una forma de abortar un barrido en curso.
- `vna_gui.py` - La ventana PyQt6: conexion al Arduino, configuracion de
  barrido (inicio/fin/paso), wizard de calibracion SOL con botones,
  medicion del DUT, y graficos en vivo de modulo, fase y abaco de Smith.

## Instalacion

```bash
pip install -r requirements.txt
```

En Windows tambien necesitas el driver USB-serial de tu Arduino (CH340,
FTDI, etc.) instalado para que el puerto COM aparezca en el sistema.

## Uso

```bash
python vna_gui.py
```

1. Cargar el puerto serie (ej. `COM3` o `/dev/ttyACM0`) y presionar
   **Conectar**.
2. Elegir frecuencia de inicio, fin y paso (MHz).
3. Calibracion:
   - **Iniciar calibracion nueva**: pide conectar SHORT, luego OPEN, luego
     LOAD, barriendo con el boton **Barrer paso actual** en cada uno. Al
     terminar LOAD se calcula automaticamente la matriz de error.
   - o **Cargar calibracion desde archivo...** si ya tenes una calibracion
     guardada de un barrido con el mismo rango de frecuencias.
4. **Medir DUT**: conecta el dispositivo a medir y arranca el barrido
   final. Los graficos de modulo, fase y Smith se van actualizando punto
   a punto (con correccion SOL aplicada en vivo si los indices coinciden
   con la calibracion).
5. **Guardar resultados CSV...** al terminar.

## Cosas para revisar/pulir antes de usarlo en serio

Este es un esqueleto funcional pensado para arrancar rapido, no una version
final. Antes de confiar en el para mediciones reales conviene:

- **Probarlo con el hardware real**: no hay forma de validar timing de
  serial/audio sin el Arduino y la placa de sonido conectados.
- **Indice de calibracion vs. DUT**: la correccion en vivo asume que el
  barrido de calibracion y el de DUT excluyen exactamente las mismas
  frecuencias y en el mismo orden. Si cambias `frecuencias_excluidas` entre
  una calibracion vieja y una medicion nueva, el indice puede desalinearse
  (el codigo ya avisa con un QMessageBox si el largo no coincide, pero no
  detecta un desalineamiento parcial).
- **Dispositivo de audio**: `config["dispositivo_audio"]` queda en `None`
  (dispositivo por defecto del sistema). Si necesitas elegir la placa de
  sonido especifica, conviene agregar un combo con
  `sounddevice.query_devices()`.
- **Manejo de reconexion**: si se pierde la conexion serie a mitad de un
  barrido, hoy se corta con una excepcion mostrada en un QMessageBox: capturalo
  y probá que el mensaje sea claro para vos.
- **Empaquetado a .exe**: cuando este validado, `pyinstaller --noconfirm
  --onefile vna_gui.py` (ajustando hooks si sounddevice/matplotlib no se
  detectan solos) te da el ejecutable standalone.
