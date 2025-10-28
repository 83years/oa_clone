"""
Matplotlib Themes for Clinical Flow Cytometry Gender Analysis
==============================================================

This module provides custom matplotlib themes that enforce the project style guide.
Apply these themes at the start of plotting scripts to ensure consistency.

Author: Lucas Black
Date: 2025-10-28
Version: 1.0
"""

import matplotlib.pyplot as plt
import matplotlib as mpl


# =============================================================================
# FIGURE DIMENSIONS
# =============================================================================

FIGURE_WIDTH = 13.33  # inches
FIGURE_HEIGHT = 7.5   # inches
FIGURE_DPI = 150

# Multi-panel figure dimensions
FIGURE_2x1_WIDTH = 13.33
FIGURE_2x1_HEIGHT = 7.5
FIGURE_1x2_WIDTH = 13.33
FIGURE_1x2_HEIGHT = 7.5
FIGURE_2x2_WIDTH = 13.33
FIGURE_2x2_HEIGHT = 7.5


# =============================================================================
# FONT SIZES
# =============================================================================

FONT_SIZE_AXIS_TITLE = 14
FONT_SIZE_AXIS_LABEL = 12
FONT_SIZE_LEGEND_TITLE = 12
FONT_SIZE_LEGEND_TEXT = 10
FONT_SIZE_PLOT_TITLE = 16
FONT_SIZE_ANNOTATION = 10
FONT_SIZE_PANEL_LABEL = 18


# =============================================================================
# PROJECT THEME
# =============================================================================

def set_project_theme():
    """
    Apply project-wide matplotlib theme.

    This sets all rcParams to match the style guide specifications.
    Call this at the start of any plotting script.

    Example
    -------
    >>> from themes import set_project_theme
    >>> set_project_theme()
    >>> fig, ax = plt.subplots()
    >>> # ... plotting code ...
    """

    # Font settings
    plt.rcParams['font.family'] = 'Arial'
    plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
    plt.rcParams['font.size'] = 12

    # Font sizes for specific elements
    plt.rcParams['axes.titlesize'] = FONT_SIZE_AXIS_TITLE
    plt.rcParams['axes.labelsize'] = FONT_SIZE_AXIS_TITLE
    plt.rcParams['axes.titleweight'] = 'bold'
    plt.rcParams['axes.labelweight'] = 'bold'

    plt.rcParams['xtick.labelsize'] = FONT_SIZE_AXIS_LABEL
    plt.rcParams['ytick.labelsize'] = FONT_SIZE_AXIS_LABEL

    plt.rcParams['legend.fontsize'] = FONT_SIZE_LEGEND_TEXT
    plt.rcParams['legend.title_fontsize'] = FONT_SIZE_LEGEND_TITLE

    plt.rcParams['figure.titlesize'] = FONT_SIZE_PLOT_TITLE
    plt.rcParams['figure.titleweight'] = 'bold'

    # Figure settings
    plt.rcParams['figure.figsize'] = (FIGURE_WIDTH, FIGURE_HEIGHT)
    plt.rcParams['figure.dpi'] = FIGURE_DPI
    plt.rcParams['savefig.dpi'] = FIGURE_DPI
    plt.rcParams['savefig.bbox'] = 'tight'

    # Axes settings
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.spines.right'] = False
    plt.rcParams['axes.linewidth'] = 1.0
    plt.rcParams['axes.edgecolor'] = 'black'

    # Grid settings
    plt.rcParams['axes.grid'] = False  # Enable per-plot as needed
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['grid.linestyle'] = '--'
    plt.rcParams['grid.linewidth'] = 0.5

    # Legend settings
    plt.rcParams['legend.frameon'] = True
    plt.rcParams['legend.framealpha'] = 0.8
    plt.rcParams['legend.edgecolor'] = '#CCCCCC'
    plt.rcParams['legend.fancybox'] = True

    # Line and marker settings
    plt.rcParams['lines.linewidth'] = 1.5
    plt.rcParams['lines.markersize'] = 6

    # Save settings
    plt.rcParams['savefig.format'] = 'png'
    plt.rcParams['savefig.transparent'] = False
    plt.rcParams['savefig.facecolor'] = 'white'

    print("Project theme applied successfully.")


def reset_theme():
    """
    Reset matplotlib to default settings.
    """
    mpl.rcdefaults()
    print("Matplotlib reset to defaults.")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_figure(nrows=1, ncols=1, **kwargs):
    """
    Create a figure with project defaults.

    Parameters
    ----------
    nrows : int, optional
        Number of subplot rows (default: 1)
    ncols : int, optional
        Number of subplot columns (default: 1)
    **kwargs
        Additional arguments passed to plt.subplots()

    Returns
    -------
    fig, ax or axes
        Matplotlib figure and axis/axes objects

    Example
    -------
    >>> fig, ax = create_figure()
    >>> fig, axes = create_figure(2, 2)
    """
    # Set default figsize if not provided
    if 'figsize' not in kwargs:
        kwargs['figsize'] = (FIGURE_WIDTH, FIGURE_HEIGHT)

    if 'dpi' not in kwargs:
        kwargs['dpi'] = FIGURE_DPI

    fig, ax = plt.subplots(nrows, ncols, **kwargs)
    return fig, ax


