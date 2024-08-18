from bs4 import BeautifulSoup


# Function to parse the HTML file and extract relevant metrics
def parse_html(file_path):
    with open(file_path, "r") as file:
        soup = BeautifulSoup(file, "html.parser")

        # Find the metric table
        table = soup.find("table")
        rows = table.find_all("tr")

        # Extract metrics into a dictionary
        metrics = {}
        for row in rows[1:]:  # Skip header row
            cells = row.find_all("td")
            metric_name = cells[0].get_text(strip=True)
            metric_value = cells[1].get_text(strip=True)
            metrics[metric_name] = metric_value

        return metrics


# Function to format the LaTeX table with bold maximum values and sorted rows
def format_latex_table(models, idm_single, idm_multiple):
    # Prepare data for sorting
    table_data = []
    for model in models:
        single = idm_single.get(model, {})
        multiple = idm_multiple.get(model, {})
        table_data.append(
            {
                "model": model,
                "single_mind2web": float(single.get("mind2web_score", "0.0")) * 100,
                "single_aitw": float(single.get("aitw_score", "0.0")) * 100,
                "single_vwa": float(single.get("vwa_score", "0.0")) * 100,
                "single_agent_studio": float(single.get("agent_studio_score", "0.0"))
                * 100,
                "single_total": float(single.get("Score", "0.0")) * 100,
                "multiple_mind2web": float(multiple.get("mind2web_score", "0.0")) * 100,
                "multiple_aitw": float(multiple.get("aitw_score", "0.0")) * 100,
                "multiple_vwa": float(multiple.get("vwa_score", "0.0")) * 100,
                "multiple_agent_studio": float(
                    multiple.get("agent_studio_score", "0.0")
                )
                * 100,
                "multiple_total": float(multiple.get("Score", "0.0")) * 100,
            }
        )

    # Sort by total score
    table_data.sort(key=lambda x: x["single_total"], reverse=True)
    single_sorted = table_data.copy()
    table_data.sort(key=lambda x: x["multiple_total"], reverse=True)

    # Find maximum values for each column
    max_values = {}
    for key in [
        "single_mind2web",
        "single_aitw",
        "single_vwa",
        "single_agent_studio",
        "single_total",
        "multiple_mind2web",
        "multiple_aitw",
        "multiple_vwa",
        "multiple_agent_studio",
        "multiple_total",
    ]:
        max_values[key] = max(item[key] for item in table_data)

    # Build LaTeX table rows
    def format_row(data):
        def format_cell(value, max_value):
            return (
                r"\textbf{" + f"{value:.1f}" + "}"
                if value == max_value
                else f"{value:.1f}"
            )

        return (
            f"{data['model']} & "
            f"{format_cell(data['single_mind2web'], max_values['single_mind2web'])} & "
            f"{format_cell(data['single_aitw'], max_values['single_aitw'])} & "
            f"{format_cell(data['single_vwa'], max_values['single_vwa'])} & "
            f"{format_cell(data['single_agent_studio'], max_values['single_agent_studio'])} & "  # noqa: E501
            f"{format_cell(data['single_total'], max_values['single_total'])} & "
            f"{format_cell(data['multiple_mind2web'], max_values['multiple_mind2web'])} & "  # noqa: E501
            f"{format_cell(data['multiple_aitw'], max_values['multiple_aitw'])} & "
            f"{format_cell(data['multiple_vwa'], max_values['multiple_vwa'])} & "
            f"{format_cell(data['multiple_agent_studio'], max_values['multiple_agent_studio'])} & "  # noqa: E501
            f"{format_cell(data['multiple_total'], max_values['multiple_total'])} \\\\"
        )

    rows = [format_row(data) for data in single_sorted]

    return "\n".join(rows) + "\n"


def format_latex_single_table(models, idm_single):
    # Prepare data for sorting
    table_data = []
    for model in models:
        single = idm_single.get(model, {})
        table_data.append(
            {
                "model": model,
                "mind2web": float(single.get("mind2web_score", "0.0")) * 100,
                "aitw": float(single.get("aitw_score", "0.0")) * 100,
                "vwa": float(single.get("vwa_score", "0.0")) * 100,
                "agent_studio": float(single.get("agent_studio_score", "0.0")) * 100,
                "total": float(single.get("Score", "0.0")) * 100,
            }
        )

    # Sort by total score
    table_data.sort(key=lambda x: x["total"], reverse=True)

    # Find maximum values for each column
    max_values = {}
    for key in [
        "mind2web",
        "aitw",
        "vwa",
        "agent_studio",
        "total",
    ]:
        max_values[key] = max(item[key] for item in table_data)

    # Build LaTeX table rows
    def format_row(data):
        def format_cell(value, max_value):
            return (
                r"\textbf{" + f"{value:.1f}" + "}"
                if value == max_value
                else f"{value:.1f}"
            )

        return (
            f"{data['model']} & "
            f"{format_cell(data['mind2web'], max_values['mind2web'])} & "
            f"{format_cell(data['aitw'], max_values['aitw'])} & "
            f"{format_cell(data['vwa'], max_values['vwa'])} & "
            f"{format_cell(data['agent_studio'], max_values['agent_studio'])} & "
            f"{format_cell(data['total'], max_values['total'])} \\\\"
        )

    rows = [format_row(data) for data in table_data]

    return "\n".join(rows)


