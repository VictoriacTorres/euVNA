import pickle
import os
import tkinter as tk
from tkinter import filedialog, messagebox

import matplotlib.pyplot as plt

ventana = tk.Tk()
ventana.withdraw()
try:
    archivos_seleccionados = filedialog.askopenfilenames(
        title="Seleccionar figura",
        initialdir=os.path.dirname(os.path.abspath(__file__)),
        filetypes=[("Figuras pickle", "*.pkl"), ("Todos los archivos", "*.*")]
    )
finally:
    ventana.destroy()

if not archivos_seleccionados:
    raise SystemExit("No se seleccionó ninguna figura.")

figuras_abiertas = []
for archivo_seleccionado in archivos_seleccionados:
    try:
        with open(archivo_seleccionado, "rb") as archivo:
            figuras_abiertas.append(pickle.load(archivo))
    except Exception as error:
        messagebox.showerror(
            "Error al abrir la figura",
            f"{archivo_seleccionado}\n\n{error}"
        )

if not figuras_abiertas:
    raise SystemExit("No se pudo abrir ninguna figura.")

plt.show()