#!/usr/bin/env python3
"""
Error máximo de módulo y fase de un CSV respecto de valores ideales,
excluyendo puntos anómalos (outliers).

Uso:
    python max_error.py
        -> abre una ventana para elegir el CSV y pregunta los valores ideales
           por la terminal.
    python max_error.py medicion.csv --mag -0.5 --fase 0
        -> todo por argumentos (lo que no se indique se pregunta/abre igual).
    python max_error.py --mag 0 --fase 180 --mag-unit lin --k 3

Si no se indican las columnas, se buscan por nombre (freq/frec, mod/mag/db,
fase/phase/ang). Para forzarlas: --col-freq, --col-mag, --col-fase.
"""
import argparse
import numpy as np
import pandas as pd


def elegir_archivo():
    """Abre el explorador de archivos para elegir el CSV."""
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)  # que no quede detrás de VS Code
    ruta = filedialog.askopenfilename(
        title="Elegí el archivo CSV",
        filetypes=[("CSV", "*.csv"), ("Todos los archivos", "*.*")],
    )
    root.destroy()
    if not ruta:
        raise SystemExit("No se eligió ningún archivo.")
    return ruta


def pedir_numero(texto):
    while True:
        try:
            return float(input(texto).strip().replace(",", "."))
        except ValueError:
            print("Ingresá un número (ej: -20 o 0,5).")


def buscar_columna(df, claves, nombre):
    for c in df.columns:
        if any(k in str(c).lower() for k in claves):
            return c
    raise SystemExit(
        f"No encontré la columna de {nombre}. Columnas disponibles: "
        f"{list(df.columns)}. Indicala con --col-{nombre}."
    )


def outliers_mad(x, k):
    """Marca outliers con el z-score modificado (mediana y MAD), robusto."""
    x = np.asarray(x, float)
    med = np.nanmedian(x)
    mad = np.nanmedian(np.abs(x - med))
    if mad == 0:  # datos casi constantes: usar desvío estándar
        sigma = np.nanstd(x)
        if sigma == 0:
            return np.zeros_like(x, bool)
        return np.abs(x - med) > k * sigma
    z = 0.6745 * (x - med) / mad
    return np.abs(z) > k


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv", nargs="?", help="ruta del CSV (si no, se abre un selector)")
    p.add_argument("--mag", type=float, help="módulo ideal (si no, se pregunta)")
    p.add_argument("--fase", type=float, help="fase ideal en grados (si no, se pregunta)")
    p.add_argument("--mag-unit", choices=["db", "lin"], default="db",
                   help="unidad del módulo (solo informativo en el reporte)")
    p.add_argument("--k", type=float, default=3.5,
                   help="umbral de outliers (menor = más estricto). Default 3.5")
    p.add_argument("--col-freq")
    p.add_argument("--col-mag")
    p.add_argument("--col-fase")
    a = p.parse_args()

    if a.csv is None:
        a.csv = elegir_archivo()
    if a.mag is None:
        a.mag = pedir_numero("Módulo ideal (en las unidades del CSV): ")
    if a.fase is None:
        a.fase = pedir_numero("Fase ideal (grados): ")

    df = pd.read_csv(a.csv, sep=None, engine="python")  # detecta , ; tab
    c_mag = a.col_mag or buscar_columna(df, ["mod", "mag", "db"], "mag")
    c_fase = a.col_fase or buscar_columna(df, ["fase", "phase", "ang"], "fase")
    c_freq = a.col_freq
    if c_freq is None:
        try:
            c_freq = buscar_columna(df, ["freq", "frec", "mhz", "hz"], "freq")
        except SystemExit:
            c_freq = None

    mag = pd.to_numeric(df[c_mag], errors="coerce").to_numpy()
    fase = pd.to_numeric(df[c_fase], errors="coerce").to_numpy()
    validos = ~(np.isnan(mag) | np.isnan(fase))

    # Errores respecto del ideal (la fase se envuelve a [-180, 180])
    err_mag = mag - a.mag
    err_fase = (fase - a.fase + 180.0) % 360.0 - 180.0

    # Un punto es anómalo si lo es en módulo o en fase
    anomalo = (outliers_mad(err_mag[validos], a.k).astype(bool))
    anomalo_f = outliers_mad(err_fase[validos], a.k).astype(bool)
    flag = np.zeros(len(df), bool)
    flag[np.where(validos)[0]] = anomalo | anomalo_f
    buenos = validos & ~flag

    u = "dB" if a.mag_unit == "db" else ""
    print(f"Archivo: {a.csv}")
    print(f"Puntos totales: {len(df)} | válidos: {validos.sum()} | "
          f"anómalos excluidos: {flag.sum()} | usados: {buenos.sum()}")
    print(f"Ideal: módulo = {a.mag} {u}, fase = {a.fase}°\n")

    for nombre, err, un in [("Módulo", err_mag, u), ("Fase", err_fase, "°")]:
        i = np.nanargmax(np.where(buenos, np.abs(err), -np.inf))
        f_txt = f" en f = {df[c_freq].iloc[i]}" if c_freq else f" (fila {i})"
        print(f"{nombre}: error máximo = {abs(err[i]):.4g} {un}"
              f"{f_txt} | error medio = {np.mean(err[buenos]):+.4g} {un}"
              f" | desvío = {np.std(err[buenos]):.4g} {un}")

    if flag.any():
        print("\nPuntos excluidos como anómalos:")
        cols = [c for c in [c_freq, c_mag, c_fase] if c]
        print(df.loc[flag, cols].to_string())


if __name__ == "__main__":
    main()