
#!/usr/bin/env python3
"""
Superpone dos mediciones de S11 en el mismo grafico (modulo y fase).

Formatos de entrada:
  - .s1p (Touchstone): RI, MA o DB.
  - .csv: columnas freq_rf_MHz, modulo_S11_dB, fase_S11_deg.
  - .pkl: figura de Matplotlib con dos subgraficos:
          primer grafico = modulo de S11
          segundo grafico = fase de S11.

Ambas mediciones se convierten a:
  frecuencia [MHz], modulo [dB], fase [grados].

Uso:
    python plot_s11.py
    python plot_s11.py --invertir-fase-csv
    python plot_s11.py --salida comparacion.png
"""

import argparse
import pickle
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

import numpy as np
import matplotlib.pyplot as plt


# Factor para llevar la frecuencia de la unidad del archivo a MHz
A_MHZ = {
    "HZ": 1e-6,
    "KHZ": 1e-3,
    "MHZ": 1.0,
    "GHZ": 1e3
}


def seleccionar_archivos():
    """Permite seleccionar los archivos de las dos mediciones."""

    root = tk.Tk()
    root.withdraw()

    # Seleccionar archivo S1P
    archivo_s1p = filedialog.askopenfilename(
        title="Seleccionar medición S11 (.s1p)",
        filetypes=[
            ("Archivos Touchstone", "*.s1p"),
            ("Todos los archivos", "*.*")
        ]
    )

    if not archivo_s1p:
        print("No se seleccionó ningún archivo S1P.")
        root.destroy()
        return None, None

    # Seleccionar segundo archivo: CSV o PKL
    archivo_medicion = filedialog.askopenfilename(
        title="Seleccionar segunda medición (.csv o .pkl)",
        filetypes=[
            ("Mediciones CSV o PKL", "*.csv *.pkl"),
            ("Archivos CSV", "*.csv"),
            ("Archivos Pickle", "*.pkl"),
            ("Todos los archivos", "*.*")
        ]
    )

    if not archivo_medicion:
        print("No se seleccionó ningún segundo archivo.")
        root.destroy()
        return None, None

    root.destroy()

    return Path(archivo_s1p), Path(archivo_medicion)


def leer_s1p(ruta):
    """Lee un Touchstone de 1 puerto y devuelve (f_MHz, mag_dB, fase_deg)."""

    unidad, formato = "GHZ", "MA"
    filas = []

    with open(ruta, "r", encoding="utf-8", errors="replace") as fh:
        for linea in fh:

            linea = linea.split("!")[0].strip()

            if not linea:
                continue

            if linea.startswith("#"):
                tokens = linea[1:].upper().split()

                for t in tokens:
                    if t in A_MHZ:
                        unidad = t
                    elif t in ("RI", "MA", "DB"):
                        formato = t

                continue

            filas.append([float(x) for x in linea.split()[:3]])

    d = np.array(filas)

    f_mhz = d[:, 0] * A_MHZ[unidad]

    a, b = d[:, 1], d[:, 2]

    if formato == "RI":
        s = a + 1j * b

    elif formato == "MA":
        s = a * np.exp(1j * np.radians(b))

    else:  # DB
        s = 10 ** (a / 20) * np.exp(1j * np.radians(b))

    mag_db = 20 * np.log10(np.abs(s))
    fase_deg = np.degrees(np.angle(s))

    return f_mhz, mag_db, fase_deg


def leer_csv(ruta):
    """Lee el CSV propio y devuelve (f_MHz, mag_dB, fase_deg)."""

    with open(ruta, "r", encoding="utf-8", errors="replace") as fh:
        encabezado = fh.readline().strip().lower()

    d = np.genfromtxt(ruta, delimiter=",", skip_header=1)

    escala = 1e3 if "ghz" in encabezado else 1.0

    return d[:, 0] * escala, d[:, 1], d[:, 2]


