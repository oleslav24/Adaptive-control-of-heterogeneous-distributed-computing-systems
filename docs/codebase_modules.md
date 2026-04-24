# Карта кода: модули и ответственность

Этот документ описывает назначение каждого модуля в `project/`, чтобы быстрее ориентироваться в кодовой базе и понимать точки расширения.

## 1) Общая логика выполнения

Базовый путь запуска:

1. CLI читает конфиг и флаги: `project.experiments.run`.
2. Формируется `ExperimentConfig`: `project.core.config`.
3. Контроллер запускает симуляцию: `project.experiments.controller.Experiment`.
4. `SimulationLoop` инициализирует окружение (узлы, сеть, очередь, сценарии): `project.simulation.*`.
5. На каждом такте MAS-агенты наблюдают состояние, принимают решения и действуют: `project.agents.*` + `project.simulation.mas`.
6. Алгоритм назначения задач выбирает узлы: `project.algorithms.schedulers`.
7. Для интеллектуальных режимов используются предиктор и ZNN: `project.intelligence.*`.
8. Для LLM-режима применяется prompt + клиент + валидация policy: `project.llm.*`.
9. Метрики, артефакты и графики сохраняются: `project.metrics.reporter`.
10. Для batch/publication режимов используются раннеры экспериментов: `project.experiments.runner` и `project.experiments.publication`.

## 2) Модульная структура

### `project/core` — базовые контракты и модели

#### `project/core/models.py`
- Назначение: формальная модель системы (`Node`, `Task`, `NetworkEdge`, `SystemState`).
- Что важно:
  - `Node` хранит ресурсы, проверяет `can_run(task)`, выполняет `assign/release`.
  - `Task` хранит требования, дедлайн, время прибытия и длительность.
  - `SystemState` — центральный контейнер состояния симуляции и метрик.

#### `project/core/agent.py`
- Назначение: единый интерфейс агента и формат сообщений между агентами.
- Что важно:
  - `AgentMessage` — сообщение (`sender`, `recipient`, `topic`, `payload`).
  - `Agent` — базовый класс с lifecycle: `observe -> decide -> act`.
  - Встроены примитивы коммуникации: `send`, `receive`, `flush_outbox`.

#### `project/core/config.py`
- Назначение: загрузка `config.yaml` в typed-конфиг.
- Что важно:
  - `ExperimentConfig` агрегирует simulation/optimization/scenario/intelligence/llm/observability параметры.
  - Нормализует алгоритмы, сценарии, диапазоны, формат графиков.
  - Даёт единый источник правды для всех запусков.

#### `project/core/__init__.py`
- Назначение: пакетный экспорт ключевых сущностей `core`.

### `project/simulation` — движок симуляции

#### `project/simulation/bootstrap.py`
- Назначение: быстрое построение системы через `init_system(N, topology, ...)`.
- Что важно:
  - Создаёт узлы, сетевые ребра, `NetworkModel`, стартовый `SystemState`.
  - Поддерживает топологии: `full/mesh`, `ring`, `line`, `star`.

#### `project/simulation/network.py`
- Назначение: модель сети поверх `networkx`.
- Что важно:
  - Конструирует граф из `NetworkEdge`.
  - Выдаёт snapshot состояния сети.
  - Считает `node_bandwidth_map` для алгоритмов назначения.

#### `project/simulation/task_queue.py`
- Назначение: очередь задач (enqueue/extend/pop/peek).
- Что важно:
  - Изолирует операции с очередью от логики loop/агентов.

#### `project/simulation/context.py`
- Назначение: операционный контекст шага симуляции.
- Что важно:
  - Доступ к queued/running задачам.
  - API назначения задачи на узел (`assign_task`) и requeue.

#### `project/simulation/scenarios.py`
- Назначение: сценарный движок нагрузки и отказов.
- Что важно:
  - Dynamic load (в т.ч. peak burst).
  - Node failures/recovery.
  - Генерация задач с гетерогенными профилями.
  - Пишет события в историю сценария.

