"""Researcher agent that explains likely conclusions from runtime charts."""

from __future__ import annotations

from statistics import fmean, pstdev
from typing import Sequence

from project.core.agent import Agent


def _safe_floats(values: Sequence[float | int] | None) -> list[float]:
    """Convert numeric sequence to float list, skipping invalid values."""
    if not values:
        return []
    cleaned: list[float] = []
    for value in values:
        try:
            cleaned.append(float(value))
        except (TypeError, ValueError):
            continue
    return cleaned


def _relative_change(values: Sequence[float]) -> float:
    """Return relative start-to-end change with safe near-zero denominator."""
    if len(values) < 2:
        return 0.0
    start = float(values[0])
    end = float(values[-1])
    scale = abs(start) if abs(start) > 1e-9 else 1.0
    return (end - start) / scale


def _slope(values: Sequence[float]) -> float:
    """Return simple per-step slope over full window."""
    if len(values) < 2:
        return 0.0
    return (float(values[-1]) - float(values[0])) / float(len(values) - 1)


class ResearcherAgent(Agent):
    """Analyze chart metrics and produce concise textual findings."""

    def __init__(self, name: str = "researcher") -> None:
        super().__init__(name=name)
        self.last_insights: list[str] = []

    def decide(self) -> None:
        """Produce insights from observed state history when used in MAS."""
        if self.state is None or not self.state.history:
            self.last_insights = []
            return
        history = self.state.history
        metrics = {
            "time": [entry.get("time", 0) for entry in history],
            "queue": [entry.get("queue_size", 0) for entry in history],
            "completed": [entry.get("completed_tasks", 0) for entry in history],
            "latency": [entry.get("avg_latency", 0.0) for entry in history],
            "throughput": [entry.get("throughput", 0.0) for entry in history],
            "avg_load": [entry.get("avg_load", 0.0) for entry in history],
        }
        self.last_insights = self.analyze_metrics(metrics, lang="en")

    def act(self) -> None:
        """This agent is analytical and does not apply direct actions."""
        return

    def analyze_metrics(
        self,
        metrics: dict[str, Sequence[float | int]],
        *,
        lang: str = "en",
        status: str | None = None,
        max_items: int = 6,
    ) -> list[str]:
        """Generate human-readable insights from chart time series."""
        ru = str(lang).strip().lower() == "ru"
        time_values = _safe_floats(metrics.get("time"))
        queue = _safe_floats(metrics.get("queue"))
        completed = _safe_floats(metrics.get("completed"))
        latency = _safe_floats(metrics.get("latency"))
        throughput = _safe_floats(metrics.get("throughput"))
        avg_load = _safe_floats(metrics.get("avg_load"))

        legend_note = (
            "Пояснение линий: цвет линии = отдельный подпрогон. "
            "На графике queue/completed сплошная линия — очередь, пунктир — выполненные задачи (накопительно)."
            if ru
            else "Line legend: line color = individual sub-run. "
            "On queue/completed chart, solid line = queue, dashed line = completed tasks (cumulative)."
        )

        if len(time_values) < 2:
            return [
                legend_note,
                (
                    "Недостаточно данных для выводов: дождитесь нескольких тактов симуляции."
                    if ru
                    else "Not enough data for conclusions yet: wait for more simulation ticks."
                ),
            ]

        insights: list[str] = [legend_note]
        lat_change = _relative_change(latency)
        thr_change = _relative_change(throughput)
        queue_change = _relative_change(queue)
        queue_rate = _slope(queue)
        completion_rate = _slope(completed)
        load_recent = avg_load[-min(6, len(avg_load)) :]
        latency_recent = latency[-min(8, len(latency)) :]

        if lat_change <= -0.12:
            insights.append(
                (
                    f"Задержка снижается ({latency[0]:.3f} -> {latency[-1]:.3f}), качество обслуживания улучшается."
                    if ru
                    else f"Latency is decreasing ({latency[0]:.3f} -> {latency[-1]:.3f}), service quality is improving."
                )
            )
        elif lat_change >= 0.12:
            insights.append(
                (
                    f"Задержка растет ({latency[0]:.3f} -> {latency[-1]:.3f}), есть признаки деградации."
                    if ru
                    else f"Latency is increasing ({latency[0]:.3f} -> {latency[-1]:.3f}), indicating possible degradation."
                )
            )
        else:
            insights.append(
                (
                    "Задержка в целом стабильна, сильного дрейфа не наблюдается."
                    if ru
                    else "Latency is broadly stable with no strong drift."
                )
            )

        if thr_change >= 0.12:
            insights.append(
                (
                    f"Пропускная способность растет ({throughput[0]:.3f} -> {throughput[-1]:.3f})."
                    if ru
                    else f"Throughput is increasing ({throughput[0]:.3f} -> {throughput[-1]:.3f})."
                )
            )
        elif thr_change <= -0.12:
            insights.append(
                (
                    f"Пропускная способность падает ({throughput[0]:.3f} -> {throughput[-1]:.3f})."
                    if ru
                    else f"Throughput is decreasing ({throughput[0]:.3f} -> {throughput[-1]:.3f})."
                )
            )
        else:
            insights.append(
                (
                    "Пропускная способность удерживается на близком уровне."
                    if ru
                    else "Throughput remains at a comparable level."
                )
            )

        if queue_rate > 0.15 and completion_rate <= 0.0:
            insights.append(
                (
                    "Очередь накапливается быстрее, чем завершаются задачи: риск перегрузки."
                    if ru
                    else "Queue is accumulating faster than tasks finish: overload risk is rising."
                )
            )
        elif queue_change < -0.12 and completion_rate > 0.0:
            insights.append(
                (
                    "Очередь разгружается, система успевает обрабатывать поток задач."
                    if ru
                    else "Queue is being drained; the system is keeping up with incoming work."
                )
            )
        else:
            insights.append(
                (
                    "Динамика очереди умеренная, выраженного накопления не видно."
                    if ru
                    else "Queue dynamics are moderate without clear runaway accumulation."
                )
            )

        if load_recent:
            load_mean = fmean(load_recent)
            load_peak = max(avg_load) if avg_load else 0.0
            if load_peak >= 0.90 and queue_rate > 0.0:
                insights.append(
                    (
                        f"Пиковая загрузка высокая (до {load_peak:.2f}), возможны узкие места."
                        if ru
                        else f"Peak load is high (up to {load_peak:.2f}), bottlenecks are likely."
                    )
                )
            elif load_mean < 0.30 and thr_change <= 0.0:
                insights.append(
                    (
                        f"Средняя загрузка низкая ({load_mean:.2f}): ресурсы могут использоваться неэффективно."
                        if ru
                        else f"Average load is low ({load_mean:.2f}): resources may be underutilized."
                    )
                )
            else:
                insights.append(
                    (
                        f"Средняя загрузка в рабочем диапазоне ({load_mean:.2f})."
                        if ru
                        else f"Average load is in a healthy operating range ({load_mean:.2f})."
                    )
                )

        if len(latency_recent) >= 3:
            mean_latency = fmean(latency_recent)
            volatility = pstdev(latency_recent)
            coef = volatility / (mean_latency if abs(mean_latency) > 1e-9 else 1.0)
            if coef > 0.25:
                insights.append(
                    (
                        "Задержка нестабильна (высокая вариативность), полезно проверить балансировку."
                        if ru
                        else "Latency is unstable (high variability); rebalancing may help."
                    )
                )

        if status in {"success", "failed", "stopped"}:
            insights.append(
                (
                    "Прогон завершен: выводы сформированы по финальному участку графиков."
                    if ru
                    else "Run finished: conclusions are based on the final chart segment."
                )
            )

        return insights[: max(1, int(max_items))]
