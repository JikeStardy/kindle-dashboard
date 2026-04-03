import io
import base64
import threading
import yfinance as yf
from matplotlib.figure import Figure
from .base import SimpleCache, ServiceProtocol


yf_lock = threading.Lock()


def generate_sparkline(ticker_symbol: str) -> tuple[str | None, str, float]:
    """Returns (base64_png, price_str, change_pct)."""
    try:
        with yf_lock:
            hist = yf.download(ticker_symbol, period="5d", interval="60m", progress=False)
        if hist is None or hist.empty:
            return None, "--", 0
        try:
            prices = hist["Close"].values.flatten()
        except KeyError:
            if "Adj Close" in hist:
                prices = hist["Adj Close"].values.flatten()
            else:
                return None, "--", 0
        if len(prices) == 0:
            return None, "--", 0
        current_price = prices[-1]
        prev_close = prices[0]
        percent_change = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0
        fig = Figure(figsize=(4, 1), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(prices, color="black", linewidth=3)
        ax.axis("off")
        img = io.BytesIO()
        fig.savefig(img, format="png", transparent=True, bbox_inches="tight", pad_inches=0)
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()
        return plot_url, current_price, percent_change
    except Exception as e:
        print(f"Finance Error {ticker_symbol}: {e}")
        return None, "--", 0


class FinanceService:
    def __init__(self, tickers: list[dict], cache: SimpleCache):
        self._tickers = tickers
        self._cache = cache

    @property
    def cache_ttl(self) -> int:
        return self._cache._ttl

    def fetch(self) -> list[dict]:
        cached = self._cache.get("finance_data")
        if cached:
            return cached

        result = []
        for ticker in self._tickers:
            chart, price, change = generate_sparkline(ticker["symbol"])
            if price == "--":
                price_str = "--"
            elif "BTC" in ticker["name"]:
                price_str = f"{price:,.0f}"
            else:
                try:
                    price_str = f"{price:.4f}"
                except Exception:
                    price_str = str(price)
            result.append({
                "name": ticker["name"],
                "price": price_str,
                "change": change,
                "chart": chart,
            })

        self._cache.set("finance_data", result)
        return result