#### `project/simulation/randomness.py`
- Назначение: централизованная фиксация seed (`set_global_seed`).

#### `project/simulation/mas.py`
- Назначение: оркестратор мультиагентной системы.
- Что важно:
  - Вызывает `observe/decide/act` у агентов.
  - Маршрутизирует сообщения между агентами.
  - Считает служебные MAS-метрики (assignments/messages).

#### `project/simulation/loop.py`
- Назначение: основной цикл симуляции.
- Что важно:
  - Lifecycle такта: `generate_tasks -> mas.step -> update_state`.
  - Синхронизация `SystemState` на каждом шаге.
  - Финальные сводные метрики по завершению run.

#### `project/simulation/__init__.py`
- Назначение: экспорт `init_system`, `InitializedSystem`, `TopologySpec`.

### `project/agents` — конкретные агенты MAS

#### `project/agents/monitoring.py` (`MonitoringAgent`)
- Назначение: собирает и публикует срез состояния для остальных агентов.

#### `project/agents/compute.py` (`ComputeAgent`)
- Назначение: принимает задачи из очереди и назначает их на узлы.
- Что важно:
  - Учитывает активный алгоритм (`round-robin|min-load|greedy`).
  - Применяет policy-подсказки от оптимизации/LLM.

#### `project/agents/network.py` (`NetworkAgent`)
- Назначение: учитывает сетевые ограничения при распределении.
- Что важно:
  - Отсеивает/маркирует узлы с низкой пропускной способностью.

#### `project/agents/qos.py` (`QoSAgent`)
- Назначение: контроль дедлайнов/SLA и приоритизация срочных задач.

#### `project/agents/optimization.py` (`OptimizationAgent`)
- Назначение: выставляет/корректирует алгоритмическую policy.
- Что важно:
  - Поддерживает фиксированный и адаптивный режим.

#### `project/agents/prediction.py` (`PredictionAgent`)
- Назначение: прогноз нагрузки и управляющие сигналы для адаптивности.
- Что важно:
  - Использует `LinearLoadRegressor` и `ZNNBalancer`.
  - Генерирует рекомендации по bias/алгоритму.

#### `project/agents/llm.py` (`LLMAgent`)
- Назначение: LLM-анализ состояния и предложение действий.
- Что важно:
  - Формирует prompt из state.
  - Вызывает LLM-клиент.
  - Пропускает решение через policy guard и передаёт в MAS.

#### `project/agents/__init__.py`
- Назначение: пакетный экспорт агентов.

### `project/algorithms` — эвристики назначения

#### `project/algorithms/schedulers.py`
- Назначение: чистые функции выбора узла для задачи.
- Что важно:
  - `normalize_algorithm` нормализует имя стратегии.
  - `choose_node` точка входа для всех политик.
  - Реализованы `_round_robin`, `_min_load`, `_greedy`.

#### `project/algorithms/__init__.py`
- Назначение: экспорт API планировщиков.

### `project/intelligence` — ML/ZNN слой

#### `project/intelligence/ml.py`
- Назначение: простая регрессия для прогноза очереди/нагрузки.
- Что важно:
  - `LinearLoadRegressor.predict_next(series)` возвращает next-step forecast.

#### `project/intelligence/znn.py`
- Назначение: упрощённый ZNN-механизм балансировки.
- Что важно:
  - `node_bias(node_loads, predicted_avg_load)` формирует bias по узлам.

#### `project/intelligence/__init__.py`
- Назначение: экспорт intelligence-компонентов.

### `project/llm` — инфраструктура LLM-управления

#### `project/llm/prompt.py`
- Назначение: преобразование `SystemState -> text` и сборка prompt-шаблона.

