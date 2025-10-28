"""
Plot Templates for Clinical Flow Cytometry Gender Analysis
==========================================================

This module provides template functions for common plot types used in the project.
All templates follow the project style guide specifications.

Author: Lucas Black
Date: 2025-10-28
Version: 1.0
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy import stats

from color_palettes import GENDER_COLORS, GENDER_ORDER
from themes import (set_project_theme, create_figure, save_figure,
                    add_sample_size_text, add_significance_bracket, enable_grid)


# =============================================================================
# GENDER COMPARISON PLOTS
# =============================================================================

def plot_gender_comparison_violin(
    data: pd.DataFrame,
    metric: str,
    metric_label: str = None,
    title: str = None,
    filename: str = None,
    show_plot: bool = False
):
    """
    Create violin plot comparing female and male authors on a metric.

    This is the primary plot type for H1, H2, H3, and H6 analyses.

    Parameters
    ----------
    data : pd.DataFrame
        Must contain columns: 'gender', metric
        'gender' must be 'F', 'M', or 'Unknown'
    metric : str
        Column name of metric to compare (e.g., 'degree_centrality')
    metric_label : str, optional
        Y-axis label (defaults to metric name, title case)
    title : str, optional
        Plot title (default: no title)
    filename : str, optional
        If provided, save to this path (without extension)
    show_plot : bool, optional
        Whether to display the plot (default: False)

    Returns
    -------
    fig : matplotlib.figure.Figure
        The created figure object

    Example
    -------
    >>> data = pd.DataFrame({
    ...     'gender': ['F', 'M', 'F', 'M', ...],
    ...     'degree_centrality': [12.4, 15.1, 10.2, 16.3, ...]
    ... })
    >>> fig = plot_gender_comparison_violin(
    ...     data,
    ...     metric='degree_centrality',
    ...     metric_label='Degree Centrality',
    ...     filename='figures/fig2_gender_degree_v1'
    ... )
    """

    # Ensure theme is applied
    set_project_theme()

    # Filter to F and M only (exclude Unknown for comparison)
    plot_data = data[data['gender'].isin(['F', 'M'])].copy()

    if len(plot_data) == 0:
        raise ValueError("No data with gender 'F' or 'M' found")

    # Calculate statistics
    stats_dict = {}
    for gender in ['F', 'M']:
        gender_data = plot_data[plot_data['gender'] == gender][metric]
        if len(gender_data) == 0:
            raise ValueError(f"No data for gender '{gender}'")
        stats_dict[gender] = {
            'n': len(gender_data),
            'mean': gender_data.mean(),
            'std': gender_data.std()
        }

    # T-test
    f_vals = plot_data[plot_data['gender'] == 'F'][metric].dropna()
    m_vals = plot_data[plot_data['gender'] == 'M'][metric].dropna()
    t_stat, p_val = stats.ttest_ind(f_vals, m_vals)

    # Cohen's d
    pooled_std = np.sqrt((stats_dict['F']['std']**2 + stats_dict['M']['std']**2) / 2)
    cohens_d = (stats_dict['M']['mean'] - stats_dict['F']['mean']) / pooled_std

    # Significance marker
    if p_val < 0.001:
        sig_marker = '***'
    elif p_val < 0.01:
        sig_marker = '**'
    elif p_val < 0.05:
        sig_marker = '*'
    else:
        sig_marker = 'ns'

    # Create figure
    fig, ax = create_figure()

    # Violin plot (F first, M second - alphabetical order)
    parts = ax.violinplot(
        [f_vals, m_vals],
        positions=[0, 1],
        widths=0.7,
        showmeans=False,
        showmedians=False,
        showextrema=False
    )

    # Color violins (F = purple, M = orange)
    for i, gender in enumerate(['F', 'M']):
        parts['bodies'][i].set_facecolor(GENDER_COLORS[gender])
        parts['bodies'][i].set_alpha(0.7)
        parts['bodies'][i].set_edgecolor('black')
        parts['bodies'][i].set_linewidth(1)

    # Overlay boxplots
    bp = ax.boxplot(
        [f_vals, m_vals],
        positions=[0, 1],
        widths=0.3,
        showfliers=False,
        patch_artist=True,
        boxprops=dict(facecolor='white', alpha=0.8),
        medianprops=dict(color='black', linewidth=2),
        whiskerprops=dict(color='black', linewidth=1),
        capprops=dict(color='black', linewidth=1)
    )

    # X-axis (F first, M second - alphabetical)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['Female', 'Male'], fontsize=12)
    ax.set_xlabel('Inferred Gender', fontsize=14, fontweight='bold')

    # Y-axis
    if metric_label is None:
        metric_label = metric.replace('_', ' ').title()
    ax.set_ylabel(metric_label, fontsize=14, fontweight='bold')
    ax.tick_params(axis='y', labelsize=12)

    # Sample sizes and stats (F first - alphabetical)
    sample_text = f"F: n = {stats_dict['F']['n']:,} | M: n = {stats_dict['M']['n']:,}"
    stats_text = (f"F: {stats_dict['F']['mean']:.2f} ± {stats_dict['F']['std']:.2f} | "
                  f"M: {stats_dict['M']['mean']:.2f} ± {stats_dict['M']['std']:.2f}")

    ax.text(0.5, 0.98, sample_text, transform=ax.transAxes,
            ha='center', va='top', fontsize=10, style='italic', color='#4B5563')
    ax.text(0.5, 0.94, stats_text, transform=ax.transAxes,
            ha='center', va='top', fontsize=10, color='#4B5563')

    # Significance bracket
    ymax = plot_data[metric].max()
    bracket_y = ymax * 1.05
    ax.plot([0, 1], [bracket_y, bracket_y], 'k-', linewidth=1)
    ax.text(0.5, bracket_y * 1.02, sig_marker, ha='center', fontsize=10)

    # Legend
    legend_text = f"* p < 0.05, ** p < 0.01, *** p < 0.001\nCohen's d = {cohens_d:.3f}"
    ax.text(0.98, 0.02, legend_text, transform=ax.transAxes,
            ha='right', va='bottom', fontsize=9, color='#4B5563',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # Title (if provided)
    if title:
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)

    # Clean up
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    enable_grid(ax, axis='y')

    plt.tight_layout()

    # Save if filename provided
    if filename:
        save_figure(fig, filename)

    # Show if requested
    if show_plot:
        plt.show()
    else:
        plt.close(fig)

    return fig


# =============================================================================
# TEMPORAL TREND PLOTS
# =============================================================================

def plot_temporal_trends_lines(
    data: pd.DataFrame,
    time_var: str,
    metric_var: str,
    metric_label: str = None,
    title: str = None,
    filename: str = None,
    show_plot: bool = False
):
    """
    Create line plot showing temporal trends by gender.

    Used for H4 (temporal trends in gender equity).

    Parameters
    ----------
    data : pd.DataFrame
        Must contain columns: time_var, 'gender', metric_var
    time_var : str
        Name of time variable (e.g., 'year', 'period')
    metric_var : str
        Name of metric to plot (e.g., 'degree_centrality')
    metric_label : str, optional
        Y-axis label
    title : str, optional
        Plot title
    filename : str, optional
        Save path (without extension)
    show_plot : bool, optional
        Whether to display the plot

    Returns
    -------
    fig : matplotlib.figure.Figure

    Example
    -------
    >>> fig = plot_temporal_trends_lines(
    ...     data,
    ...     time_var='year',
    ...     metric_var='degree_centrality',
    ...     filename='figures/fig4_temporal_trends_v1'
    ... )
    """

    set_project_theme()

    # Filter to F and M only
    plot_data = data[data['gender'].isin(['F', 'M'])].copy()

    # Aggregate by time and gender
    agg_data = plot_data.groupby([time_var, 'gender'])[metric_var].agg([
        ('mean', 'mean'),
        ('std', 'std'),
        ('n', 'count')
    ]).reset_index()

    # Calculate 95% CI
    agg_data['se'] = agg_data['std'] / np.sqrt(agg_data['n'])
    agg_data['ci_lower'] = agg_data['mean'] - 1.96 * agg_data['se']
    agg_data['ci_upper'] = agg_data['mean'] + 1.96 * agg_data['se']

    # Create figure
    fig, ax = create_figure()

    # Plot for each gender (F first - alphabetical)
    for gender in ['F', 'M']:
        gender_data = agg_data[agg_data['gender'] == gender]

        # Line with confidence ribbon
        ax.plot(gender_data[time_var], gender_data['mean'],
                color=GENDER_COLORS[gender], linewidth=2,
                label='Female' if gender == 'F' else 'Male')

        ax.fill_between(gender_data[time_var],
                        gender_data['ci_lower'],
                        gender_data['ci_upper'],
                        color=GENDER_COLORS[gender], alpha=0.2)

        # Points
        ax.scatter(gender_data[time_var], gender_data['mean'],
                   color=GENDER_COLORS[gender], s=50, zorder=5,
                   edgecolors='white', linewidth=1.5)

    # Labels
    time_label = time_var.replace('_', ' ').title()
    ax.set_xlabel(time_label, fontsize=14, fontweight='bold')

    if metric_label is None:
        metric_label = metric_var.replace('_', ' ').title()
    ax.set_ylabel(metric_label, fontsize=14, fontweight='bold')

    # Legend
    ax.legend(title='Inferred Gender', fontsize=10, title_fontsize=12,
              loc='best', frameon=True, framealpha=0.9)

    # Title
    if title:
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)

    # Grid
    enable_grid(ax, axis='y')

    # Clean up
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()

    # Save
    if filename:
        save_figure(fig, filename)

    if show_plot:
        plt.show()
    else:
        plt.close(fig)

    return fig


# =============================================================================
# ADDITIONAL PLOT TEMPLATES
# =============================================================================

# TODO: Add more templates as needed:
# - Forest plots (regression coefficients)
# - Effect plots (predicted values)
# - Scatter plots (institutional stratification)
# - Heatmaps (cluster profiles)
# - Network visualizations (ego networks)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Create example data
    np.random.seed(428)

    n_female = 120000
    n_male = 150000

    example_data = pd.DataFrame({
        'gender': ['F'] * n_female + ['M'] * n_male,
        'degree_centrality': (
            list(np.random.normal(12.4, 8.2, n_female)) +
            list(np.random.normal(15.1, 9.7, n_male))
        )
    })

    # Test gender comparison violin plot
    print("Creating example gender comparison violin plot...")
    fig = plot_gender_comparison_violin(
        example_data,
        metric='degree_centrality',
        metric_label='Degree Centrality',
        title='Example: Gender Differences in Network Centrality',
        filename='figures/example_gender_violin',
        show_plot=True
    )

    print("\nExample plot created successfully!")
    print("Check figures/example_gender_violin.png and .pdf")

    # Create example temporal data
    years = list(range(2000, 2025))
    temporal_data = []

    for year in years:
        for gender in ['F', 'M']:
            # Simulate convergence over time
            base_f = 12.0
            base_m = 15.0
            convergence = (year - 2000) * 0.1  # Gender gap closes over time

            if gender == 'F':
                mean_val = base_f + convergence + np.random.normal(0, 0.5)
            else:
                mean_val = base_m - convergence * 0.5 + np.random.normal(0, 0.5)

            n_authors = np.random.randint(3000, 5000)

            for _ in range(n_authors):
                temporal_data.append({
                    'year': year,
                    'gender': gender,
                    'degree_centrality': np.random.normal(mean_val, 3)
                })

    temporal_df = pd.DataFrame(temporal_data)

    # Test temporal trends plot
    print("\nCreating example temporal trends plot...")
    fig2 = plot_temporal_trends_lines(
        temporal_df,
        time_var='year',
        metric_var='degree_centrality',
        metric_label='Degree Centrality',
        title='Example: Gender Gap Convergence Over Time',
        filename='figures/example_temporal_trends',
        show_plot=True
    )

    print("\nTemporal trends plot created successfully!")
    print("Check figures/example_temporal_trends.png and .pdf")
