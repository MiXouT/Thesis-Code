import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats
import os


def load_data():
    ai = pd.read_csv("results_ai.csv")
    rnd = pd.read_csv("results_random.csv")
    grid = pd.read_csv("results_grid.csv")
    return ai, rnd, grid


def analyze_significance(ai, rnd, grid):
    """
    Perform Mann-Whitney U test (non-parametric) to check if AI is significantly better.
    """
    report = "# Statistical Significance Report (Section 4.3.4)\n\n"
    report += "**Method:** Mann-Whitney U Test (Two-sided)\n"
    report += "**Alpha:** 0.05\n\n"

    methods = {"Random": rnd, "Grid": grid}
    metrics = ["Power", "Interference"]

    for m_name, m_data in methods.items():
        report += f"## Comparison: AI vs {m_name}\n"
        for metric in metrics:
            # For Grid, we might have very few samples, so test might be weak
            # But we do it anyway.

            # AI Data
            a = ai[metric].values
            # Baseline Data
            b = m_data[metric].values

            # Test
            stat, p_value = stats.mannwhitneyu(a, b, alternative="two-sided")

            # Interpretation (We want AI < Baseline for minimization)
            # Check means to see direction
            mean_ai = np.mean(a)
            mean_base = np.mean(b)
            improvement = (mean_base - mean_ai) / mean_base * 100

            is_significant = p_value < 0.05
            verdict = "Significant" if is_significant else "Not Significant"

            report += f"- **{metric}**:\n"
            report += f"  - AI Mean: {mean_ai:.2f} | {m_name} Mean: {mean_base:.2f}\n"
            report += f"  - Improvement: {improvement:.1f}%\n"
            report += f"  - p-value: {p_value:.2e} ({verdict})\n\n"

    return report


def plot_interference_boxplot(ai, rnd, grid):
    """
    Section 4.3.3: Interference Mitigation Analysis
    """
    fig = go.Figure()
    fig.add_trace(
        go.Box(y=ai["Interference"], name="AI (NSGA-II)", marker_color="blue")
    )
    fig.add_trace(go.Box(y=rnd["Interference"], name="Random", marker_color="gray"))
    fig.add_trace(go.Box(y=grid["Interference"], name="Grid", marker_color="orange"))

    fig.update_layout(
        title="Interference Mitigation Analysis (Comparison)",
        yaxis_title="Interference Count (Overlapping Signals)",
        showlegend=False,
    )
    return fig


def plot_coverage_barchart(ai, rnd, grid):
    """
    Section 4.3.1: Coverage Efficiency Analysis (Fixed Energy Budgets)
    We bin samples into energy ranges and compare Mean Uncovered Sensors.
    """
    # Define Energy Buckets (Watts)
    # Based on ranges: AI is 0-30W. Grid starts at 10W.
    # Let's assess at 10W, 20W, 30W.
    buckets = [(9, 11, "10 Watts"), (19, 21, "20 Watts"), (29, 31, "30 Watts")]

    data_points = []

    for low, high, label in buckets:
        # Filter data
        ai_set = ai[(ai["Power"] >= low) & (ai["Power"] <= high)]
        rnd_set = rnd[(rnd["Power"] >= low) & (rnd["Power"] <= high)]
        grid_set = grid[(grid["Power"] >= low) & (grid["Power"] <= high)]

        # Calculate Mean Uncovered
        # If no data, set to NaN
        val_ai = ai_set["Uncovered"].mean() if len(ai_set) > 0 else 0
        val_rnd = rnd_set["Uncovered"].mean() if len(rnd_set) > 0 else 0
        val_grid = grid_set["Uncovered"].mean() if len(grid_set) > 0 else 0

        data_points.append([label, val_ai, val_rnd, val_grid])

    df = pd.DataFrame(data_points, columns=["Energy Budget", "AI", "Random", "Grid"])

    # Save to CSV
    df.to_csv("coverage_efficiency.csv", index=False)

    fig = go.Figure(
        data=[
            go.Bar(name="AI", x=df["Energy Budget"], y=df["AI"], marker_color="blue"),
            go.Bar(
                name="Random",
                x=df["Energy Budget"],
                y=df["Random"],
                marker_color="gray",
            ),
            go.Bar(
                name="Grid", x=df["Energy Budget"], y=df["Grid"], marker_color="orange"
            ),
        ]
    )

    fig.update_layout(
        title="Coverage Efficiency at Fixed Energy Budgets",
        yaxis_title="Average Uncovered Sensors (Lower is Better)",
        barmode="group",
    )
    return fig


def save_interference_stats(ai, rnd, grid):
    """
    Save descriptive statistics for interference.
    """
    stats_data = []
    methods = {"AI": ai, "Random": rnd, "Grid": grid}

    for name, df in methods.items():
        data = df["Interference"]
        stats_data.append(
            [name, data.mean(), data.median(), data.std(), data.min(), data.max()]
        )

    df_stats = pd.DataFrame(
        stats_data, columns=["Method", "Mean", "Median", "StdDev", "Min", "Max"]
    )
    df_stats.to_csv("interference_stats.csv", index=False)


def save_energy_stats(ai, rnd, grid):
    """
    Save descriptive statistics for energy consumption.
    """
    stats_data = []
    methods = {"AI": ai, "Random": rnd, "Grid": grid}

    for name, df in methods.items():
        data = df["Power"]
        stats_data.append(
            [name, data.mean(), data.median(), data.std(), data.min(), data.max()]
        )

    df_stats = pd.DataFrame(
        stats_data, columns=["Method", "Mean", "Median", "StdDev", "Min", "Max"]
    )
    df_stats.to_csv("energy_stats.csv", index=False)


def main():
    print("Loading data...")
    ai, rnd, grid = load_data()

    # 1. Stats
    print("Calculating statistics...")
    report = analyze_significance(ai, rnd, grid)
    with open("stats_report.md", "w") as f:
        f.write(report)
    print("Saved stats_report.md")

    # 2. Energy Stats (New)
    print("Generating Energy Stats...")
    save_energy_stats(ai, rnd, grid)
    print("Saved energy_stats.csv")

    # 3. Interference Plot
    print("Generating Interference Plot...")
    fig_int = plot_interference_boxplot(ai, rnd, grid)
    fig_int.write_html("interference_boxplot.html")
    save_interference_stats(ai, rnd, grid)
    print("Saved interference_boxplot.html & interference_stats.csv")

    # 4. Coverage Bar Chart
    print("Generating Coverage Bar Chart...")
    fig_cov = plot_coverage_barchart(ai, rnd, grid)
    fig_cov.write_html("coverage_efficiency.html")
    print("Saved coverage_efficiency.html & coverage_efficiency.csv")

    print("Done.")


if __name__ == "__main__":
    main()
