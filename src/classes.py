import os

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MultipleLocator


class BioprocessMonitor:
    def __init__(self, filepath, ph_lims, temperature_lims):
        """
        Utility class used to monitor bioprocesses by
        generating dashboards and summaries.

        Parameters
        ----------
        filepath : str
            Input CSV dataset path.
        ph_lims : tuple[float, float]
            Lower and upper acceptable pH limits.
        temperature_lims : tuple[float, float]
            Lower and upper acceptable temperature limits.
        """
        self.df = pd.read_csv(filepath)
        self.ph_lims = ph_lims
        self.temperature_lims = temperature_lims

    def extract_batch(self, batch_id):
        """
        Extracts data corresponding to a single batch.

        Parameters
        ----------
        batch_id : int
            Batch identifier.

        Returns
        -------
        pandas.DataFrame
            DataFrame containing only rows associated with
            the requested batch.
        """
        df_batch = self.df[self.df["batch_id"] == batch_id]
        return df_batch.sort_values("time_h").reset_index(drop=True)

    def optimal_ph_mask(self, df_batch):
        """
        Determines whether each pH measurement falls within
        the acceptable operating range.

        Parameters
        ----------
        df_batch : pandas.DataFrame
            Batch-specific DataFrame.

        Returns
        -------
        array-like of bool
            A mask whereby True indicates that the measurement
            is within the acceptable operating range.
        """
        low, high = self.ph_lims
        return df_batch["pH"].between(low, high)

    def optimal_temperature_mask(self, df_batch):
        """
        Determines whether each temperature measurement falls
        within the acceptable operating range.

        Parameters
        ----------
        df_batch : pandas.DataFrame
            Batch-specific DataFrame.

        Returns
        -------
        array-like of bool
            A mask whereby True indicates that the measurement
            is within the acceptable operating range.
        """
        low, high = self.temperature_lims
        return df_batch["temperature_C"].between(low, high)

    def get_n_batches(self):
        """
        Determines the number of unique batches present
        in the dataset.

        Returns
        -------
        int
            Total number of distinct batch identifiers.
        """
        return int(self.df["batch_id"].nunique())

    def export_dashboard(self, batch_id, filepath):
        """
        Creates and saves a dashboard figure for a single batch.

        Parameters
        ----------
        batch_id : int
            Batch identifier.
        filepath : str
            Output PNG image path.
        """
        df = self.extract_batch(batch_id)
        t = df["time_h"]

        fig, axes = plt.subplots(2, 2, figsize=(12, 9))
        ax_conc, ax_temp, ax_ph, ax_do = axes.ravel()

        edge = dict(edgecolors="black", linewidths=0.5, alpha=0.8)

        # Top-left: concentrations
        ax_conc.scatter(t, df["C_glucose_g_L^-1"], color="tab:blue",
                        marker="o", label="Glucose", **edge)
        ax_conc.scatter(t, df["C_biomass_g_L^-1"], color="tab:orange",
                        marker="^", label="Biomass", **edge)
        ax_conc.scatter(t, df["C_product_g_L^-1"], color="tab:green",
                        marker="s", label="Product", **edge)
        ax_conc.set_ylabel("Concentration [g/L]")
        ax_conc.legend()

        # Top-right and bottom-left: optimal vs sub-optimal
        panels = [
            (ax_temp, "temperature_C", self.optimal_temperature_mask(df),
             "Temperature [°C]"),
            (ax_ph, "pH", self.optimal_ph_mask(df), "pH"),
        ]
        for ax, col, mask, ylabel in panels:
            ax.scatter(t[mask], df.loc[mask, col], color="tab:green",
                       marker="o", label="Optimal", **edge)
            ax.scatter(t[~mask], df.loc[~mask, col], color="tab:red",
                       marker="X", label="Sub-Optimal", **edge)
            ax.set_ylabel(ylabel)
            ax.legend()

        # Bottom-right: dissolved oxygen
        ax_do.scatter(t, df["DO_percent"], color="tab:blue", marker="o", **edge)
        ax_do.set_ylabel("Dissolved Oxygen (DO) [%]")

        # Consistent x-axis formatting
        for ax in axes.ravel():
            ax.set_xlabel("Time [h]")
            ax.xaxis.set_major_locator(MultipleLocator(6))

        fig.tight_layout()

        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)
        fig.savefig(filepath, dpi=150)
        plt.close(fig)

    def export_summary(self, filepath):
        """
        Generates a batch summary table and exports it to a CSV file.

        Parameters
        ----------
        filepath : str
            Output CSV table path.
        """
        rows = []
        for batch_id in sorted(self.df["batch_id"].unique()):
            df = self.extract_batch(batch_id)
            rows.append({
                "batch_id": int(batch_id),
                "ph_optimal_percent": round(
                    100 * self.optimal_ph_mask(df).mean(), 2),
                "temperature_optimal_percent": round(
                    100 * self.optimal_temperature_mask(df).mean(), 2),
                "C_product_g_L^-1_final": df["C_product_g_L^-1"].iloc[-1],
            })

        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)
        pd.DataFrame(rows).to_csv(filepath, index=False)
