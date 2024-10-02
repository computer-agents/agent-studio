import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages

matplotlib.rcParams["font.family"] = "Helvetica"
matplotlib.rcParams["mathtext.fontset"] = "cm"

# Data
domains = ["Web", "Desktop", "Mobile"]
domain_sizes = [400, 300, 300]

datasets = [
    "Mind2Web\n(test domain)",
    "Mind2Web\n(test task)",
    "OmniACT",
    "Mind2Web\n(test website)",
    "ScreenSpot",
    "OmniACT",
    "ScreenSpot",
    "AgentStudio",
    "MoTIF",
    "ScreenSpot",
]

dataset_sizes = [
    191,
    80,
    77,
    38,
    14,
    243,
    33,
    24,
    265,
    35,
]

# Define colors for the inner and outer rings
raw_sns_colors = sns.color_palette("Paired", 6)
base_colors = [raw_sns_colors[0], raw_sns_colors[2], raw_sns_colors[4]]

# Define lighter shades for outer rings using alpha values (descending order)
outer_colors_web = [
    matplotlib.colors.to_rgba(base_colors[0], alpha)
    for alpha in [0.8, 0.6, 0.4, 0.2, 0.1]
]
outer_colors_desktop = [
    matplotlib.colors.to_rgba(base_colors[1], alpha) for alpha in [0.8, 0.6, 0.4]
]
outer_colors_mobile = [
    matplotlib.colors.to_rgba(base_colors[2], alpha) for alpha in [0.8, 0.6]
]
outer_colors = outer_colors_web + outer_colors_desktop + outer_colors_mobile

# Inner ring uses solid base colors
inner_colors = base_colors

# Create figure and axis
fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(aspect="equal"))

# Create the inner ring (domains)
inner_wedges, inner_texts = ax.pie(
    domain_sizes,
    radius=0.4,
    colors=inner_colors,
    wedgeprops=dict(width=0.05, edgecolor="w"),
)

# Create the outer ring (datasets)
outer_wedges, outer_texts = ax.pie(
    dataset_sizes,
    radius=0.5,
    colors=outer_colors,
    wedgeprops=dict(width=0.1, edgecolor="w"),
)

# Calculate total for outer percentages
total_outer = sum(dataset_sizes)

# Annotate the outer ring (datasets) manually with percentages and lines
# for i, (x, y) in enumerate(outer_positions):
for i, wedge in enumerate(outer_wedges):
    # Get the angle in the center of the wedge
    theta = (wedge.theta2 + wedge.theta1) / 2.0
    scale_factor = 0.66
    x = scale_factor * np.cos(np.deg2rad(theta))  # Convert from degrees to radians
    y = scale_factor * np.sin(np.deg2rad(theta))

    percentage = dataset_sizes[i] / total_outer * 100
    label = f"{datasets[i]}\n{percentage:.1f}%"

    if "test task" in label:
        y -= 0.08
    if "MoTIF" in label:
        y += 0.07
    if "7.7" in label:
        x += 0.02
        y -= 0.07
    if "ScreenSpot\n1.4" in label:
        x -= 0.03
        y -= 0.1
    if "ScreenSpot\n3.3" in label:
        x -= 0.06
        y += 0.1
    if "AgentStudio" in label:
        x += 0.005
        y += 0.075
    if "OmniACT\n24" in label:
        x += 0.04
    if "test website" in label:
        x += 0.02
        y -= 0.04

    ax.annotate(
        label,
        xy=(x, y),
        xytext=(x, y),
        fontsize=12,
        horizontalalignment="center",
        verticalalignment="center",
    )

# Annotate the inner ring (domains)
for i, wedge in enumerate(inner_wedges):
    theta = (wedge.theta2 + wedge.theta1) / 2.0
    scale_factor = 0.27
    x = scale_factor * np.cos(np.deg2rad(theta))  # Convert from degrees to radians
    y = scale_factor * np.sin(np.deg2rad(theta))
    if "Desktop" in domains[i]:
        x += 0.07

    ax.annotate(
        domains[i],
        xy=(x, y),
        xytext=(x, y),
        fontsize=16,
        horizontalalignment="center",
        verticalalignment="center",
    )

# crop empty side
plt.xlim(-0.7, 0.7)
plt.ylim(-0.7, 0.7)

# Save the figure to a PDF
plt.tight_layout()
plt.show()

pdf = PdfPages("figures/grounding_stats.pdf")
pdf.savefig(fig)
pdf.close()
