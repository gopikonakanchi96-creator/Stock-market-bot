from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class ReportOrder:
    ticker: str
    side: str
    quantity: int
    price: float
    currency: str
    status: str
    reason: str
    pnl: float = 0.0


@dataclass(frozen=True)
class DailyTradingReport:
    report_date: date
    weekday: str
    recipient: str
    orders: list[ReportOrder]
    balances: dict[str, float]
    portfolio_value_base: float
    base_currency: str
    us_market_status: str
    summary: str
    no_trade_explanation: str | None = None
    generated_at: datetime = field(default_factory=datetime.now)


class DailyReportBuilder:
    def build(
        self,
        recipient: str,
        orders: list[ReportOrder] | None = None,
        balances: dict[str, float] | None = None,
        portfolio_value_base: float = 0.0,
        base_currency: str = "USD",
        us_market_status: str = "Not checked",
        report_date: date | None = None,
    ) -> DailyTradingReport:
        report_date = report_date or date.today()
        orders = orders or []
        balances = balances or {"USD": 100_000.0, "INR": 1_000_000.0}
        realized_pnl = sum(order.pnl for order in orders)
        if not orders:
            summary = "No trades were placed today. The bot remained in monitoring/risk-control mode."
            no_trade = "No executable signal passed market-data, AI-confidence, risk, and market-session checks."
        elif realized_pnl > 0:
            summary = f"Trading day closed with realized profit of {realized_pnl:.2f} {base_currency}."
            no_trade = None
        elif realized_pnl < 0:
            summary = f"Trading day closed with realized loss of {realized_pnl:.2f} {base_currency}."
            no_trade = None
        else:
            summary = "Trading activity occurred today with flat realized P/L."
            no_trade = None
        return DailyTradingReport(
            report_date=report_date,
            weekday=report_date.strftime("%A"),
            recipient=recipient,
            orders=orders,
            balances=balances,
            portfolio_value_base=portfolio_value_base,
            base_currency=base_currency,
            us_market_status=us_market_status,
            summary=summary,
            no_trade_explanation=no_trade,
        )

    def to_text(self, report: DailyTradingReport) -> str:
        lines = [
            f"Daily Trading Report - {report.report_date.isoformat()} ({report.weekday})",
            "",
            report.summary,
            "",
            f"US market status: {report.us_market_status}",
            f"Portfolio value: {report.portfolio_value_base:.2f} {report.base_currency}",
            "",
            "Balances:",
        ]
        for currency, amount in report.balances.items():
            lines.append(f"- {currency}: {amount:.2f}")
        lines.extend(["", "Orders:"])
        if not report.orders:
            lines.append("- No orders placed today.")
            if report.no_trade_explanation:
                lines.append(f"- Reason: {report.no_trade_explanation}")
        else:
            for order in report.orders:
                pnl_status = "profit" if order.pnl > 0 else "loss" if order.pnl < 0 else "flat"
                lines.append(
                    f"- {order.side} {order.quantity} {order.ticker} @ {order.price:.2f} {order.currency}; "
                    f"status={order.status}; pnl={order.pnl:.2f}; outcome={pnl_status}; reason={order.reason}"
                )
        return "\n".join(lines)

    def write_pdf(self, report: DailyTradingReport, output_dir: str | Path = "reports") -> Path:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        pdf_path = output_path / f"daily_report_{report.report_date.isoformat()}.pdf"
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            raise RuntimeError("reportlab is required for PDF reports. Run: pip install -r requirements.txt") from exc

        pdf = canvas.Canvas(str(pdf_path), pagesize=letter)
        width, height = letter
        y = height - 50
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y, f"Daily Trading Report - {report.report_date.isoformat()} ({report.weekday})")
        y -= 30
        pdf.setFont("Helvetica", 10)
        for line in self.to_text(report).splitlines()[2:]:
            if y < 50:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y = height - 50
            pdf.drawString(50, y, line[:110])
            y -= 16
        pdf.save()
        return pdf_path

