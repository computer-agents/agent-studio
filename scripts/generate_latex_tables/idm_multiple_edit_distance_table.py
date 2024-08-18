from bs4 import BeautifulSoup


# Function to parse the HTML file and extract edit distance metrics
def parse_edit_distances(file_path):
    with open(file_path, "r") as file:
        soup = BeautifulSoup(file, "html.parser")

        # Find the metric table
        table = soup.find("table")
        rows = table.find_all("tr")

        # Extract relevant edit distances into a dictionary
        edit_distances = {}
        for row in rows[1:]:  # Skip header row
            cells = row.find_all("td")
            metric_name = cells[0].get_text(strip=True)
            if "edit_distance" in metric_name:
                metric_value = cells[1].get_text(strip=True)
                edit_distances[metric_name] = float(metric_value)

        return edit_distances


# Function to format the LaTeX table with edit distances
def format_edit_distance_table(models, edit_distances):
    header = r"""
\begin{tabular}{c|ccccc}
\hline
\textbf{Model} & \textbf{Mind2Web} & \textbf{AITW} & \textbf{VWA} & \textbf{AgentStudio} & \textbf{Total} \\
\hline
"""  # noqa: E501
    footer = r"\hline" + "\n" + r"\end{tabular}"

    # Sort models by total edit distance
    sorted_models = sorted(
        models, key=lambda model: edit_distances.get(model, {}).get("edit_distance")
    )

    # Find minimum values for each column
    mind2web_min = min(
        float(f"{edit_distances[model].get('mind2web_edit_distance'):.1f}")
        for model in models
    )
    aitw_min = min(
        float(f"{edit_distances[model].get('aitw_edit_distance'):.1f}")
        for model in models
    )
    vwa_min = min(
        float(f"{edit_distances[model].get('vwa_edit_distance'):.1f}")
        for model in models
    )
    agent_studio_min = min(
        float(f"{edit_distances[model].get('agent_studio_edit_distance'):.1f}")
        for model in models
    )
    total_min = min(
        float(f"{edit_distances[model].get('edit_distance'):.1f}") for model in models
    )

    rows = []
    for model in sorted_models:
        distances = edit_distances.get(model, {})

        mind2web_value = f"{distances.get('mind2web_edit_distance', float('nan')):.1f}"
        aitw_value = f"{distances.get('aitw_edit_distance', float('nan')):.1f}"
        vwa_value = f"{distances.get('vwa_edit_distance', float('nan')):.1f}"
        agent_studio_value = (
            f"{distances.get('agent_studio_edit_distance', float('nan')):.1f}"
        )
        total_value = f"{distances.get('edit_distance', float('nan')):.1f}"

        # Bold the minimum values
        if float(mind2web_value) == mind2web_min:
            mind2web_value = f"\\textbf{{{mind2web_value}}}"
        if float(aitw_value) == aitw_min:
            aitw_value = f"\\textbf{{{aitw_value}}}"
        if float(vwa_value) == vwa_min:
            vwa_value = f"\\textbf{{{vwa_value}}}"
        if float(agent_studio_value) == agent_studio_min:
            agent_studio_value = f"\\textbf{{{agent_studio_value}}}"
        if float(total_value) == total_min:
            total_value = f"\\textbf{{{total_value}}}"

        row = f"{model} & {mind2web_value} & {aitw_value} & {vwa_value} & {agent_studio_value} & {total_value} \\\\"  # noqa: E501
        rows.append(row)

    return header + "\n".join(rows) + "\n" + footer


# Define paths to your n2n HTML files
n2n_files = {
    "Claude 3.5 Sonnet": "results/idmn2n/claude-3-5-sonnet-20240620.html",
    "Gemini 1.5 Flash": "results/idmn2n/gemini-1.5-flash-001.html",
    "Gemini 1.5 Pro": "results/idmn2n/gemini-1.5-pro-001.html",
    "GPT-4o (0513)": "results/idmn2n/gpt-4o-2024-05-13.html",
    "Qwen-VL-Chat": "results/idmn2n/Qwen-VL-Chat.html",
}

# Extract edit distances from the n2n HTML files
edit_distances = {
    model: parse_edit_distances(file) for model, file in n2n_files.items()
}

# Generate LaTeX table
latex_table = format_edit_distance_table(n2n_files.keys(), edit_distances)

# Print or save the LaTeX table
print(latex_table)
