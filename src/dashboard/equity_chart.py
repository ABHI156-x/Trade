"""
Stage 24 – ASCII Equity Curve Renderer
Renders a sparkline of the equity curve using block characters.
"""

from typing import List


_BARS = " ▁▂▃▄▅▆▇█"


def render_ascii_equity_curve(
    equity_series: List[float],
    width: int = 60,
    label: str = "Equity Curve"
) -> str:
    """
    Render *equity_series* as a single-line ASCII sparkline.

    Parameters
    ----------
    equity_series : list of float – equity values over time
    width         : max characters wide for the sparkline
    label         : header label

    Returns
    -------
    Multi-line string (label + sparkline).
    """
    if not equity_series:
        return f"{label}: (no data)"

    series = list(equity_series)

    # Downsample if too many points
    if len(series) > width:
        step = len(series) / width
        series = [series[int(i * step)] for i in range(width)]

    lo = min(series)
    hi = max(series)
    span = hi - lo

    if span == 0:
        bars = _BARS[4] * len(series)   # flat line
    else:
        bars = "".join(
            _BARS[int((v - lo) / span * (len(_BARS) - 1))]
            for v in series
        )

    start_val = equity_series[0]
    end_val   = equity_series[-1]
    change    = end_val - start_val
    pct       = (change / start_val * 100) if start_val else 0
    sign      = "+" if change >= 0 else ""

    header = (
        f"  {label}: ₹{start_val:,.0f} → ₹{end_val:,.0f}  "
        f"({sign}{change:,.0f} | {sign}{pct:.1f}%)"
    )

    return f"{header}\n  {bars}"
