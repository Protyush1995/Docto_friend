import pandas as pd
import tkinter as tk
from tkinter import filedialog

def merge_csv(file1, file2, output_file="merged.csv"):
    # Load both CSVs
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)

    # Combine short_composition1 and short_composition2 into salt_composition
    def combine_compositions(df):
        df["salt_composition"] = df["short_composition1"].fillna("") + " " + df["short_composition2"].fillna("")
        return df

    df1 = combine_compositions(df1)
    df2 = combine_compositions(df2)

    # Keep only required columns
    cols_to_keep = ["name", "manufacturer_name", "salt_composition", "Is_discontinued"]
    df1 = df1[cols_to_keep].rename(columns={"manufacturer_name": "brand"})
    df2 = df2[cols_to_keep].rename(columns={"manufacturer_name": "brand"})

    # Merge and drop duplicates by 'name'
    merged = pd.concat([df1, df2], ignore_index=True)
    merged = merged.drop_duplicates(subset=["name"], keep="first")

    # Save to output file
    merged.to_csv(output_file, index=False)
    print(f"Merged file saved as {output_file}")

if __name__ == "__main__":
    # Create a hidden Tkinter root window
    root = tk.Tk()
    root.withdraw()

    print("Select the first CSV file...")
    file1 = filedialog.askopenfilename(title="Select first CSV file", filetypes=[("CSV files", "*.csv")])

    print("Select the second CSV file...")
    file2 = filedialog.askopenfilename(title="Select second CSV file", filetypes=[("CSV files", "*.csv")])

    if file1 and file2:
        merge_csv(file1, file2, "merged.csv")
    else:
        print("File selection cancelled.")
