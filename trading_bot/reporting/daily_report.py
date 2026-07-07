from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
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
class MarketSummary:
    market: str
    symbol: str
    current_price: float
    daily_change_pct: float
    volume_ratio: float
    rsi: float
    trend: str
    macd: float
    macd_signal: float
    provider: str | None = None


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
    report_type: str = "daily"
    period_start: date | None = None
    period_end: date | None = None
    market_summaries: list[MarketSummary] = field(default_factory=list)
    good_signs: list[str] = field(default_factory=list)
    bad_signs: list[str] = field(default_factory=list)
    improvement_actions: list[str] = field(default_factory=list)
    ai_analysis: str = ""
    activity_summary: dict[str, float | int] = field(default_factory=dict)
    signal_counts: dict[str, int] = field(default_factory=dict)
    risk_events: list[str] = field(default_factory=list)
    open_positions: list[dict[str, object]] = field(default_factory=list)
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
        signal_counts: dict[str, int] | None = None,
        risk_events: list[str] | None = None,
        open_positions: list[dict[str, object]] | None = None,
        market_summaries: list[MarketSummary] | None = None,
        report_type: str = "daily",
        period_start: date | None = None,
        period_end: date | None = None,
        signal_reasons: list[dict[str, object]] | None = None,
    ) -> DailyTradingReport:
        report_date = report_date or date.today()
        period_start = period_start or report_date
        period_end = period_end or report_date
        orders = orders or []
        balances = balances or {"USD": 100_000.0, "INR": 1_000_000.0}
        market_summaries = market_summaries or []
        signal_counts = signal_counts or {}
        risk_events = risk_events or []
        open_positions = open_positions or []
        signal_reasons = signal_reasons or []

        activity_summary = self._activity_summary(orders)
        good_signs, bad_signs = self._market_signs(market_summaries, signal_counts, risk_events, open_positions)
        ai_analysis = self._ai_analysis(market_summaries, signal_counts, risk_events, activity_summary, signal_reasons)
        improvement_actions = self._improvement_actions(market_summaries, signal_counts, risk_events, orders)
        summary, no_trade = self._summary(report_type, activity_summary, base_currency)

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
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            market_summaries=market_summaries,
            good_signs=good_signs,
            bad_signs=bad_signs,
            improvement_actions=improvement_actions,
            ai_analysis=ai_analysis,
            activity_summary=activity_summary,
            signal_counts=signal_counts,
            risk_events=risk_events,
            open_positions=open_positions,
        )

    def build_from_repository(
        self,
        repository,
        recipient: str,
        balances: dict[str, float],
        us_market_status: str,
        report_date: date | None = None,
        base_currency: str = "USD",
        market_summaries: list[MarketSummary] | None = None,
        report_type: str = "daily",
        timezone_name: str = "America/Chicago",
    ) -> DailyTradingReport:
        report_date = report_date or date.today()
        period_start, period_end = self._period_bounds(report_type, report_date)
        if report_type == "daily":
            data = repository.daily_report_data(report_date, timezone_name=timezone_name)
        else:
            data = repository.date_range_report_data(period_start, period_end, timezone_name=timezone_name)
        orders = [
            ReportOrder(
                ticker=item["symbol"],
                side=item["side"],
                quantity=item["quantity"],
                price=item["price"],
                currency=item["currency"],
                status=item["status"],
                reason=item["reason"],
                pnl=item["pnl"],
            )
            for item in data["orders"]
        ]
        return self.build(
            recipient=recipient,
            orders=orders,
            balances=balances,
            portfolio_value_base=data["portfolio_value"] or balances.get(base_currency, 0.0),
            base_currency=data["portfolio_base_currency"] or base_currency,
            us_market_status=us_market_status,
            report_date=report_date,
            signal_counts=data["signal_counts"],
            risk_events=[event["reason"] for event in data["risk_events"]],
            open_positions=data["positions"],
            market_summaries=market_summaries,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            signal_reasons=data.get("signal_reasons", []),
        )

    def to_text(self, report: DailyTradingReport) -> str:
        title = f"{report.report_type.title()} Trading Review - {report.report_date.isoformat()} ({report.weekday})"
        lines = [
            title,
            f"Period: {report.period_start.isoformat()} to {report.period_end.isoformat()}",
            "",
            report.summary,
            "",
            "Market Movement:",
        ]
        if report.market_summaries:
            for item in report.market_summaries:
                lines.append(
                    f"- {item.market} {item.symbol}: {item.daily_change_pct:+.2f}% today, "
                    f"trend={item.trend}, RSI={item.rsi:.1f}, volume={item.volume_ratio:.2f}x average"
                )
        else:
            lines.append("- No live market snapshot was available. Do not trade on incomplete market data.")

        lines.extend(["", "Good Signs:"])
        lines.extend(f"- {item}" for item in report.good_signs)

        lines.extend(["", "Bad Signs / Risks:"])
        lines.extend(f"- {item}" for item in report.bad_signs)
        if report.risk_events:
            lines.append("- Recent risk notes:")
            lines.extend(f"  {event}" for event in self._compact_risk_notes(report.risk_events))

        lines.extend(["", "AI Analysis:"])
        lines.append(report.ai_analysis)

        lines.extend(["", "Trading Activity:"])
        lines.append(f"- Orders: {int(report.activity_summary['orders'])}")
        lines.append(f"- Buys: {int(report.activity_summary['buys'])}; Sells: {int(report.activity_summary['sells'])}")
        lines.append(f"- Realized P/L: {report.activity_summary['realized_pnl']:.2f} {report.base_currency}")
        if report.no_trade_explanation:
            lines.append(f"- No-trade reason: {report.no_trade_explanation}")

        lines.extend(["", "Signals:"])
        if report.signal_counts:
            for signal, count in report.signal_counts.items():
                lines.append(f"- {signal}: {count}")
        else:
            lines.append("- No signals recorded for this period.")

        lines.extend(["", "Portfolio Status:"])
        lines.append(f"- Portfolio value: {report.portfolio_value_base:.2f} {report.base_currency}")
        for currency, amount in report.balances.items():
            lines.append(f"- Cash {currency}: {amount:.2f}")
        if report.open_positions:
            lines.append(f"- Open positions: {len(report.open_positions)}")
            for position in report.open_positions[:8]:
                lines.append(
                    f"  {position['symbol']}: qty={position['quantity']}, "
                    f"entry={position['entry_price']:.2f}, current={position['current_price']:.2f}, "
                    f"stop={position['stop_loss']:.2f}, lock={position['profit_lock']:.2f}"
                )
        else:
            lines.append("- Open positions: 0")

        lines.extend(["", "What To Improve:"])
        lines.extend(f"- {item}" for item in report.improvement_actions)

        return "\n".join(lines)

    def write_pdf(self, report: DailyTradingReport, output_dir: str | Path = "reports") -> Path:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        pdf_path = output_path / f"{report.report_type}_review_{report.report_date.isoformat()}.pdf"
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            raise RuntimeError("reportlab is required for PDF reports. Run: pip install -r requirements.txt") from exc

        pdf = canvas.Canvas(str(pdf_path), pagesize=letter)
        _, height = letter
        y = height - 50
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(50, y, f"{report.report_type.title()} Trading Review - {report.report_date.isoformat()}")
        y -= 30
        pdf.setFont("Helvetica", 10)
        for line in self.to_text(report).splitlines()[1:]:
            if y < 50:
                pdf.showPage()
                pdf.setFont("Helvetica", 10)
                y = height - 50
            pdf.drawString(50, y, line[:110])
            y -= 16
        pdf.save()
        return pdf_path

    def _period_bounds(self, report_type: str, report_date: date) -> tuple[date, date]:
        if report_type == "weekly":
            return report_date - timedelta(days=6), report_date
        if report_type == "monthly":
            return report_date.replace(day=1), report_date
        if report_type == "quarterly":
            quarter_start_month = ((report_date.month - 1) // 3) * 3 + 1
            return report_date.replace(month=quarter_start_month, day=1), report_date
        return report_date, report_date

    def _activity_summary(self, orders: list[ReportOrder]) -> dict[str, float | int]:
        return {
            "orders": len(orders),
            "buys": sum(1 for order in orders if order.side.upper() == "BUY"),
            "sells": sum(1 for order in orders if order.side.upper() == "SELL"),
            "realized_pnl": sum(order.pnl for order in orders),
        }

    def _summary(
        self, report_type: str, activity: dict[str, float | int], base_currency: str
    ) -> tuple[str, str | None]:
        realized_pnl = float(activity["realized_pnl"])
        orders = int(activity["orders"])
        label = report_type.lower()
        if orders == 0:
            return (
                f"No trades were placed in this {label} period. The bot stayed in monitoring and risk-control mode.",
                "No executable signal passed market-data, AI-confidence, risk, and market-session checks.",
            )
        if realized_pnl > 0:
            return f"{label.title()} period closed with realized profit of {realized_pnl:.2f} {base_currency}.", None
        if realized_pnl < 0:
            return f"{label.title()} period closed with realized loss of {realized_pnl:.2f} {base_currency}.", None
        return f"{label.title()} period had trading activity with flat realized P/L.", None

    def _market_signs(
        self,
        market_summaries: list[MarketSummary],
        signal_counts: dict[str, int],
        risk_events: list[str],
        open_positions: list[dict[str, object]],
    ) -> tuple[list[str], list[str]]:
        good: list[str] = []
        bad: list[str] = []
        positive = [item for item in market_summaries if item.daily_change_pct > 0 and item.trend.lower() == "positive"]
        weak = [item for item in market_summaries if item.daily_change_pct < 0 or item.trend.lower() != "positive"]
        volume = [item for item in market_summaries if item.volume_ratio >= 1.0]
        overbought = [item for item in market_summaries if item.rsi >= 70]

        if positive:
            good.append(
                f"{len(positive)} watched symbols showed positive price action with positive trend confirmation."
            )
        if volume:
            good.append(
                f"{len(volume)} watched symbols traded above average volume, confirming stronger participation."
            )
        if signal_counts.get("BUY", 0) > 0:
            good.append(f"The signal engine produced {signal_counts['BUY']} BUY signal(s).")
        if open_positions:
            good.append("Open positions have active stop/profit-lock tracking.")
        if not good:
            good.append("The bot avoided forcing trades when confirmation was weak or incomplete.")

        if weak:
            bad.append(f"{len(weak)} watched symbols were weak, flat, or lacked positive trend confirmation.")
        if overbought:
            bad.append(f"{len(overbought)} watched symbols had RSI at or above 70, raising overbought risk.")
        if risk_events:
            bad.append(f"{len(risk_events)} risk event(s) were logged during the period.")
        if signal_counts.get("WAIT", 0) > signal_counts.get("BUY", 0):
            bad.append("WAIT signals dominated, meaning the strategy did not see enough confirmation.")
        if not bad:
            bad.append(
                "No major risk events were recorded, but continue treating missing data as a no-trade condition."
            )
        return good, bad

    def _ai_analysis(
        self,
        market_summaries: list[MarketSummary],
        signal_counts: dict[str, int],
        risk_events: list[str],
        activity: dict[str, float | int],
        signal_reasons: list[dict[str, object]],
    ) -> str:
        buy_count = signal_counts.get("BUY", 0)
        wait_count = signal_counts.get("WAIT", 0)
        sell_count = signal_counts.get("SELL", 0)
        avg_change = (
            sum(item.daily_change_pct for item in market_summaries) / len(market_summaries)
            if market_summaries
            else 0.0
        )
        tone = "constructive" if avg_change > 0 and buy_count >= sell_count else "cautious"
        if risk_events:
            tone = "defensive"
        reason_text = "; ".join(str(item["reason"])[:90] for item in signal_reasons[:3])
        if not reason_text:
            reason_text = "No detailed signal reasons were recorded for this period."
        return (
            f"AI assessment is {tone}. Average watched-symbol move was {avg_change:+.2f}%. "
            f"Signals: BUY={buy_count}, SELL={sell_count}, WAIT={wait_count}. "
            f"Main observed reasons: {reason_text}"
        )

    def _improvement_actions(
        self,
        market_summaries: list[MarketSummary],
        signal_counts: dict[str, int],
        risk_events: list[str],
        orders: list[ReportOrder],
    ) -> list[str]:
        actions: list[str] = []
        if not market_summaries:
            actions.append(
                "Improve market-data coverage before trading; missing snapshots should continue to block trades."
            )
        if signal_counts.get("WAIT", 0) > signal_counts.get("BUY", 0):
            actions.append(
                "Review thresholds for news confidence, volume confirmation, and trend filters after more paper data."
            )
        if risk_events:
            actions.append(
                "Review risk events and confirm emergency stop, daily loss, and max-position limits are calibrated."
            )
        if orders:
            actions.append(
                "Compare each executed order against the original signal and risk score before increasing trade size."
            )
        actions.append("Keep running paper trading and review reports before considering live trading.")
        return actions

    def _compact_risk_notes(self, risk_events: list[str]) -> list[str]:
        notes: list[str] = []
        seen: set[str] = set()
        for event in risk_events:
            note = event.split(" | ", 1)[0].strip()
            if note and note not in seen:
                notes.append(note[:120])
                seen.add(note)
            if len(notes) >= 5:
                break
        return notes