#### `project/llm/client.py`
- Назначение: унифицированный клиент LLM (OpenAI и mock).
- Что важно:
  - Поддерживает таймаут/temperature/max_tokens.
  - Имеет стабильный `mock` для воспроизводимых экспериментов.

#### `project/llm/policy.py`
- Назначение: безопасный разбор и ограничение действий LLM.
- Что важно:
  - `parse_llm_decision` извлекает структуру решения.
  - `clamp_decision` применяет whitelist алгоритмов и clamp bias.

#### `project/llm/__init__.py`
- Назначение: экспорт LLM-модулей.

### `project/metrics` — наблюдаемость и артефакты

#### `project/metrics/reporter.py`
- Назначение: сбор summary/history и экспорт CSV/JSON/plots.
- Что важно:
  - `summarize_state` даёт компактный финальный снимок run.
  - `persist_observability` сохраняет артефакты одиночного запуска.
  - `persist_batch_observability` сохраняет агрегаты batch-запуска.
  - Поддерживает publication-профиль графиков (`png/pdf/svg`, DPI, стиль).

#### `project/metrics/__init__.py`
- Назначение: экспорт API репортинга.

### `project/experiments` — запуск и исследовательские режимы

#### `project/experiments/controller.py`
- Назначение: тонкий orchestration-слой одного эксперимента.
- Что важно:
  - Инкапсулирует создание и запуск `SimulationLoop`.

#### `project/experiments/run.py`
- Назначение: основной CLI entrypoint.
- Что важно:
  - Режимы: single, compare, batch, repro-check, AB (LLM/intelligence), publication-study.
  - Runtime override параметров конфигурации через CLI.
  - Единая печать итогов и маршрутизация артефактов.

#### `project/experiments/runner.py`
- Назначение: пакетные прогоны по матрице `scenario x algorithm x repeat`.
- Что важно:
  - Агрегирует `summary/ranking/winners`.
  - Сохраняет batch-manifest и табличные артефакты.

#### `project/experiments/publication.py`
- Назначение: pipeline публикационного уровня (E1-E5, H1-H5).
- Что важно:
  - Генерирует набор run specs и seeds.
  - Формирует методы сравнения (готовые + placeholders).
  - Считает расширенные метрики, статистику и CI95.
  - Экспортирует `raw_runs`, `summary`, `hypotheses`, report, publication manifest, графики.

#### `project/experiments/manifest.py`
- Назначение: манифест воспроизводимости.
- Что важно:
  - Фиксирует `git_commit`, `git_dirty`, версии зависимостей, CLI args, config snapshot.

#### `project/experiments/__init__.py`
- Назначение: экспорт контроллера, batch/publication API.

### `project/__init__.py`
- Назначение: корневой пакет проекта.

## 3) Зависимости между пакетами

- `core` — нижний уровень, от него зависят почти все.
- `simulation` использует `core`, `algorithms`, `agents`, `intelligence`, `llm`.
- `agents` используют `core`, плюс профильные пакеты (`algorithms`, `intelligence`, `llm`).
- `experiments` оркестрирует `simulation` и `metrics`.
- `metrics` читает только финальные структуры состояния и DataFrame.

Практическое правило расширения:

1. Новая логика планирования: добавлять в `algorithms/` и подключать через `OptimizationAgent`/CLI.
2. Новый агент: добавлять в `agents/`, подключать при сборке списка агентов в `SimulationLoop.init_system` (`project/simulation/loop.py`).
3. Новый сценарий: добавлять в `simulation/scenarios.py` + конфиг в `core/config.py`.
4. Новый тип отчётности: добавлять в `metrics/reporter.py` и/или `experiments/publication.py`.

## 4) Точки входа для разработчика

- Быстрый запуск одного эксперимента: `python -m project.experiments.run --config config.yaml`
- Матрица сравнений: `python -m project.experiments.run --config config.yaml --batch`
- Публикационный pipeline: `python -m project.experiments.run --config config.yaml --publication-study`
