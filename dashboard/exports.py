"""Export analytics data from the dashboard."""

import io
import json
import datetime
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd


class _AnalyticsJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles types produced by pandas and numpy.

    Specifically converts:
    - ``pd.Timestamp`` → ISO 8601 string (timezone preserved)
    - ``numpy`` integer/float scalars → Python int/float
    - ``datetime.datetime`` / ``datetime.date`` → ISO 8601 string
    - ``pd.NaT``, ``float('nan')``, ``pd.NA`` → ``None``
    """

    def default(self, obj: Any) -> Any:  # noqa: ANN001
        # pd.NaT and pd.NA
        if obj is pd.NaT or obj is pd.NA:
            return None
        # pandas Timestamp (also covers datetime64 scalars)
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        # numpy integer types (int8 … int64, uint8 … uint64)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        # numpy floating types
        if isinstance(obj, (np.floating,)):
            f = float(obj)
            return None if np.isnan(f) or np.isinf(f) else f
        # numpy bool_
        if isinstance(obj, np.bool_):
            return bool(obj)
        # numpy ndarray — convert to list and let the encoder recurse
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        # stdlib datetime / date
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super().default(obj)


def export_to_csv(metrics: Dict[str, Any], chart_data: Dict[str, pd.DataFrame]) -> bytes:
    """Export metrics and chart data to CSV bytes."""
    buffer = io.StringIO()
    buffer.write("### Metrics\n")
    metrics_df = pd.DataFrame([metrics])
    metrics_df.to_csv(buffer, index=False)
    buffer.write("\n")

    for key, df in chart_data.items():
        buffer.write(f"### {key}\n")
        df.to_csv(buffer, index=False)
        buffer.write("\n")
    return buffer.getvalue().encode("utf-8")


def export_to_json(metrics: Dict[str, Any], chart_data: Dict[str, pd.DataFrame]) -> bytes:
    """Export metrics and chart data to JSON bytes."""
    payload = {
        "metrics": metrics,
        "chart_data": {key: df.to_dict(orient="records") for key, df in chart_data.items()},
    }
    return json.dumps(payload, indent=2, cls=_AnalyticsJSONEncoder).encode("utf-8")


def export_to_pdf(metrics: Dict[str, Any], chart_data: Dict[str, pd.DataFrame], file_name: str) -> bytes:
    """Return simple PDF bytes for analytics export."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, 740, "Repository Analytics Export")
    pdf.setFont("Helvetica", 10)
    y = 720
    pdf.drawString(40, y, f"Metrics Summary:")
    y -= 20
    for label, value in metrics.items():
        pdf.drawString(50, y, f"{label}: {value}")
        y -= 14
        if y < 100:
            pdf.showPage()
            y = 740
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()
