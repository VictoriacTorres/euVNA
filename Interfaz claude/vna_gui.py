"""
vna_gui.py
==========
Interfaz grafica (PyQt6) para el VNA casero: permite elegir frecuencia de
inicio/fin/paso, conectar el Arduino, correr la calibracion SOL (short /
open / load) paso a paso, medir un DUT, y visualizar en vivo el modulo y
la fase de S11 junto con el abaco de Smith.

Requisitos:
    pip install PyQt6 pyserial sounddevice numpy scipy matplotlib

Ejecutar con:
    python vna_gui.py
"""

import os
import sys

import numpy as np

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QDoubleSpinBox,
    QProgressBar, QFileDialog, QMessageBox, QPlainTextEdit, QSplitter,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import vna_core as core


# ==================== Hilo de trabajo: corre un barrido sin trabar la GUI ====================

class SweepWorker(QThread):
    """Ejecuta core.barrido() en un hilo aparte y reenvia sus resultados como señales Qt."""

    punto_medido = pyqtSignal(int, int, float, complex, float)  # i, n, f_rf, s11, f_batido
    terminado = pyqtSignal(object, object)                      # freqs (ndarray), s11 (ndarray)
    abortado = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, ser, frecuencias_rf, coef_filtro, config, parent=None):
        super().__init__(parent)
        self.ser = ser
        self.frecuencias_rf = frecuencias_rf
        self.coef_filtro = coef_filtro
        self.config = config
        self._abortar = False

    def abortar(self):
        self._abortar = True

    def run(self):
        try:
            freqs, s11 = core.barrido(
                self.ser, self.frecuencias_rf, self.coef_filtro, self.config,
                on_point=lambda i, n, f, s, fb: self.punto_medido.emit(i, n, f, s, fb),
                should_abort=lambda: self._abortar,
            )
            self.terminado.emit(freqs, s11)
        except core.BarridoAbortado:
            self.abortado.emit()
        except Exception as e:  # noqa: BLE001 - se muestra en la GUI
            self.error.emit(str(e))


# ==================== Dibujo del abaco de Smith (fondo estatico) ====================

def dibujar_fondo_smith(ax):
    """Dibuja el grillado clasico de un abaco de Smith (r y x constantes)."""
    ax.clear()
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.15, 1.15)
    ax.set_title("Abaco de Smith")

    theta = np.linspace(0, 2 * np.pi, 400)

    # Circulo unitario (|Gamma| = 1)
    ax.plot(np.cos(theta), np.sin(theta), color="black", linewidth=1.0)
    ax.axhline(0, color="gray", linewidth=0.5)

    # Circulos de resistencia constante (r = 0, 0.2, 0.5, 1, 2, 5)
    for r in (0.0, 0.2, 0.5, 1.0, 2.0, 5.0):
        cx = r / (r + 1)
        rad = 1 / (r + 1)
        x = cx + rad * np.cos(theta)
        y = rad * np.sin(theta)
        ax.plot(x, y, color="gray", linewidth=0.5)

    # Arcos de reactancia constante (x = +/- 0.2, 0.5, 1, 2, 5)
    t = np.linspace(0, 2 * np.pi, 800)
    for x_val in (0.2, 0.5, 1.0, 2.0, 5.0):
        for signo in (1, -1):
            xv = signo * x_val
            cx, cy = 1.0, 1.0 / xv
            rad = abs(1.0 / xv)
            gx = cx + rad * np.cos(t)
            gy = cy + rad * np.sin(t)
            mask = gx ** 2 + gy ** 2 <= 1.0 + 1e-6
            ax.plot(gx[mask], gy[mask], color="gray", linewidth=0.5)


