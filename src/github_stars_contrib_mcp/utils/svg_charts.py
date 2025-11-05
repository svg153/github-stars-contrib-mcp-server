"""SVG chart generation utilities for MCP visualization."""


class SVGChartGenerator:
    """Generate SVG charts without external dependencies."""

    @staticmethod
    def bar_chart(
        labels: list[str],
        values: list[int | float],
        title: str = "",
        width: int = 500,
        height: int = 300,
    ) -> str:
        """Generate SVG bar chart."""
        padding = 50
        chart_width = width - 2 * padding
        chart_height = height - 2 * padding

        max_val = max(values) if values else 1
        bar_width = chart_width / len(values) if values else 1

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" style="font-family: Arial, sans-serif; background: white;">',
            "<defs>",
            "<style>",
            ".title { font-size: 18px; font-weight: bold; }",
            ".label { font-size: 12px; text-anchor: middle; }",
            ".value { font-size: 11px; text-anchor: middle; fill: #333; }",
            ".axis { stroke: #999; stroke-width: 1; }",
            "</style>",
            "</defs>",
        ]

        # Title
        if title:
            svg_parts.append(
                f'<text x="{width / 2}" y="30" text-anchor="middle" class="title">{title}</text>'
            )

        # Y-axis
        svg_parts.append(
            f'<line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height - padding}" class="axis"/>'
        )

        # X-axis
        svg_parts.append(
            f'<line x1="{padding}" y1="{height - padding}" x2="{width - padding}" y2="{height - padding}" class="axis"/>'
        )

        # Bars
        for i, (label, value) in enumerate(zip(labels, values, strict=False)):
            bar_height = (value / max_val) * chart_height if max_val > 0 else 0
            x = padding + i * bar_width + bar_width / 4
            y = height - padding - bar_height

            # Bar
            svg_parts.append(
                f'<rect x="{x}" y="{y}" width="{bar_width / 2}" height="{bar_height}" fill="#4A90E2" opacity="0.8"/>'
            )

            # Label
            label_x = padding + i * bar_width + bar_width / 2
            label_y = height - padding + 20
            svg_parts.append(
                f'<text x="{label_x}" y="{label_y}" class="label">{label}</text>'
            )

            # Value
            value_y = y - 5
            svg_parts.append(
                f'<text x="{label_x}" y="{value_y}" class="value">{value}</text>'
            )

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    @staticmethod
    def pie_chart(
        labels: list[str],
        values: list[int | float],
        title: str = "",
        width: int = 400,
        height: int = 400,
    ) -> str:
        """Generate SVG pie chart."""
        colors = [
            "#4A90E2",
            "#50C878",
            "#FFB84D",
            "#E75480",
            "#9B59B6",
            "#1ABC9C",
            "#E67E22",
            "#34495E",
        ]

        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 2 - 40

        total = sum(values) if values else 1
        current_angle = -90  # Start from top

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" style="font-family: Arial, sans-serif; background: white;">',
            "<defs>",
            "<style>",
            ".pie-label { font-size: 12px; text-anchor: middle; fill: white; font-weight: bold; }",
            ".pie-title { font-size: 16px; font-weight: bold; text-anchor: middle; }",
            ".legend-text { font-size: 12px; }",
            "</style>",
            "</defs>",
        ]

        # Title
        if title:
            svg_parts.append(
                f'<text x="{width / 2}" y="25" class="pie-title">{title}</text>'
            )

        # Pie slices
        legend_y = 60
        for i, (label, value) in enumerate(zip(labels, values, strict=False)):
            percentage = (value / total * 100) if total > 0 else 0
            angle = (percentage / 100) * 360

            start_angle = current_angle
            end_angle = current_angle + angle

            # Convert to radians
            start_rad = start_angle * 3.14159 / 180
            end_rad = end_angle * 3.14159 / 180

            # SVG arc path (simplified for readability)
            large_arc = 1 if angle > 180 else 0

            x2 = center_x + radius * cos(end_rad)
            y2 = center_y + radius * sin(end_rad)

            path = f"M {center_x} {center_y} L {center_x + radius * cos(start_rad)} {center_y + radius * sin(start_rad)} A {radius} {radius} 0 {large_arc} 1 {x2} {y2} Z"

            color = colors[i % len(colors)]
            svg_parts.append(f'<path d="{path}" fill="{color}" opacity="0.8"/>')

            # Percentage label (center of slice)
            label_angle = start_angle + angle / 2
            label_rad = label_angle * 3.14159 / 180
            label_radius = radius * 0.6
            label_x = center_x + label_radius * cos(label_rad)
            label_y = center_y + label_radius * sin(label_rad)

            if percentage > 5:  # Only show percentage if slice is large enough
                svg_parts.append(
                    f'<text x="{label_x}" y="{label_y}" class="pie-label">{percentage:.1f}%</text>'
                )

            # Legend
            legend_color_x = 20
            svg_parts.append(
                f'<rect x="{legend_color_x}" y="{legend_y + i * 20}" width="15" height="15" fill="{color}"/>'
            )
            svg_parts.append(
                f'<text x="40" y="{legend_y + i * 20 + 12}" class="legend-text">{label} ({value})</text>'
            )

            current_angle = end_angle

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)

    @staticmethod
    def line_chart(
        x_labels: list[str],
        y_values: list[int | float],
        title: str = "",
        width: int = 500,
        height: int = 300,
    ) -> str:
        """Generate SVG line chart."""
        padding = 50
        chart_width = width - 2 * padding
        chart_height = height - 2 * padding

        max_val = max(y_values) if y_values else 1
        min_val = min(y_values) if y_values else 0
        value_range = max_val - min_val if max_val > min_val else 1

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" style="font-family: Arial, sans-serif; background: white;">',
            "<defs>",
            "<style>",
            ".line { stroke: #4A90E2; stroke-width: 2; fill: none; }",
            ".point { fill: #4A90E2; r: 4; }",
            ".label { font-size: 11px; text-anchor: middle; }",
            ".title { font-size: 16px; font-weight: bold; text-anchor: middle; }",
            ".axis { stroke: #999; stroke-width: 1; }",
            ".grid { stroke: #EEE; stroke-width: 1; }",
            "</style>",
            "</defs>",
        ]

        # Title
        if title:
            svg_parts.append(
                f'<text x="{width / 2}" y="25" class="title">{title}</text>'
            )

        # Grid and axes
        svg_parts.append(
            f'<line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height - padding}" class="axis"/>'
        )
        svg_parts.append(
            f'<line x1="{padding}" y1="{height - padding}" x2="{width - padding}" y2="{height - padding}" class="axis"/>'
        )

        # Points and line
        points = []
        for i, value in enumerate(y_values):
            x = (
                padding + (i / (len(y_values) - 1)) * chart_width
                if len(y_values) > 1
                else padding + chart_width / 2
            )
            y = height - padding - ((value - min_val) / value_range) * chart_height
            points.append((x, y))

            # Draw point
            svg_parts.append(f'<circle cx="{x}" cy="{y}" class="point"/>')

            # Draw label
            label_y = height - padding + 20
            svg_parts.append(
                f'<text x="{x}" y="{label_y}" class="label">{x_labels[i] if i < len(x_labels) else ""}</text>'
            )

        # Draw line
        if points:
            path_data = f"M {points[0][0]} {points[0][1]}"
            for x, y in points[1:]:
                path_data += f" L {x} {y}"
            svg_parts.append(f'<path d="{path_data}" class="line"/>')

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)


def cos(radians: float) -> float:
    """Approximate cosine without math library."""
    # Use Taylor series for approximation
    x = radians % (2 * 3.14159)
    return 1 - x**2 / 2 + x**4 / 24 - x**6 / 720


def sin(radians: float) -> float:
    """Approximate sine without math library."""
    # Use Taylor series for approximation
    x = radians % (2 * 3.14159)
    return x - x**3 / 6 + x**5 / 120 - x**7 / 5040
