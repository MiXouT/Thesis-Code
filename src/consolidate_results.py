import pandas as pd
import os
import glob
import json
import sys

# Add parent directory to path to allow importing src.config if run from src/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import src.config as config
except ImportError:
    # Fallback if run from root and src is a package
    try:
        from src import config
    except ImportError:
        config = None


def get_best_solution_stats(csv_file):
    if not os.path.exists(csv_file):
        return "N/A"
    try:
        df = pd.read_csv(csv_file)
        if df.empty:
            return "No Data"
        # Sort by Uncovered (asc), then Power (asc)
        df_sorted = df.sort_values(by=["Uncovered", "Power"], ascending=[True, True])
        best = df_sorted.iloc[0]
        return f"Uncovered: {best['Uncovered']:.1f}, Power: {best['Power']:.2f}W, Interference: {best['Interference']:.1f}"
    except Exception as e:
        return f"Error calculating stats: {e}"


def get_layout_name():
    layout_path = os.path.join(os.path.dirname(__file__), "..", "layout.json")
    if os.path.exists(layout_path):
        try:
            with open(layout_path, "r") as f:
                data = json.load(f)
                return data.get("name", "Unknown Layout")
        except:
            return "Unknown Layout"
    return "Unknown Layout (File not found)"


def consolidate_data():
    output_xlsx = "thesis_data_compiled.xlsx"
    output_combined_csv = "combined_solutions.csv"

    writer = pd.ExcelWriter(output_xlsx, engine="openpyxl")

    print("Compiling separate CSVs into Excel sheets...")

    # 1. Raw Solutions (Merge these)
    solutions = []
    for schema, name in [
        ("results_ai.csv", "AI"),
        ("results_random.csv", "Random"),
        ("results_grid.csv", "Grid"),
    ]:
        if os.path.exists(schema):
            df = pd.read_csv(schema)
            # Remove existing Method column if it exists to avoid duplication
            if "Method" in df.columns:
                df = df.drop(columns=["Method"])
            df["Method"] = name
            solutions.append(df)
            # Write individual to Excel too
            df.to_excel(writer, sheet_name=f"Raw_{name}", index=False)
            print(f"Added {schema} to Excel.")

    if solutions:
        combined_df = pd.concat(solutions, ignore_index=True)
        # Reorder columns to put Method first
        cols = ["Method"] + [c for c in combined_df.columns if c != "Method"]
        combined_df = combined_df[cols]

        combined_df.to_csv(output_combined_csv, index=False)
        combined_df.to_excel(writer, sheet_name="Combined_Solutions", index=False)
        print(f"Created {output_combined_csv} and added to Excel.")

    # 2. Other Stats
    misc_files = [
        "convergence_history.csv",
        "energy_stats.csv",
        "interference_stats.csv",
        "coverage_efficiency.csv",
    ]

    for f in misc_files:
        if os.path.exists(f):
            df = pd.read_csv(f)
            # Sheet name limit is 31 chars
            sheet_name = f.replace(".csv", "")[:31]
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"Added {f} to Excel as sheet '{sheet_name}'.")

    writer.close()
    print(f"\nSuccessfully created {output_xlsx}")

    # 3. Create Flat Text File (Appendix Style)
    text_output = "thesis_complete_data.txt"
    print(f"Creating metrics dump: {text_output}...")

    # Gather Metadata
    layout_name = get_layout_name()
    poe_status = "On" if getattr(config, "POE_ENABLED", False) else "Off"
    base_load = getattr(config, "ROUTER_BASE_LOAD_WATTS", "N/A")
    tx_levels = getattr(config, "TX_POWER_LEVELS", "N/A")

    ai_stats = get_best_solution_stats("results_ai.csv")
    rnd_stats = get_best_solution_stats("results_random.csv")
    grid_stats = get_best_solution_stats("results_grid.csv")

    with open(text_output, "w") as f_out:
        f_out.write("=======================================================\n")
        f_out.write("THESIS SIMULATION DATA - COMPLETE TEXT DUMP\n")
        f_out.write("=======================================================\n\n")

        f_out.write("-------------------------------------------------------\n")
        f_out.write("SIMULATION METADATA\n")
        f_out.write("-------------------------------------------------------\n")
        f_out.write(f"Layout Name:       {layout_name}\n")
        f_out.write(f"PoE Enabled:       {poe_status}\n")
        f_out.write(f"Base Load:         {base_load} W\n")
        f_out.write(f"Tx Power Levels:   {tx_levels} dBm\n\n")

        f_out.write("-------------------------------------------------------\n")
        f_out.write("BEST SOLUTIONS FOUND (Min Uncovered, then Min Power)\n")
        f_out.write("-------------------------------------------------------\n")
        f_out.write(f"AI (NSGA-II):      {ai_stats}\n")
        f_out.write(f"Random Search:     {rnd_stats}\n")
        f_out.write(f"Grid Deployment:   {grid_stats}\n\n")

        # Helper to dump file
        def dump_csv(filename, title):
            if os.path.exists(filename):
                f_out.write(
                    f"-------------------------------------------------------\n"
                )
                f_out.write(f"DATASET: {title} ({filename})\n")
                f_out.write(
                    f"-------------------------------------------------------\n"
                )
                with open(filename, "r") as f_in:
                    f_out.write(f_in.read())
                f_out.write("\n\n")
                print(f"Appended {filename}")
            else:
                print(f"Warning: {filename} not found.")

        # Dump order
        dump_csv(
            "combined_solutions.csv",
            "Section 4.1: Pareto Front Solutions (AI + Baselines)",
        )
        dump_csv("convergence_history.csv", "Section 4.2: Convergence History")
        dump_csv(
            "coverage_efficiency.csv", "Section 4.3.1: Coverage Efficiency Buckets"
        )
        dump_csv("energy_stats.csv", "Section 4.3.2: Energy Distribution Statistics")
        dump_csv("interference_stats.csv", "Section 4.3.3: Interference Statistics")
        dump_csv("stats_report.md", "Section 4.3.4: Statistical Significance Report")

    print(f"Successfully created {text_output}")


if __name__ == "__main__":
    consolidate_data()
