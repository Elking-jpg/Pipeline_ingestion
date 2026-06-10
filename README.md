# Asynchronous Weather Telemetry Pipeline

An optimized, concurrent ETL data pipeline built with Python (`asyncio`/`aiohttp`) and Pandas, designed to ingest historical time-series atmospheric data into a structured PostgreSQL relational database.

## Architecture Overview

The system implements a decoupled **Star Schema** to optimize storage allocation and speed up analytical queries by separating static spatial variables from high-frequency telemetry metrics.

* **`dim_location`**: Stores immutable dimensional parameters (City Name, Coordinates, Elevation).
* **`fact_weather_measurement`**: Stores structural metrics sampled hourly (Shortwave Radiation, Cloud Cover, Relative Humidity).

### Data Flow & Engineering Safeguards

1. **Concurrency & Rate-Limiting**: Instead of sequential, blocking requests, the ingestion phase handles multiple target cities simultaneously utilizing an `asyncio.Semaphore(3)` constraint. This prevents throttling and guarantees compliance with external API limits (HTTP 429 mitigation).
2. **Timezone Alignment**: Leverages localized coordinate mapping (`&timezone=auto`) directly at the extraction layer. This ensures accurate diurnal filtering (`radiation > 0`) within Pandas before database mapping, preventing UTC time-shifting bugs on the analytical frontend.
3. **Idempotency & Upserts**: The persistence layer uses defensive programming. It performs an atomic `UPSERT` on the location dimension and implements a composite unique key constraint (`unique_location_timestamp`) on the fact table, serving as an idempotency shield during pipeline re-runs.

---

## Technical Features

* **Asynchronous I/O Bound Operations**: Built using `aiohttp` to maximize throughput during multi-target network operations.
* **Vectorized Data Profiling**: Time-series extraction parsed via `pandas` for efficient memory management, date-time transformations, and data cleaning.
* **Mass Insertion Performance**: Database operations use `psycopg2.extras.execute_batch` to perform bulk inserts, reducing relational transaction overhead significantly compared to iterative raw executions.
* **Secure Infrastructure Environment**: Tailored to infrastructure standards using `os.getenv` to pull credential parameters from the environment instead of exposure in code blocks.

---

## System Scalability Strategy

This prototype is structurally prepared for seamless migration to an enterprise cloud architecture:
* **Orchestration**: The pipeline execution logic is encapsulated to be wrapped inside a lightweight Docker container and scheduled daily via orchestrators such as **Apache Airflow**.
* **Target Warehouse Scaling**: Connection parameters allow transitioning from local PostgreSQL to managed cloud data warehouses like **Snowflake** or **BigQuery** by swapping the interface driver layer without altering core parsing mechanics.
