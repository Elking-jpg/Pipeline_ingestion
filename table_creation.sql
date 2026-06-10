/*
PostgreSQL 14+

This schema models time-series environmental and astronomical telemetry. 
By decoupling static spatial attributes from high-frequency structural metrics, 
the layout optimizes storage allocation, speeds up dynamic indexing, and 
guarantees relational consistency across bulk concurrent ingestion cycles.

*/

CREATE TABLE dim_location (
    location_id SERIAL PRIMARY KEY,
    city_name VARCHAR(100) UNIQUE NOT NULL,
    latitude NUMERIC(7, 4) NOT NULL,
    longitude NUMERIC(7, 4) NOT NULL,
    elevation NUMERIC(6, 2) NOT NULL
);

CREATE TABLE fact_weather_measurement (
    measurement_id SERIAL PRIMARY KEY,
    location_id INT NOT NULL,
    measurement_date DATE NOT NULL,
    measurement_time TIME NOT NULL,
    radiation FLOAT NOT NULL,
    cloud_cover INT NOT NULL,
    humidity INT NOT NULL,
        
    /* 
    The unique_location_timestamp composite constraint acts as a defensive 
    idempotency shield, preventing duplicate row allocation during incremental pipelines.
    */
    
    CONSTRAINT unique_location_timestamp UNIQUE (location_id, measurement_date, measurement_time),
    
    CONSTRAINT fk_location FOREIGN KEY (location_id) 
        REFERENCES dim_location(location_id) 
        ON DELETE CASCADE
);