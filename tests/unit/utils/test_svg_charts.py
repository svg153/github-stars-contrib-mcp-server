"""Unit tests for SVG chart generation utilities."""

from github_stars_contrib_mcp.utils.svg_charts import SVGChartGenerator, cos, sin


class TestSVGChartGenerator:
    """Test SVGChartGenerator class methods."""

    def test_bar_chart_basic(self):
        """Test basic bar chart generation."""
        labels = ["A", "B", "C"]
        values = [10, 20, 15]
        result = SVGChartGenerator.bar_chart(labels, values, title="Test Chart")

        assert isinstance(result, str)
        assert "<svg" in result
        assert "</svg>" in result
        assert "Test Chart" in result
        assert "A" in result
        assert "B" in result
        assert "C" in result

    def test_bar_chart_empty_data(self):
        """Test bar chart with empty data."""
        result = SVGChartGenerator.bar_chart([], [])
        assert isinstance(result, str)
        assert "<svg" in result
        assert "</svg>" in result

    def test_bar_chart_single_value(self):
        """Test bar chart with single value."""
        labels = ["Single"]
        values = [100]
        result = SVGChartGenerator.bar_chart(labels, values, title="Single")

        assert isinstance(result, str)
        assert "Single" in result
        assert "100" in result

    def test_bar_chart_custom_dimensions(self):
        """Test bar chart with custom width and height."""
        labels = ["X", "Y"]
        values = [5, 10]
        result = SVGChartGenerator.bar_chart(labels, values, width=600, height=400)

        assert 'width="600"' in result
        assert 'height="400"' in result

    def test_bar_chart_no_title(self):
        """Test bar chart without title."""
        labels = ["A", "B"]
        values = [5, 10]
        result = SVGChartGenerator.bar_chart(labels, values)

        assert isinstance(result, str)
        assert "<svg" in result

    def test_bar_chart_zero_values(self):
        """Test bar chart with zero values."""
        labels = ["Zero", "NonZero"]
        values = [0, 10]
        result = SVGChartGenerator.bar_chart(labels, values)

        assert isinstance(result, str)
        assert "Zero" in result
        assert "NonZero" in result

    def test_pie_chart_basic(self):
        """Test basic pie chart generation."""
        labels = ["Slice1", "Slice2", "Slice3"]
        values = [30, 40, 30]
        result = SVGChartGenerator.pie_chart(labels, values, title="Pie")

        assert isinstance(result, str)
        assert "<svg" in result
        assert "</svg>" in result
        assert "Pie" in result
        assert "Slice1" in result
        assert "Slice2" in result
        assert "Slice3" in result

    def test_pie_chart_empty_data(self):
        """Test pie chart with empty data."""
        result = SVGChartGenerator.pie_chart([], [])
        assert isinstance(result, str)
        assert "<svg" in result

    def test_pie_chart_single_slice(self):
        """Test pie chart with single slice."""
        labels = ["Only"]
        values = [100]
        result = SVGChartGenerator.pie_chart(labels, values)

        assert isinstance(result, str)
        assert "Only" in result
        assert "100" in result

    def test_pie_chart_custom_dimensions(self):
        """Test pie chart with custom dimensions."""
        labels = ["A"]
        values = [10]
        result = SVGChartGenerator.pie_chart(labels, values, width=800, height=600)

        assert 'width="800"' in result
        assert 'height="600"' in result

    def test_pie_chart_no_title(self):
        """Test pie chart without title."""
        labels = ["A", "B"]
        values = [50, 50]
        result = SVGChartGenerator.pie_chart(labels, values)

        assert isinstance(result, str)
        assert "<svg" in result

    def test_pie_chart_percentage_display(self):
        """Test pie chart percentage calculation and display."""
        labels = ["Large", "Small"]
        values = [80, 20]
        result = SVGChartGenerator.pie_chart(labels, values)

        assert isinstance(result, str)
        assert "80" in result
        assert "20" in result

    def test_pie_chart_many_slices(self):
        """Test pie chart with many slices (tests color cycling)."""
        labels = [f"Slice{i}" for i in range(10)]
        values = [10] * 10
        result = SVGChartGenerator.pie_chart(labels, values)

        assert isinstance(result, str)
        assert "Slice0" in result
        assert "Slice9" in result

    def test_line_chart_basic(self):
        """Test basic line chart generation."""
        x_labels = ["Jan", "Feb", "Mar"]
        y_values = [10, 20, 15]
        result = SVGChartGenerator.line_chart(x_labels, y_values, title="Line")

        assert isinstance(result, str)
        assert "<svg" in result
        assert "</svg>" in result
        assert "Line" in result
        assert "Jan" in result
        assert "Feb" in result
        assert "Mar" in result

    def test_line_chart_empty_data(self):
        """Test line chart with empty data."""
        result = SVGChartGenerator.line_chart([], [])
        assert isinstance(result, str)
        assert "<svg" in result

    def test_line_chart_single_point(self):
        """Test line chart with single point."""
        x_labels = ["Point"]
        y_values = [50]
        result = SVGChartGenerator.line_chart(x_labels, y_values)

        assert isinstance(result, str)
        assert "Point" in result
        assert "50" in result

    def test_line_chart_custom_dimensions(self):
        """Test line chart with custom dimensions."""
        x_labels = ["A", "B"]
        y_values = [5, 10]
        result = SVGChartGenerator.line_chart(x_labels, y_values, width=700, height=350)

        assert 'width="700"' in result
        assert 'height="350"' in result

    def test_line_chart_no_title(self):
        """Test line chart without title."""
        x_labels = ["X", "Y"]
        y_values = [1, 2]
        result = SVGChartGenerator.line_chart(x_labels, y_values)

        assert isinstance(result, str)
        assert "<svg" in result

    def test_line_chart_negative_values(self):
        """Test line chart with negative and positive values."""
        x_labels = ["A", "B", "C"]
        y_values = [-10, 5, 20]
        result = SVGChartGenerator.line_chart(x_labels, y_values)

        assert isinstance(result, str)
        assert "A" in result
        assert "B" in result
        assert "C" in result

    def test_line_chart_same_values(self):
        """Test line chart with all same values."""
        x_labels = ["A", "B", "C"]
        y_values = [10, 10, 10]
        result = SVGChartGenerator.line_chart(x_labels, y_values)

        assert isinstance(result, str)
        assert "<svg" in result


