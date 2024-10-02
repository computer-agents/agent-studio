import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages

matplotlib.rcParams["font.family"] = "Helvetica"
matplotlib.rcParams["mathtext.fontset"] = "cm"

# Initialize counters for source and platform
platform_counts = {
    "Single-API": {
        "OS": 19,
        "Gmail": 13,
        "Google Calendar": 11,
        "Google Docs": 7,
    },
    "Single-GUI": {
        "VSCode": 20,
        "OS": 19,
        "Docs": 15,
        "Spreadsheet": 15,
        "Slides": 15,
        "Image Editor": 11,
    },
    "Compositional": {"Mix": 60},
}

# Prepare data for the nested pie chart
inner_labels = ["Single-API", "Single-GUI", "Compositional"]
inner_sizes = [sum(platform_counts[platform].values()) for platform in inner_labels]

outer_labels = [
    "OS",
    "Email",
    "Calendar",
    "Docs",
    "VS\nCode",
    "OS",
    "Docs",
    "Spread-\nsheet",
    "Slides",
    "Image\nEditor",
    "Mix",
]
outer_sizes = [19, 13, 11, 7, 20, 19, 15, 15, 15, 11, 60]

# Define colors
# base_colors = ['#6CA0DC', '#6CC24A', '#E94D44']  # Blue, Green, Red
raw_sns_colors = sns.color_palette("Paired", 6)
base_colors = [raw_sns_colors[0], raw_sns_colors[2], raw_sns_colors[4]]

# Define lighter shades for outer rings using alpha values (in descending order)
outer_colors_single_api = [
    matplotlib.colors.to_rgba(base_colors[0], alpha) for alpha in [0.8, 0.6, 0.4, 0.2]
]
outer_colors_single_gui = [
    matplotlib.colors.to_rgba(base_colors[1], alpha)
    for alpha in [0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
]
outer_colors_compositional = [
    matplotlib.colors.to_rgba(base_colors[2], 0.6)
]  # Single compositional section
outer_colors = (
    outer_colors_single_api + outer_colors_single_gui + outer_colors_compositional
)

# Inner ring uses solid base colors
inner_colors = base_colors

# Create figure and axis
fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(aspect="equal"))

# Create the inner ring (platforms)
inner_wedges, inner_texts = ax.pie(
    inner_sizes,
    radius=0.6,
    colors=inner_colors,
    wedgeprops=dict(width=0.15, edgecolor="w"),
)

# Create the outer ring (sources)
outer_wedges, outer_texts = ax.pie(
    outer_sizes,
    radius=0.85,
    colors=outer_colors,
    wedgeprops=dict(width=0.25, edgecolor="w"),
)

# Calculate total for outer percentages
total_outer = sum(outer_sizes)

# Annotate the outer ring (sources) with percentages
for i, wedge in enumerate(outer_wedges):
    # Get the angle in the center of the wedge
    theta = (wedge.theta2 + wedge.theta1) / 2.0
    scale_factor = 0.72
    x = scale_factor * np.cos(np.deg2rad(theta))  # Convert from degrees to radians
    y = scale_factor * np.sin(np.deg2rad(theta))
    if "Calendar" in outer_labels[i]:
        x += 0.015
        y -= 0.015
    if "sheet" in outer_labels[i]:
        x -= 0.01
    if "Image" in outer_labels[i]:
        x += 0.01
        y -= 0.01

    percentage = outer_sizes[i] / total_outer * 100
    label = f"{outer_labels[i]}\n{percentage:.1f}%"
    ax.annotate(
        label,
        xy=(x, y),
        xytext=(x, y),
        fontsize=20,
        horizontalalignment="center",
        verticalalignment="center",
    )

# Annotate the inner ring
for i, wedge in enumerate(inner_wedges):
    theta = (wedge.theta2 + wedge.theta1) / 2.0
    scale_factor = 0.26
    x = scale_factor * np.cos(np.deg2rad(theta))  # Convert from degrees to radians
    y = scale_factor * np.sin(np.deg2rad(theta))

    ax.annotate(
        inner_labels[i],
        xy=(x, y),
        xytext=(x, y),
        fontsize=24,
        horizontalalignment="center",
        verticalalignment="center",
    )

# crop empty side
plt.xlim(-0.85, 0.85)
plt.ylim(-0.85, 0.85)

# Save the figure to a PDF
plt.tight_layout()
plt.show()
pdf = PdfPages("figures/benchmark_stats.pdf")
pdf.savefig(fig)
pdf.close()
