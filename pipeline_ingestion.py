import asyncio
import aiohttp
import time
import psycopg2
from psycopg2.extras import execute_batch
import pandas as pd
import os  

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "postgres"),  
    "user": os.getenv("DB_USER", "postgres"),   
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}



async def fetch_historical_weather(session, city):
    """
    Orchestrates the data extraction phase by combining geocoding and weather forecast endpoints.
    First resolves the city's static spatial parameters (latitude, longitude, elevation). 
    Then dynamic parameters are used to query the target time-series dataset. 
    Returns a tuple containing the target city name and its raw JSON payload with injection metadata.
    """
    geocoding_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
    headers_config = {
        "User-Agent": "AstronomyDataPipeline/1.0",
        "Accept": "application/json"
    }
    
    try:
        async with session.get(geocoding_url, headers=headers_config) as geo_response:
            if geo_response.status != 200:
                print(f"Geocoding failed for {city}: Status {geo_response.status}")
                return city, None
                
            geo_data = await geo_response.json()
            if 'results' not in geo_data or len(geo_data['results']) == 0:
                print(f"Location not found: {city}")
                return city, None
            
            latitude = geo_data['results'][0]['latitude']
            longitude = geo_data['results'][0]['longitude']
            elevation = geo_data['results'][0].get('elevation', 0.0)

        data_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=shortwave_radiation,cloud_cover,relative_humidity_2m&current=relative_humidity_2m&minutely_15=relative_humidity_2m&timezone=auto&start_date=2026-06-06&end_date=2026-06-16"
            
        async with session.get(data_url, headers=headers_config) as data_response:
            if data_response.status == 200:
                raw_data = await data_response.json()
                raw_data['metadata'] = {
                    'latitude' : latitude,
                    'longitude' : longitude,
                    'elevation' : elevation
                }
                return city, raw_data 
            else:
                print(f"Archive API failed for {city}: Status {data_response.status}")
                return city, None
                
    except Exception as execution_error:
        print(f"Architectural exception processing '{city}': {execution_error}")
        return city, None



def save_to_postgresql(city_name, df, metadata):

    """
    Handles data ingestion into the PostgreSQL relational schema.
    Executes a continuous transactional workflow: performs an UPSERT on the dimensional table 
    (dim_location) to secure the foreign key reference, unpacks the DataFrame rows into standard 
    Python tuples, and triggers a bulk insertion into the fact table (fact_weather_measurement) 
    via cursor execution batches. 
    """

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        upsert_city_query = """
            INSERT INTO dim_location (city_name, latitude, longitude, elevation)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (city_name) DO UPDATE 
            SET city_name = EXCLUDED.city_name
            RETURNING location_id;
        """
        cursor.execute(upsert_city_query, (city_name, metadata['latitude'], metadata['longitude'], metadata['elevation']))
        location_id = cursor.fetchone()[0]
        
        df_ingest = df.copy()
        df_ingest['location_id'] = location_id
        
        records_to_insert = list(df_ingest[['location_id', 'date', 'time', 'radiation', 'cloud_cover', 'humidity']].itertuples(index=False, name=None))
        
        bulk_insert_query = """
            INSERT INTO fact_weather_measurement (location_id, measurement_date, measurement_time, radiation, cloud_cover, humidity)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT unique_location_timestamp DO NOTHING;
        """
        
        execute_batch(cursor, bulk_insert_query, records_to_insert)
        
        conn.commit()
        print(f"--> Database Ingestion Success: {len(records_to_insert)} records stored for {city_name} (ID: {location_id}).")
        
        cursor.close()
        conn.close()
        
    except Exception as db_error:
        print(f"Database transaction aborted for {city_name}: {db_error}")


async def main():

    """
    Main orchestrator for the asynchronous ETL pipeline execution.
    Manages concurrent network request dispatches using an internal wrapper constrained by an 
    asyncio.Semaphore to handle API rate-limiting. Once data is gathered, iterates through the payloads 
    to execute data cleaning, vectorized date-time parsing, and diurnal filtering before pushing records 
    to the target database.
    """

    target_cities = [
        "Buenos Aires",
        "New York",
        "Tokyo",
        "Quito",
        "Manta",
        "Reykjavik",
        "Cairo",
        "Singapore",
        "Sydney",
        "Calgary",
        "Chone",
        "Guayaquil"
    ] 

    sem = asyncio.Semaphore(3)

    async def wrapper(session, city):
        
        async with sem: 
            return await fetch_historical_weather(session, city)

    print("=== STARTING ASYNCHRONOUS EXTRACT PHASE ===")
    async with aiohttp.ClientSession() as session:

        tasks = [wrapper(session, city) for city in target_cities]
        concurrency_results = await asyncio.gather(*tasks)
        



        print("\n=== STARTING PANDAS TRANSFORM PHASE ===")
        for city, raw_json in concurrency_results:
            if not raw_json or 'hourly' not in raw_json:
                call = f"Skipping transformation for: {city} (No data returned), raw json type: {type(raw_json)}"
                if type(raw_json) == dict: call = call + f', hourly in raw_json: {('hourly' in raw_json)}'
                print(call)

                continue
                
            hourly_data = raw_json["hourly"]
            metadata = raw_json['metadata']
            timestamp_dt = pd.to_datetime(hourly_data["time"])
            

            df = pd.DataFrame({
                "radiation": hourly_data["shortwave_radiation"],
                "cloud_cover": hourly_data["cloud_cover"],
                "humidity": hourly_data["relative_humidity_2m"]
            })
     
            df["date"] = timestamp_dt.date
            df["time"] = timestamp_dt.time
            df.set_index("date", inplace=True)
            

            df.dropna(inplace=True)
            df_diurnal = df[df["radiation"] > 0].copy()
            df_final = df_diurnal.reset_index()
            
            save_to_postgresql(city, df_final, metadata)



if __name__ == "__main__":  
    start_benchmark = time.time()
    asyncio.run(main())
    end_benchmark = time.time()
    print(f"\nTotal Pipeline Execution Time: {end_benchmark - start_benchmark:.2f} seconds")
    

