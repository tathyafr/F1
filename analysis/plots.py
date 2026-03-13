# analysis/plots.py

import pandas as pd
import matplotlib.pyplot as plt


def plot_soc_vs_time(csv_file="results/monza_telemetry.csv"):

    df = pd.read_csv(csv_file)

    plt.figure()

    plt.plot(df["time"], df["soc"])

    plt.xlabel("Time (s)")
    plt.ylabel("State of Charge")

    plt.title("SOC vs Time")

    plt.show()


def plot_power_vs_time(csv_file="results/monza_telemetry.csv"):

    df = pd.read_csv(csv_file)

    plt.figure()

    plt.plot(df["time"], df["power"])

    plt.xlabel("Time (s)")
    plt.ylabel("Power Deployment (W)")

    plt.title("MGU-K Power vs Time")

    plt.show()


def plot_soc_vs_distance(csv_file="results/monza_telemetry.csv"):

    df = pd.read_csv(csv_file)

    plt.figure()

    plt.plot(df["distance"], df["soc"])

    plt.xlabel("Distance Along Track (m)")
    plt.ylabel("State of Charge")

    plt.title("SOC vs Distance (Monza)")

    plt.show()


if __name__ == "__main__":

    plot_soc_vs_time()

    plot_power_vs_time()

    plot_soc_vs_distance()
