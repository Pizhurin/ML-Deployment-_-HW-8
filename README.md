# ДЗ 8 — Мониторинг ML-сервиса

## SLO (Service Level Objectives)

| # | Метрика | SLO | Prometheus-запрос |
|---|---------|-----|-------------------|
| 1 | Latency p95 | < 1 сек | `histogram_quantile(0.95, sum(rate(request_latency_seconds_bucket[5m])) by (le))` |
| 2 | Error Rate | < 1% | `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])` |
| 3 | Availability | > 99% | `up{job="ml_service"}` |

---

## Структура репозитория

```
.
├── docker-compose.yml        # Prometheus + Grafana + ML-сервис + PostgreSQL
├── prometheus.yml            # Конфиг Prometheus (scrape_configs)
├── alerts.yml                # Правила алертов (3 SLO)
├── grafana/
│   └── dashboard.json        # Экспортированный дашборд Grafana
├── ml_service/
│   ├── app.py                # FastAPI сервис с метриками
│   ├── Dockerfile
│   └── requirements.txt
├── HW8_Monitoring_filled.ipynb  # Заполненный ноутбук (все 5 шагов)
├── screenshots/              # Скриншоты дашборда и алертов
└── README.md
```

---

## Шаг 1 — Запуск стека

```bash
docker compose up --build -d
```

Сервисы:
- **Prometheus** → http://localhost:9090
- **Grafana** → http://localhost:3000  (admin / admin)
- **ML Service** → http://localhost:8000/docs
- **PostgreSQL** → localhost:5432

---

## Шаг 2 — Настройка Grafana

1. Откройте http://localhost:3000, войдите (admin/admin).
2. **Connections → Data Sources → Add → Prometheus** → URL: `http://prometheus:9090`.
3. **Dashboards → Import** → вставьте `grafana/dashboard.json`.
4. Дашборд покажет три панели: p95 latency, error rate, availability.

PromQL для p95 latency:
```promql
histogram_quantile(0.95, sum(rate(request_latency_seconds_bucket[5m])) by (le))
```

---

## Шаг 3 — Проверка алерта

Включаем режим искусственной задержки (имитация деградации):

```bash
docker compose stop ml-service
SLOW_MODE=true docker compose up ml-service -d
```

Или локально:
```bash
SLOW_MODE=true python ml_service/app.py
```

Генерируем нагрузку:
```bash
# простой load test
for i in $(seq 1 200); do curl -s "http://localhost:8000/predict?feature=$i" > /dev/null; done
```

Через ~2 минуты в Grafana и Prometheus появится алерт **HighLatency** (FIRING).

---

## Шаг 4 — Дрифт данных (Evidently)

```bash
pip install evidently scikit-learn
jupyter notebook HW8_Monitoring_filled.ipynb
```

Ячейка Шаг 3 в ноутбуке запускает `evidently.Report` с `DataDriftPreset`.  
`current_data = X * 1000` — симуляция сенсорного сбоя.

---

## Шаг 5 — DQOps (качество данных)

```bash
pip install dqops
python -m dqops          # → http://localhost:8080
```

SQL для воспроизведения инцидента — в ячейке 4 ноутбука (`SQL_BREAK`):
- изменяем тип столбца `temperature TEXT`
- вставляем `NULL` и строки вместо чисел
- DQOps обнаруживает нарушение проверок → вкладка **Incidents**

---

## Шаг 6 — Архитектурная схема (Diagrams)

```bash
pip install diagrams
apt-get install graphviz
```

Ячейка 5 ноутбука генерирует схему Kappa-архитектуры для системы **Virtual Product Placement**.

**Выбор архитектуры: Kappa**, т.к.:
- данные — непрерывный видеопоток (нет batch-слоя)
- требуется низкая задержка (реальное время)
- кадры хорошо параллелизируются через Kafka partitions
- Lambda избыточна: отдельный batch-слой не нужен

---

## Скриншоты

> Добавьте в папку `screenshots/` после запуска:
> - `01_grafana_dashboard.png` — дашборд с тремя панелями
> - `02_alert_firing.png` — алерт HighLatency в состоянии FIRING
> - `03_prometheus_targets.png` — /targets в Prometheus (ml_service UP)
> - `04_evidently_drift.png` — отчёт Evidently с обнаруженным дрифтом
> - `05_dqops_incident.png` — вкладка Incidents в DQOps
> - `06_kappa_diagram.png` — схема Kappa-архитектуры