def save_figure(fig, filename, dpi=None, formats=['png', 'pdf']):
    """
    Save figure in multiple formats following project standards.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure to save
    filename : str
        Base filename (without extension)
    dpi : int, optional
        Resolution (default: uses project DPI)
    formats : list of str, optional
        List of formats to save (default: ['png', 'pdf'])

    Example
    -------
    >>> save_figure(fig, 'figures/fig1_corpus_overview_v1')
    # Saves fig1_corpus_overview_v1.png and fig1_corpus_overview_v1.pdf
    """
    if dpi is None:
        dpi = FIGURE_DPI

    for fmt in formats:
        output_path = f"{filename}.{fmt}"
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
        print(f"Saved: {output_path}")


def add_panel_label(ax, label, x=0.02, y=0.98, **kwargs):
    """
    Add panel label (A, B, C, D) to subplot.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axis to add label to
    label : str
        Panel label (e.g., 'A', 'B', 'C')
    x : float, optional
        X position in axis coordinates (default: 0.02)
    y : float, optional
        Y position in axis coordinates (default: 0.98)
    **kwargs
        Additional text properties

    Example
    -------
    >>> fig, axes = create_figure(1, 2)
    >>> add_panel_label(axes[0], 'A')
    >>> add_panel_label(axes[1], 'B')
    """
    default_kwargs = {
        'fontsize': FONT_SIZE_PANEL_LABEL,
        'fontweight': 'bold',
        'va': 'top',
        'ha': 'left',
        'transform': ax.transAxes
    }
    default_kwargs.update(kwargs)

    ax.text(x, y, label, **default_kwargs)


def add_sample_size_text(ax, text, x=0.5, y=0.95, **kwargs):
    """
    Add sample size text to plot.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axis to add text to
    text : str
        Sample size text (e.g., 'F: n = 120,000 | M: n = 150,000')
    x : float, optional
        X position in axis coordinates (default: 0.5, centered)
    y : float, optional
        Y position in axis coordinates (default: 0.95)
    **kwargs
        Additional text properties

    Example
    -------
    >>> add_sample_size_text(ax, 'F: n = 120,000 | M: n = 150,000')
    """
    default_kwargs = {
        'fontsize': FONT_SIZE_ANNOTATION,
        'style': 'italic',
        'color': '#4B5563',
        'ha': 'center',
        'va': 'top',
        'transform': ax.transAxes
    }
    default_kwargs.update(kwargs)

    ax.text(x, y, text, **default_kwargs)


def add_significance_bracket(ax, x1, x2, y, text, **kwargs):
    """
    Add significance bracket with star notation.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axis to add bracket to
    x1 : float
        X position of left end of bracket (data coordinates)
    x2 : float
        X position of right end of bracket (data coordinates)
    y : float
        Y position of bracket (data coordinates)
    text : str
        Significance text (e.g., '***', '**', '*', 'ns')
    **kwargs
        Additional line/text properties

    Example
    -------
    >>> add_significance_bracket(ax, 0, 1, ymax*1.05, '***')
    """
    # Draw bracket
    ax.plot([x1, x2], [y, y], 'k-', linewidth=1)

    # Add text
    text_kwargs = {
        'fontsize': FONT_SIZE_ANNOTATION,
        'ha': 'center',
        'va': 'bottom'
    }
    text_kwargs.update(kwargs)

    ax.text((x1 + x2) / 2, y, text, **text_kwargs)


def enable_grid(ax, axis='y'):
    """
    Enable grid on axis following project style.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axis to enable grid on
    axis : {'both', 'x', 'y'}, optional
        Which axis to apply grid to (default: 'y')

    Example
    -------
    >>> enable_grid(ax, axis='y')
    """
    ax.grid(axis=axis, alpha=0.3, linestyle='--', linewidth=0.5)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Demonstrate theme application
    set_project_theme()

    # Create a simple example plot
    fig, ax = create_figure()

    # Example data
    categories = ['Female', 'Male']
    values = [12.4, 15.1]

    ax.bar(categories, values, color=['#6a00ff', '#FCA63F'])
    ax.set_xlabel('Inferred Gender')
    ax.set_ylabel('Mean Degree Centrality')
    ax.set_title('Example Plot with Project Theme')

    # Add sample size
    add_sample_size_text(ax, 'F: n = 120,000 | M: n = 150,000')

    # Add significance bracket
    add_significance_bracket(ax, 0, 1, max(values) * 1.1, '***')

    # Enable grid
    enable_grid(ax, axis='y')

    # Save figure
    save_figure(fig, 'example_plot_with_theme')

    plt.show()

    print("\nExample plot created successfully!")
    print("Check example_plot_with_theme.png and example_plot_with_theme.pdf")