def leer_pkl(ruta):
    """
    Lee una figura de Matplotlib guardada con pickle.dump(fig, f).

    Se espera una figura con dos subgraficos:
      axes[0]: modulo de S11.
      axes[1]: fase de S11.

    Se recuperan los datos de la primera curva de cada subgrafico.
    """

    with open(ruta, "rb") as f:
        fig = pickle.load(f)

    axes = fig.axes

    if len(axes) < 2:
        raise ValueError(
            "El archivo PKL no contiene dos subgraficos."
        )

    if len(axes[0].lines) == 0 or len(axes[1].lines) == 0:
        raise ValueError(
            "No se encontraron curvas en los dos subgraficos."
        )

    # Extraer modulo
    linea_modulo = axes[0].lines[0]

    f_modulo = np.asarray(linea_modulo.get_xdata(), dtype=float)
    mag_db = np.asarray(linea_modulo.get_ydata(), dtype=float)

    # Extraer fase
    linea_fase = axes[1].lines[0]

    f_fase = np.asarray(linea_fase.get_xdata(), dtype=float)
    fase_deg = np.asarray(linea_fase.get_ydata(), dtype=float)

    # Verificar que ambas curvas tengan la misma frecuencia
    if not np.allclose(f_modulo, f_fase, equal_nan=True):
        raise ValueError(
            "Las frecuencias del modulo y la fase no coinciden."
        )

    print("Datos recuperados correctamente del PKL.")
    print(f"Curvas encontradas: {len(axes[0].lines)} (modulo), "
          f"{len(axes[1].lines)} (fase)")

    return f_modulo, mag_db, fase_deg


def envolver(fase_deg):
    """Lleva la fase al rango (-180, 180]."""

    return (fase_deg + 180) % 360 - 180


def cortar_saltos(f, fase_deg):
    """Inserta NaN donde la fase da el salto de +-180."""

    f2, p2 = [f[0]], [fase_deg[0]]

    for i in range(1, len(f)):

        if abs(fase_deg[i] - fase_deg[i - 1]) > 180:
            f2.append(np.nan)
            p2.append(np.nan)

        f2.append(f[i])
        p2.append(fase_deg[i])

    return np.array(f2), np.array(p2)


def leer_medicion(ruta):
    """Selecciona el lector correspondiente según la extensión."""

    extension = ruta.suffix.lower()

    if extension == ".csv":
        return leer_csv(ruta)

    elif extension == ".pkl":
        return leer_pkl(ruta)

    else:
        raise ValueError(
            f"Formato no reconocido: {extension}"
        )


def main():

    p = argparse.ArgumentParser(
        description="Superpone dos mediciones de S11"
    )

    p.add_argument(
        "--invertir-fase-csv",
        action="store_true",
        help="cambia el signo de la fase de la segunda medición"
    )

    p.add_argument(
        "--salida",
        type=Path,
        default=None,
        help="guardar el grafico en este archivo"
    )

    args = p.parse_args()

    # Seleccionar archivos
    archivo_s1p, archivo_medicion = seleccionar_archivos()

    if archivo_s1p is None or archivo_medicion is None:
        return

    # Leer mediciones
    f1, m1, ph1 = leer_s1p(archivo_s1p)

    f2, m2, ph2 = leer_medicion(archivo_medicion)

    if args.invertir_fase_csv:
        ph2 = envolver(-ph2)

    print(
        f"{archivo_s1p.name}: {len(f1)} puntos, "
        f"{f1.min():.1f} a {f1.max():.1f} MHz"
    )

    print(
        f"{archivo_medicion.name}: {len(f2)} puntos, "
        f"{f2.min():.1f} a {f2.max():.1f} MHz"
    )

    # Crear gráficos
    fig, (ax_m, ax_p) = plt.subplots(
        2, 1,
        sharex=True,
        figsize=(10, 7)
    )

    # Módulo
    ax_m.plot(
        f1, m1,
        color="tab:blue",
        lw=1.6,
        label=archivo_s1p.name
    )

    etiqueta_medicion = archivo_medicion.name + (
        " (fase invertida)" if args.invertir_fase_csv else ""
    )

    ax_m.plot(
        f2, m2,
        color="hotpink",
        marker=".",
        markersize=3,
        linestyle="None",
        label=etiqueta_medicion
    )

    ax_m.set_ylabel(r"$|S_{11}|$ (dB)")
    ax_m.set_title("Comparación de mediciones de $S_{11}$")
    ax_m.grid(True, alpha=0.4)
    ax_m.legend()

    # Fase
    fa, pa = cortar_saltos(f1, ph1)
    fb, pb = cortar_saltos(f2, ph2)

    ax_p.plot(
        fa, pa,
        color="tab:blue",
        lw=1.6
    )

    ax_p.plot(
        fb, pb,
        color="hotpink",
        marker=".",
        markersize=3,
        linestyle="None"
    )

    ax_p.set_ylabel(r"Fase de $S_{11}$ (°)")
    ax_p.set_xlabel("Frecuencia (MHz)")
    ax_p.set_ylim(-190, 190)
    ax_p.set_yticks(range(-180, 181, 60))
    ax_p.grid(True, alpha=0.4)

    fig.tight_layout()

    # Mostrar o guardar gráfico
    if args.salida:
        fig.savefig(args.salida, dpi=200)
        print(f"Guardado en {args.salida}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
