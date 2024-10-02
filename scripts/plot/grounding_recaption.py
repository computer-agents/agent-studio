import matplotlib
import numpy as np
import seaborn as sns
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

matplotlib.rcParams["font.family"] = "Helvetica"
matplotlib.rcParams["mathtext.fontset"] = "cm"


def plot_match(data):
    pdf = PdfPages("figures/recaption.pdf")
    sns_colors = sns.color_palette("Paired", 8)
    alpha = 0.5

    # Extracting data for plotting
    names = []
    raw_scores = []
    recaptioned_scores = []
    for k, v in data.items():
        if k == "gpt-4o":
            names.append("GPT-4o")
        elif k == "CogVLM2-Llama3-chat-19B":
            names.append("CogVLM2")
        elif k == "SeeClick":
            names.append("SeeClick")
        else:
            continue
        raw_scores.append(v["raw"])
        recaptioned_scores.append(v["recaptioned"])

    # Creating the plot
    fig, ax = plt.subplots(figsize=(8, 6.5))

    index = np.arange(len(names))
    bar_width = 0.35

    ax.bar(
        index - bar_width / 2,
        raw_scores,
        bar_width,
        label="Raw Instructions",
        color=sns_colors[0],
        alpha=alpha,
    )
    ax.bar(
        index + bar_width / 2,
        recaptioned_scores,
        bar_width,
        label="Recaptioned",
        color=sns_colors[1],
        alpha=alpha,
    )

    # ax.set_xlabel("Model", fontsize=31)
    # ax.set_ylabel("Scores", fontsize=31)
    # ax.set_title("Raw Instructions vs Recaptioned", fontsize=33, pad=20)

    ax.set_xticks(index)
    ax.set_xticklabels(names, ha="center", fontsize=28, fontweight="bold")
    ax.tick_params(axis="x", length=10, color="grey")
    ax.tick_params(axis="y", length=10, color="grey")
    ax.legend(loc="upper right", fontsize=28)

    # plt.yticks(fontsize=30, fontweight="bold")
    locs = [0.0, 0.2, 0.4, 0.6]
    plt.yticks(
        locs,
        [r"$%d$" % loc for loc in [0, 20, 40, 60]],
        fontsize=30,
        fontweight="bold",
    )

    plt.tight_layout()
    plt.show()
    pdf.savefig(fig)
    pdf.close()


# Example data
data = {
    "SeeClick": {"raw": 0.460, "recaptioned": 0.611},
    "gpt-4o": {"raw": 0.125, "recaptioned": 0.134},
    "CogVLM2-Llama3-chat-19B": {"raw": 0.035, "recaptioned": 0.034},
}

plot_match(data)
