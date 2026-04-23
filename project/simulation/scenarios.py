from __future__ import annotations

from dataclasses import dataclass
import logging
import math

import numpy as np

from project.core.config import (
    ExperimentConfig,
    HeterogeneousProfileConfig,
    NodeFailureEventConfig,
)
from project.core.models import Task
from project.simulation.context import SimulationContext

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ScenarioEvent:
    time: int
    kind: str
    details: dict[str, object]


class ScenarioEngine:
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.scenario = _normalize_scenario_name(config.scenario)
        self._rng = np.random.default_rng(config.simulation.seed)
        self._task_seq = 0
        self.generated_tasks_total = 0
        self.events: list[ScenarioEvent] = []
        self._failure_schedule: dict[int, list[NodeFailureEventConfig]] = {}
        self._recovery_schedule: dict[int, list[str]] = {}
        for event in config.scenarios.node_failures.events:
            self._failure_schedule.setdefault(event.time, []).append(event)

    def apply_events(self, t: int, context: SimulationContext) -> list[ScenarioEvent]:
        events: list[ScenarioEvent] = []
        if not self._is_failure_enabled():
            return events

        for node_id in self._recovery_schedule.pop(t, []):
            node = context.nodes.get(node_id)
            if node is None:
                continue
            node.is_active = True
            node.failed_since = None
            events.append(
                ScenarioEvent(
                    time=t,
                    kind="node_recovered",
                    details={"node_id": node_id},
                )
            )

        for failure in self._failure_schedule.get(t, []):
            event = self._apply_failure(failure, context, t)
            if event is not None:
                events.append(event)

        if events:
            self.events.extend(events)
        return events

    def generate_tasks(self, t: int) -> list[Task]:
        if not self._is_dynamic_enabled():
            return []

        rate = self._arrival_rate(t)
        if rate <= 0.0:
            return []
        max_new_tasks = max(0, self.config.scenarios.dynamic_load.max_new_tasks)
        count = int(min(max_new_tasks, self._rng.poisson(rate)))
        if count <= 0:
            return []

        tasks: list[Task] = []
        for _ in range(count):
            tasks.append(self._create_task(t))
        self.generated_tasks_total += len(tasks)
        return tasks

    def events_as_dicts(self) -> list[dict[str, object]]:
        return [
            {
                "time": event.time,
                "kind": event.kind,
                **event.details,
            }
            for event in self.events
        ]

    def _apply_failure(
        self,
        failure: NodeFailureEventConfig,
        context: SimulationContext,
        t: int,
    ) -> ScenarioEvent | None:
        node = context.nodes.get(failure.node_id)
        if node is None or not node.is_active:
            return None

        running_tasks = list(context.running_tasks.get(node.id, []))
        requeued = 0
        for task in running_tasks:
            node.release(task)
            task.status = "queued"
            task.assigned_node = None
            requeued += 1
        context.running_tasks[node.id] = []
        if running_tasks:
            context.requeue_tasks(running_tasks)

        node.is_active = False
        node.failed_since = t
        if failure.duration > 0:
            self._recovery_schedule.setdefault(t + failure.duration, []).append(node.id)

        LOGGER.warning(
            "Scenario event node failure: node=%s time=%d duration=%d requeued=%d",
            node.id,
            t,
            failure.duration,
            requeued,
        )
        return ScenarioEvent(
            time=t,
            kind="node_failed",
            details={
                "node_id": node.id,
                "duration": failure.duration,
                "requeued_tasks": requeued,
            },
        )

    def _arrival_rate(self, t: int) -> float:
        dynamic = self.config.scenarios.dynamic_load
        rate = max(0.0, dynamic.base_rate)
        if dynamic.amplitude > 0.0 and dynamic.period > 0:
            phase = (2.0 * math.pi * float(t % dynamic.period)) / float(dynamic.period)
            rate *= 1.0 + dynamic.amplitude * math.sin(phase)

        if self._is_peak_enabled():
            peak = self.config.scenarios.peak_load
            if peak.start <= t <= peak.end:
                rate *= peak.multiplier
        return max(0.0, rate)

    def _create_task(self, t: int) -> Task:
        if self._is_heterogeneous_enabled():
            profile = self._pick_profile()
        else:
            profile = self._dynamic_profile()

        duration = self._rand_int(profile.duration_range)
        slack = self._rand_int(profile.deadline_slack_range)
        task = Task(
            id=f"scn-task-{t}-{self._task_seq}",
            cpu_required=self._rand_float(profile.cpu_range),
            memory_required=self._rand_float(profile.memory_range),
            data_size=self._rand_float(profile.data_size_range),
            deadline=float(t + duration + slack),
            arrival_time=t,
            duration=duration,
        )
        self._task_seq += 1
        return task

    def _pick_profile(self) -> HeterogeneousProfileConfig:
        profiles = self.config.scenarios.heterogeneous_tasks.profiles
        idx = int(self._rng.integers(0, len(profiles)))
        return profiles[idx]

    def _dynamic_profile(self) -> HeterogeneousProfileConfig:
        dynamic = self.config.scenarios.dynamic_load
        return HeterogeneousProfileConfig(
            name="dynamic",
            cpu_range=dynamic.cpu_range,
            memory_range=dynamic.memory_range,
            data_size_range=dynamic.data_size_range,
            duration_range=dynamic.duration_range,
            deadline_slack_range=dynamic.deadline_slack_range,
        )

    def _rand_int(self, value_range: tuple[int, int]) -> int:
        low, high = value_range
        return int(self._rng.integers(low, high + 1))

    def _rand_float(self, value_range: tuple[float, float]) -> float:
        low, high = value_range
        return float(self._rng.uniform(low, high))

    def _is_dynamic_enabled(self) -> bool:
        if self.scenario in {
            "dynamic-load",
            "peak-load",
            "node-failures",
            "heterogeneous-tasks",
            "mixed",
        }:
            return True
        return self.config.scenarios.dynamic_load.enabled

    def _is_peak_enabled(self) -> bool:
        if self.scenario in {"peak-load", "mixed"}:
            return True
        return self.config.scenarios.peak_load.enabled

    def _is_failure_enabled(self) -> bool:
        if self.scenario in {"node-failures", "mixed"}:
            return True
        return self.config.scenarios.node_failures.enabled

    def _is_heterogeneous_enabled(self) -> bool:
        if self.scenario in {"heterogeneous-tasks", "mixed"}:
            return True
        return self.config.scenarios.heterogeneous_tasks.enabled


def _normalize_scenario_name(name: str) -> str:
    return str(name).strip().lower().replace("_", "-").replace(" ", "-")