class TestTrigonometricFunctions:
    """Test trigonometric approximation functions."""

    def test_cos_zero(self):
        """Test cosine at 0 radians."""
        result = cos(0)
        assert abs(result - 1.0) < 0.001

    def test_cos_pi_over_2(self):
        """Test cosine at π/2 radians."""
        result = cos(3.14159 / 2)
        assert abs(result) < 0.01

    def test_cos_pi(self):
        """Test cosine at π radians."""
        result = cos(3.14159)
        assert result < 0
        assert abs(result - (-1.0)) < 0.25  # Taylor series approximation tolerance

    def test_sin_zero(self):
        """Test sine at 0 radians."""
        result = sin(0)
        assert abs(result) < 0.001

    def test_sin_pi_over_2(self):
        """Test sine at π/2 radians."""
        result = sin(3.14159 / 2)
        assert abs(result - 1.0) < 0.01

    def test_sin_pi(self):
        """Test sine at π radians."""
        result = sin(3.14159)
        assert abs(result) < 0.1  # Taylor series approximation tolerance

    def test_cos_large_angle(self):
        """Test cosine with large angle (tests modulo behavior)."""
        # cos(2π) should be approximately equal to cos(0)
        result = cos(2 * 3.14159)
        assert abs(result - 1.0) < 0.01

    def test_sin_large_angle(self):
        """Test sine with large angle (tests modulo behavior)."""
        # sin(2π) should be approximately equal to sin(0)
        result = sin(2 * 3.14159)
        assert abs(result) < 0.01