def format_latex_multiple_table(models, idm_multiple):
    # Prepare data for sorting
    table_data = []
    for model in models:
        multiple = idm_multiple.get(model, {})
        table_data.append(
            {
                "model": model,
                "mind2web": float(multiple.get("mind2web_score", "0.0")) * 100,
                "aitw": float(multiple.get("aitw_score", "0.0")) * 100,
                "vwa": float(multiple.get("vwa_score", "0.0")) * 100,
                "agent_studio": float(multiple.get("agent_studio_score", "0.0")) * 100,
                "total": float(multiple.get("Score", "0.0")) * 100,
            }
        )

    # Sort by total score
    table_data.sort(key=lambda x: x["total"], reverse=True)

    # Find maximum values for each column
    max_values = {}
    for key in [
        "mind2web",
        "aitw",
        "vwa",
        "agent_studio",
        "total",
    ]:
        max_values[key] = max(item[key] for item in table_data)

    # Build LaTeX table rows
    def format_row(data):
        def format_cell(value, max_value):
            return (
                r"\textbf{" + f"{value:.1f}" + "}"
                if value == max_value
                else f"{value:.1f}"
            )

        return (
            f"{data['model']} & "
            f"{format_cell(data['mind2web'], max_values['mind2web'])} & "
            f"{format_cell(data['aitw'], max_values['aitw'])} & "
            f"{format_cell(data['vwa'], max_values['vwa'])} & "
            f"{format_cell(data['agent_studio'], max_values['agent_studio'])} & "
            f"{format_cell(data['total'], max_values['total'])} \\\\"
        )

    rows = [format_row(data) for data in table_data]

    return "\n".join(rows) + "\n"


# Define paths to your HTML files
idm_single_files = {
    "Claude 3.5 Sonnet": "results/idm/claude-3-5-sonnet-20240620.html",
    "Gemini 1.5 Flash": "results/idm/gemini-1.5-flash-001.html",
    "Gemini 1.5 Pro": "results/idm/gemini-1.5-pro-001.html",
    "GPT-4o (0513)": "results/idm/gpt-4o-2024-05-13.html",
    "Qwen-VL-Chat": "results/idm/Qwen-VL-Chat.html",
}

idm_multiple_files = {
    "Claude 3.5 Sonnet": "results/idmn2n/claude-3-5-sonnet-20240620.html",
    "Gemini 1.5 Flash": "results/idmn2n/gemini-1.5-flash-001.html",
    "Gemini 1.5 Pro": "results/idmn2n/gemini-1.5-pro-001.html",
    "GPT-4o (0513)": "results/idmn2n/gpt-4o-2024-05-13.html",
    "Qwen-VL-Chat": "results/idmn2n/Qwen-VL-Chat.html",
}

# Extract metrics from the HTML files
idm_single_metrics = {
    model: parse_html(file) for model, file in idm_single_files.items()
}
idm_multiple_metrics = {
    model: parse_html(file) for model, file in idm_multiple_files.items()
}

# Generate LaTeX tables
latex_single_table = format_latex_single_table(
    idm_single_files.keys(), idm_single_metrics
)
latex_multiple_table = format_latex_multiple_table(
    idm_multiple_files.keys(), idm_multiple_metrics
)

# Print or save the LaTeX tables
header = r"""
\begin{tabular}{c|cccc|c}
\hline
\textbf{Model} & \textbf{Mind2Web} & \textbf{AITW} & \textbf{VWA} & \textbf{AgentStudio} & \textbf{Total} \\
\hline
\multicolumn{6}{c}{\textbf{IDM-Single}} \\
\hline
"""  # noqa: E501
mid = r"""
\hline
\multicolumn{6}{c}{\textbf{IDM-Multiple}} \\
\hline
"""
footer = r"\hline" + "\n" + r"\end{tabular}"

print(header + latex_single_table + mid + latex_multiple_table + footer)
