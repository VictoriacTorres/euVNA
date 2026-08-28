import pickle
import matplotlib.pyplot as plt

with open("fft_wav.pkl", "rb") as archivo:
    figura = pickle.load(archivo)

plt.show()