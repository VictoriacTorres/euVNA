import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from tkinter import Tk, filedialog

# Parámetros del barrido
F_INICIO_MHZ = 1800
F_FIN_MHZ = 2200
F_PASO_MHZ = 1
F_CENTRO_FILTRO = 0  # Completar con el valor utilizado


def graficar_resultado(freq_rf, modulo_db, fase_deg):
    fig, axs = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    axs[0].plot(freq_rf, modulo_db, color="deeppink",
                marker=".", linestyle="None")
    axs[0].set_title("S11 - Módulo")
    axs[0].set_ylabel("|S11| (dB)")
    axs[0].grid(True, alpha=0.3)

    axs[1].plot(freq_rf, fase_deg, color="darkmagenta",
                marker=".", linestyle="None")
    axs[1].set_title("S11 - Fase")
    axs[1].set_xlabel("Frecuencia de RF (MHz)")
    axs[1].set_ylabel("Fase (grados)")
    axs[1].grid(True, alpha=0.3)

    elementos_leyenda = [
        Line2D([], [], color="none",
               label=f"F inicio: {F_INICIO_MHZ:.3f} MHz"),
        Line2D([], [], color="none",
               label=f"F fin: {F_FIN_MHZ:.3f} MHz"),
        Line2D([], [], color="none",
               label=f"F paso: {F_PASO_MHZ:.3f} MHz"),
        Line2D([], [], color="none",
               label=f"F centro filtro: {F_CENTRO_FILTRO:.0f} Hz"),
    ]

    fig.legend(handles=elementos_leyenda, loc="lower center",
               ncol=2, frameon=True)

    plt.tight_layout(rect=(0, 0.10, 1, 1))
    plt.show()


# Seleccionar archivo CSV
root = Tk()
root.withdraw()
root.attributes("-topmost", True)

archivo = filedialog.askopenfilename(
    title="Seleccionar archivo de resultados S11",
    filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
)

root.destroy()

if archivo:
    datos = pd.read_csv(archivo)

    freq_rf = datos["freq_rf_MHz"].to_numpy()
    modulo_db = datos["modulo_S11_dB"].to_numpy()
    fase_deg = datos["fase_S11_deg"].to_numpy()

    graficar_resultado(freq_rf, modulo_db, fase_deg)

else:
    print("No se seleccionó ningún archivo.")