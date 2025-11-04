"""HTML chart generation utilities using Plotly for MCP-UI."""

import json
from typing import Any


class PlotlyChartGenerator:
    """Generate interactive Plotly charts as HTML for MCP-UI resources."""

    @staticmethod
    def bar_chart(
        labels: list[str],
        values: list[int | float],
        title: str = "",
        x_label: str = "",
        y_label: str = "",
    ) -> str:
        """Generate interactive bar chart using Plotly."""
        chart_data = {
            "data": [
                {
                    "x": labels,
                    "y": values,
                    "type": "bar",
                    "marker": {"color": "#4A90E2"},
                }
            ],
            "layout": {
                "title": title,
                "xaxis": {"title": x_label},
                "yaxis": {"title": y_label},
                "hovermode": "closest",
                "margin": {"l": 50, "r": 50, "t": 80, "b": 50},
            },
        }

        return _generate_plotly_html(chart_data, f"chart-bar-{id(labels)}")

    @staticmethod
    def pie_chart(
        labels: list[str],
        values: list[int | float],
        title: str = "",
    ) -> str:
        """Generate interactive pie chart using Plotly."""
        chart_data = {
            "data": [
                {
                    "labels": labels,
                    "values": values,
                    "type": "pie",
                    "textposition": "inside",
                    "textinfo": "label+percent",
                    "hoverinfo": "label+value+percent",
                }
            ],
            "layout": {
                "title": title,
                "height": 500,
                "showlegend": True,
                "legend": {"x": 1.05, "y": 1},
            },
        }

        return _generate_plotly_html(chart_data, f"chart-pie-{id(labels)}")

    @staticmethod
    def line_chart(
        x_labels: list[str],
        y_values: list[int | float],
        title: str = "",
        x_label: str = "",
        y_label: str = "",
    ) -> str:
        """Generate interactive line chart using Plotly."""
        chart_data = {
            "data": [
                {
                    "x": x_labels,
                    "y": y_values,
                    "type": "scatter",
                    "mode": "lines+markers",
                    "line": {"color": "#4A90E2", "width": 2},
                    "marker": {"size": 8},
                    "hoverinfo": "x+y",
                }
            ],
            "layout": {
                "title": title,
                "xaxis": {"title": x_label},
                "yaxis": {"title": y_label},
                "hovermode": "closest",
                "margin": {"l": 50, "r": 50, "t": 80, "b": 50},
            },
        }

        return _generate_plotly_html(chart_data, f"chart-line-{id(x_labels)}")

    @staticmethod
    def dashboard_html(
        title: str,
        sections: list[dict[str, Any]],
    ) -> str:
        """Generate a dashboard with multiple sections."""
        html_parts = [
            """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; background: #f5f7fa; padding: 20px; }
        .dashboard { max-width: 1200px; margin: 0 auto; }
        .header { margin-bottom: 30px; }
        .header h1 { color: #1a202c; font-size: 28px; font-weight: 600; }
        .sections { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .section { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1); }
        .section h2 { color: #2d3748; font-size: 18px; font-weight: 600; margin-bottom: 15px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
        .metric { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px; margin-top: 15px; }
        .metric-card { background: #f7fafc; border-left: 4px solid #4a90e2; padding: 15px; border-radius: 4px; }
        .metric-label { font-size: 12px; color: #718096; text-transform: uppercase; letter-spacing: 0.5px; }
        .metric-value { font-size: 24px; font-weight: 700; color: #1a202c; margin-top: 5px; }
        .chart { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1); margin-top: 20px; }
        .full-width { grid-column: 1 / -1; }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>""",
            title,
            """</h1>
        </div>
        <div class="sections">
""",
        ]

        for section in sections:
            section_type = section.get("type", "text")
            if section_type == "text":
                html_parts.append(
                    f'<div class="section"><h2>{section.get("title", "")}</h2>'
                )
                html_parts.append(f"<p>{section.get('content', '')}</p></div>")
            elif section_type == "metrics":
                html_parts.append(
                    f'<div class="section"><h2>{section.get("title", "")}</h2><div class="metric">'
                )
                for metric in section.get("metrics", []):
                    html_parts.append(
                        f'<div class="metric-card"><div class="metric-label">{metric.get("label", "")}</div><div class="metric-value">{metric.get("value", "")}</div></div>'
                    )
                html_parts.append("</div></div>")
            elif section_type == "chart":
                html_parts.append(
                    f'<div class="section full-width"><h2>{section.get("title", "")}</h2>'
                )
                html_parts.append(
                    f'<div id="{section.get("id", "chart")}" style="height: 400px;"></div></div>'
                )

        html_parts.append(
            """
        </div>
    </div>
</body>
</html>"""
        )

        return "".join(html_parts)


def _generate_plotly_html(chart_data: dict[str, Any], chart_id: str) -> str:
    """Generate complete HTML with embedded Plotly chart."""
    chart_json = json.dumps(chart_data)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chart</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1); }}
        #chart {{ width: 100%; height: 500px; }}
    </style>
</head>
<body>
    <div class="container">
        <div id="{chart_id}"></div>
    </div>
    <script>
        const data = {chart_json};
        Plotly.newPlot('{chart_id}', data.data, data.layout, {{responsive: true}});
    </script>
</body>
</html>"""

    return html