# ==================== Ventana principal ====================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VNA - Control y medición de S11")
        self.resize(1200, 750)

        self.config = core.config_por_defecto()
        self.ser = None
        self.hilo = None

        # Estado de calibracion
        self.cal_paso = 0            # 0 = sin empezar, 1=SHORT, 2=OPEN, 3=LOAD, 4=lista
        self.cal_gm_cc = None
        self.cal_gm_ca = None
        self.cal_gm_50 = None
        self.cal_freqs = None
        self.cal_e00 = None
        self.cal_e11 = None
        self.cal_delta_e = None
        self.cal_disponible = False

        # Buffers de la medicion en curso (para graficar en vivo)
        self.buf_freq = []
        self.buf_mod_db = []
        self.buf_fase_deg = []
        self.buf_gamma = []
        self.ultima_medicion_freqs = None
        self.ultima_medicion_gamma = None
        self.ultima_medicion_mod_db = None
        self.ultima_medicion_fase_deg = None

        self._armar_ui()

    # ---------------------------------------------------------------- UI --

    def _armar_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout_principal = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout_principal.addWidget(splitter)

        panel_izq = self._armar_panel_controles()
        panel_der = self._armar_panel_graficos()

        splitter.addWidget(panel_izq)
        splitter.addWidget(panel_der)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    def _armar_panel_controles(self):
        panel = QWidget()
        panel.setMinimumWidth(340)
        panel.setMaximumWidth(420)
        v = QVBoxLayout(panel)

        # --- Conexion Arduino ---
        gb_conexion = QGroupBox("Conexion Arduino")
        f = QVBoxLayout(gb_conexion)
        fila_puerto = QHBoxLayout()
        fila_puerto.addWidget(QLabel("Puerto:"))
        self.ed_puerto = QLineEdit("COM3")
        fila_puerto.addWidget(self.ed_puerto)
        f.addLayout(fila_puerto)

        fila_baud = QHBoxLayout()
        fila_baud.addWidget(QLabel("Baudrate:"))
        self.ed_baudrate = QLineEdit("115200")
        fila_baud.addWidget(self.ed_baudrate)
        f.addLayout(fila_baud)

        self.btn_conectar = QPushButton("Conectar")
        self.btn_conectar.clicked.connect(self._conectar_arduino)
        f.addWidget(self.btn_conectar)

        self.lbl_estado_conexion = QLabel("Desconectado")
        f.addWidget(self.lbl_estado_conexion)
        v.addWidget(gb_conexion)

        # --- Barrido ---
        gb_barrido = QGroupBox("Barrido de frecuencia")
        f2 = QVBoxLayout(gb_barrido)

        self.sp_f_inicio = self._nuevo_spin(1800.0, 0, 6000, " MHz")
        self.sp_f_fin = self._nuevo_spin(2200.0, 0, 6000, " MHz")
        self.sp_f_paso = self._nuevo_spin(1.0, 0.001, 1000, " MHz")

        f2.addWidget(self._fila("F inicio:", self.sp_f_inicio))
        f2.addWidget(self._fila("F fin:", self.sp_f_fin))
        f2.addWidget(self._fila("F paso:", self.sp_f_paso))
        v.addWidget(gb_barrido)

        # --- Calibracion SOL ---
        gb_cal = QGroupBox("Calibracion SOL")
        f3 = QVBoxLayout(gb_cal)

        self.lbl_estado_cal = QLabel("Sin calibrar")
        f3.addWidget(self.lbl_estado_cal)

        self.btn_cal_iniciar = QPushButton("Iniciar calibracion nueva")
        self.btn_cal_iniciar.clicked.connect(self._iniciar_calibracion)
        f3.addWidget(self.btn_cal_iniciar)

        self.btn_cal_paso = QPushButton("Barrer paso actual")
        self.btn_cal_paso.setEnabled(False)
        self.btn_cal_paso.clicked.connect(self._barrer_paso_calibracion)
        f3.addWidget(self.btn_cal_paso)

        self.btn_cal_cargar = QPushButton("Cargar calibracion desde archivo...")
        self.btn_cal_cargar.clicked.connect(self._cargar_calibracion)
        f3.addWidget(self.btn_cal_cargar)

        self.btn_cal_guardar = QPushButton("Guardar calibracion actual...")
        self.btn_cal_guardar.setEnabled(False)
        self.btn_cal_guardar.clicked.connect(self._guardar_calibracion)
        f3.addWidget(self.btn_cal_guardar)

        v.addWidget(gb_cal)

        # --- Medicion DUT ---
        gb_dut = QGroupBox("Medición del DUT")
        f4 = QVBoxLayout(gb_dut)

        self.btn_medir = QPushButton("Medir DUT")
        self.btn_medir.setEnabled(False)
        self.btn_medir.clicked.connect(self._iniciar_medicion_dut)
        f4.addWidget(self.btn_medir)

        self.btn_abortar = QPushButton("Abortar barrido")
        self.btn_abortar.setEnabled(False)
        self.btn_abortar.clicked.connect(self._abortar_barrido)
        f4.addWidget(self.btn_abortar)

        self.progreso = QProgressBar()
        f4.addWidget(self.progreso)

        self.btn_guardar_resultados = QPushButton("Guardar resultados CSV...")
        self.btn_guardar_resultados.setEnabled(False)
        self.btn_guardar_resultados.clicked.connect(self._guardar_resultados)
        f4.addWidget(self.btn_guardar_resultados)

        v.addWidget(gb_dut)

        # --- Log ---
        gb_log = QGroupBox("Log")
        f5 = QVBoxLayout(gb_log)
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        f5.addWidget(self.txt_log)
        v.addWidget(gb_log, stretch=1)

        return panel

    def _armar_panel_graficos(self):
        panel = QWidget()
        v = QVBoxLayout(panel)

        # Figura módulo + fase (dos subplots apilados)
        self.fig_mf = Figure(figsize=(6, 5), facecolor="#fad7ea")
        self.ax_mod = self.fig_mf.add_subplot(211)
        self.ax_fase = self.fig_mf.add_subplot(212, sharex=self.ax_mod)
        self._preparar_ejes_mod_fase()
        self.canvas_mf = FigureCanvas(self.fig_mf)

        # Figura abaco de Smith
        self.fig_smith = Figure(figsize=(5, 5), facecolor="#fad7ea")
        self.ax_smith = self.fig_smith.add_subplot(111)
        dibujar_fondo_smith(self.ax_smith)
        (self.linea_smith,) = self.ax_smith.plot([], [], color="deeppink",
                                                  marker=".", linewidth=1)
        self.canvas_smith = FigureCanvas(self.fig_smith)

        fila_graficos = QHBoxLayout()
        fila_graficos.addWidget(self.canvas_mf, stretch=1)
        fila_graficos.addWidget(self.canvas_smith, stretch=1)
        v.addLayout(fila_graficos)

        return panel

    def _preparar_ejes_mod_fase(self):
        self.ax_mod.clear()
        self.ax_mod.set_facecolor("#fad7ea")
        self.ax_mod.set_title("S11 - Módulo")
        self.ax_mod.set_ylabel("|S11| (dB)")
        self.ax_mod.grid(True, alpha=0.3)
        (self.linea_mod,) = self.ax_mod.plot([], [], color="deeppink",
                                              marker=".", linewidth=1)

        self.ax_fase.clear()
        self.ax_fase.set_facecolor("#fad7ea")
        self.ax_fase.set_title("S11 - Fase")
        self.ax_fase.set_xlabel("Frecuencia de RF (MHz)")
        self.ax_fase.set_ylabel("Fase (grados)")
        self.ax_fase.grid(True, alpha=0.3)
        (self.linea_fase,) = self.ax_fase.plot([], [], color="darkmagenta",
                                                marker=".", linewidth=1)
        self.fig_mf.tight_layout()

    @staticmethod
    def _nuevo_spin(valor, minimo, maximo, sufijo):
        sp = QDoubleSpinBox()
        sp.setDecimals(3)
        sp.setRange(minimo, maximo)
        sp.setValue(valor)
        sp.setSuffix(sufijo)
        return sp

    @staticmethod
    def _fila(etiqueta, widget):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(QLabel(etiqueta))
        h.addWidget(widget)
        return w

    def _log(self, texto):
        self.txt_log.appendPlainText(texto)

    # ---------------------------------------------------------- Conexion --

    def _conectar_arduino(self):
        puerto = self.ed_puerto.text().strip()
        try:
            baudrate = int(self.ed_baudrate.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Baudrate invalido", "El baudrate debe ser un numero entero.")
            return

        try:
            self.ser, linea = core.conectar_arduino(puerto, baudrate)
        except Exception as e:
            QMessageBox.critical(self, "Error de conexion", str(e))
            self.lbl_estado_conexion.setText("Error de conexion")
            return

        self.lbl_estado_conexion.setText(f"Conectado ({puerto} @ {baudrate})")
        if linea:
            self._log(f"Arduino: {linea}")
        self._log(f"Conectado a {puerto} @ {baudrate} baud.")

    # --------------------------------------------------------- Utilidades --

    def _construir_frecuencias(self):
        inicio = self.sp_f_inicio.value()
        fin = self.sp_f_fin.value()
        paso = self.sp_f_paso.value()
        return core.generar_frecuencias(inicio, fin, paso)

    def _construir_filtro(self):
        return core.diseñar_filtro_pasabanda(
            self.config["fs_audio"], self.config["f_centro_filtro"],
            self.config["ancho_banda_filtro"], self.config["numtaps_filtro"],
            self.config["duracion_captura_s"],
        )

    def _validar_listo_para_barrer(self):
        if self.ser is None:
            QMessageBox.warning(self, "Sin conexion", "Primero conecta el Arduino.")
            return False
        if self.hilo is not None and self.hilo.isRunning():
            QMessageBox.warning(self, "Barrido en curso", "Ya hay un barrido corriendo.")
            return False
        return True

    def _lanzar_barrido(self, frecuencias, on_terminado, on_abortado=None, on_error=None):
        coef_filtro = self._construir_filtro()
        self.hilo = SweepWorker(self.ser, frecuencias, coef_filtro, self.config)
        self.hilo.punto_medido.connect(self._on_punto_generico)
        self.hilo.terminado.connect(on_terminado)
        self.hilo.abortado.connect(on_abortado or self._on_abortado_generico)
        self.hilo.error.connect(on_error or self._on_error_generico)
        self.progreso.setValue(0)
        self.btn_abortar.setEnabled(True)
        self.hilo.start()

    def _on_punto_generico(self, i, n, f_rf, s11, f_batido):
        self.progreso.setMaximum(n)
        self.progreso.setValue(i)
        mod_db = 20 * np.log10(abs(s11) + 1e-12)
        fase_deg = np.degrees(np.angle(s11))
        self._log(f"[{i}/{n}] RF={f_rf:.3f} MHz  batido={f_batido:.1f} Hz  "
                  f"|S11|={mod_db:.2f} dB  fase={fase_deg:.1f} deg")

    def _on_abortado_generico(self):
        self.btn_abortar.setEnabled(False)
        self._log("Barrido abortado por el usuario.")

    def _on_error_generico(self, mensaje):
        self.btn_abortar.setEnabled(False)
        QMessageBox.critical(self, "Error durante el barrido", mensaje)
        self._log(f"ERROR: {mensaje}")

    def _abortar_barrido(self):
        if self.hilo is not None and self.hilo.isRunning():
            self.hilo.abortar()

    # ------------------------------------------------------- Calibracion --

    ETIQUETAS_PASO_CAL = {
        1: "Paso 1/3: conecte SHORT (cortocircuito) y presione 'Barrer paso actual'.",
        2: "Paso 2/3: conecte OPEN (circuito abierto) y presione 'Barrer paso actual'.",
        3: "Paso 3/3: conecte LOAD (50 ohm) y presione 'Barrer paso actual'.",
    }

    def _iniciar_calibracion(self):
        if not self._validar_listo_para_barrer():
            return
        self.cal_paso = 1
        self.cal_gm_cc = self.cal_gm_ca = self.cal_gm_50 = None
        self.cal_disponible = False
        self.btn_medir.setEnabled(False)
        self.btn_cal_guardar.setEnabled(False)
        self.btn_cal_paso.setEnabled(True)
        self.lbl_estado_cal.setText(self.ETIQUETAS_PASO_CAL[1])

    def _barrer_paso_calibracion(self):
        if not self._validar_listo_para_barrer():
            return
        frecuencias = self._construir_frecuencias()
        self.btn_cal_paso.setEnabled(False)
        self.btn_cal_iniciar.setEnabled(False)
        self._lanzar_barrido(
            frecuencias,
            on_terminado=self._on_paso_calibracion_terminado,
            on_abortado=self._on_calibracion_abortada,
        )

    def _on_calibracion_abortada(self):
        self._on_abortado_generico()
        self.btn_cal_paso.setEnabled(True)
        self.btn_cal_iniciar.setEnabled(True)

    def _on_paso_calibracion_terminado(self, freqs, gm):
        self.btn_abortar.setEnabled(False)
        self.btn_cal_iniciar.setEnabled(True)
        self.cal_freqs = freqs

        if self.cal_paso == 1:
            self.cal_gm_cc = gm
            self.cal_paso = 2
            self.lbl_estado_cal.setText(self.ETIQUETAS_PASO_CAL[2])
            self.btn_cal_paso.setEnabled(True)
        elif self.cal_paso == 2:
            self.cal_gm_ca = gm
            self.cal_paso = 3
            self.lbl_estado_cal.setText(self.ETIQUETAS_PASO_CAL[3])
            self.btn_cal_paso.setEnabled(True)
        elif self.cal_paso == 3:
            self.cal_gm_50 = gm
            self._finalizar_calculo_calibracion()

    def _finalizar_calculo_calibracion(self):
        n = len(self.cal_freqs)
        if not (len(self.cal_gm_cc) == len(self.cal_gm_ca) == len(self.cal_gm_50) == n):
            QMessageBox.warning(
                self, "Inconsistencia",
                "Los tres barridos de calibracion (SHORT/OPEN/LOAD) no tienen la "
                "misma cantidad de puntos. Revisa que no se haya abortado ninguno "
                "a mitad de camino."
            )
            self.cal_paso = 0
            self.btn_cal_paso.setEnabled(False)
            return

        self.cal_e00, self.cal_e11, self.cal_delta_e = core.calculo_errores(
            self.cal_gm_cc, self.cal_gm_ca, self.cal_gm_50, n
        )
        self.cal_disponible = True
        self.cal_paso = 4
        self.lbl_estado_cal.setText(f"Calibracion lista ({n} puntos).")
        self.btn_cal_paso.setEnabled(False)
        self.btn_cal_guardar.setEnabled(True)
        self.btn_medir.setEnabled(True)
        self._log("Calibracion SOL calculada correctamente.")

    def _cargar_calibracion(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Cargar calibracion", "", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            freqs, e00, e11, delta_e = core.cargar_calibracion_csv(path)
        except Exception as e:
            QMessageBox.critical(self, "Error al cargar", str(e))
            return

        self.cal_freqs, self.cal_e00, self.cal_e11, self.cal_delta_e = freqs, e00, e11, delta_e
        self.cal_disponible = True
        self.cal_paso = 4
        self.lbl_estado_cal.setText(f"Calibracion cargada desde archivo ({len(freqs)} puntos).")
        self.btn_medir.setEnabled(True)
        self.btn_cal_guardar.setEnabled(False)
        self._log(f"Calibracion cargada de {path}")

    def _guardar_calibracion(self):
        if not self.cal_disponible:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar calibracion", "calibracion.csv", "CSV (*.csv)"
        )
        if not path:
            return
        core.guardar_calibracion_csv(path, self.cal_freqs, self.cal_e00, self.cal_e11, self.cal_delta_e)
        self._log(f"Calibracion guardada en {path}")

    # ------------------------------------------------------- Medicion DUT --

    def _iniciar_medicion_dut(self):
        if not self._validar_listo_para_barrer():
            return
        if not self.cal_disponible:
            QMessageBox.warning(self, "Sin calibracion", "Primero completa o carga una calibracion.")
            return

        frecuencias = self._construir_frecuencias()

        # Reiniciar buffers y graficos
        self.buf_freq, self.buf_mod_db, self.buf_fase_deg, self.buf_gamma = [], [], [], []
        self._preparar_ejes_mod_fase()
        self.canvas_mf.draw()
        dibujar_fondo_smith(self.ax_smith)
        (self.linea_smith,) = self.ax_smith.plot([], [], color="deeppink", marker=".", linewidth=1)
        self.canvas_smith.draw()

        self.btn_medir.setEnabled(False)
        self.btn_guardar_resultados.setEnabled(False)

        self._lanzar_barrido(
            frecuencias,
            on_terminado=self._on_medicion_dut_terminada,
            on_abortado=self._on_medicion_dut_abortada,
        )
        # Reconectamos punto_medido a un manejador especifico para DUT
        # (ademas del log generico que ya se conecto en _lanzar_barrido)
        self.hilo.punto_medido.connect(self._on_punto_dut)

    def _on_medicion_dut_abortada(self):
        self._on_abortado_generico()
        self.btn_medir.setEnabled(True)

    def _indice_calibracion_valido(self, i_1_based):
        idx = i_1_based - 1
        return self.cal_e00 is not None and 0 <= idx < len(self.cal_e00)

    def _on_punto_dut(self, i, n, f_rf, s11_crudo, f_batido):
        # Si hay calibracion punto-a-punto disponible, corregimos en vivo.
        if self._indice_calibracion_valido(i):
            idx = i - 1
            gamma = core.correccion_punto(
                s11_crudo, self.cal_e00[idx], self.cal_e11[idx], self.cal_delta_e[idx]
            )
        else:
            gamma = s11_crudo  # fallback: se corrige todo al final

        mod_db = 20 * np.log10(abs(gamma) + 1e-12)
        fase_deg = np.degrees(np.angle(gamma))

        self.buf_freq.append(f_rf)
        self.buf_mod_db.append(mod_db)
        self.buf_fase_deg.append(fase_deg)
        self.buf_gamma.append(gamma)

        self.linea_mod.set_data(self.buf_freq, self.buf_mod_db)
        self.linea_fase.set_data(self.buf_freq, self.buf_fase_deg)
        for ax in (self.ax_mod, self.ax_fase):
            ax.relim()
            ax.autoscale_view()
        self.canvas_mf.draw_idle()

        self.linea_smith.set_data([g.real for g in self.buf_gamma],
                                   [g.imag for g in self.buf_gamma])
        self.canvas_smith.draw_idle()

    def _on_medicion_dut_terminada(self, freqs, gm_dut):
        self.btn_abortar.setEnabled(False)
        self.btn_medir.setEnabled(True)

        if len(freqs) != len(self.cal_e00):
            QMessageBox.warning(
                self, "Advertencia de consistencia",
                "La cantidad de puntos medidos no coincide con la calibracion "
                "(revisa el rango de frecuencias). Se muestran los valores "
                "corregidos en vivo, pero puede haber un corrimiento de indice."
            )

        n = min(len(freqs), len(self.cal_e00))
        gamma_corregido = core.correccion(
            gm_dut[:n], self.cal_e00[:n], self.cal_e11[:n], self.cal_delta_e[:n], n
        )
        mod_db, fase_deg = core.modulo_fase(gamma_corregido)

        self.ultima_medicion_freqs = freqs[:n]
        self.ultima_medicion_gamma = gamma_corregido
        self.ultima_medicion_mod_db = mod_db
        self.ultima_medicion_fase_deg = fase_deg

        self.btn_guardar_resultados.setEnabled(True)
        self._log(f"Medicion de DUT finalizada: {n} puntos corregidos.")

    def _guardar_resultados(self):
        if self.ultima_medicion_freqs is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar resultados", "resultado_S11.csv", "CSV (*.csv)"
        )
        if not path:
            return
        core.guardar_resultados_csv(
            path, self.ultima_medicion_freqs,
            self.ultima_medicion_mod_db, self.ultima_medicion_fase_deg,
        )
        self._log(f"Resultados guardados en {path}")

    # ------------------------------------------------------------- Cierre --

    def closeEvent(self, event):
        if self.hilo is not None and self.hilo.isRunning():
            self.hilo.abortar()
            self.hilo.wait(2000)
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QMainWindow, QWidget, QGroupBox {background-color: #fad7ea; }""")
    ventana = MainWindow()
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
