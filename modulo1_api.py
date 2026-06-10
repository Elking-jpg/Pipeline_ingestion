import time
import requests
import pandas as pd

def fetch_historical_weather_sync(city):
    """
    Synchronously fetches geocoding coordinates and extracts historical 
    climatological time-series data using requests.
    """
    geocoding_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
    headers_config = {
        "User-Agent": "AstronomyDataPipeline/1.0",
        "Accept": "application/json"
    }
    
    try:
        # Step 1: Synchronous Geocoding Resolution (Blocking)
        geo_response = requests.get(geocoding_url, headers=headers_config)
        if geo_response.status_code == 200:
            geo_data = geo_response.json()
            if 'results' in geo_data and len(geo_data['results']) > 0:
                latitude = geo_data['results'][0]['latitude']
                longitude = geo_data['results'][0]['longitude']
            else:
                print(f"Location not found: {city}")
                return None
        else:
            print(f"Geocoding failed for {city}: Status {geo_response.status_code}")
            return None

        # Step 2: Synchronous Archive Time-Series Extraction (Blocking)
        data_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=shortwave_radiation,relative_humidity_2m,direct_radiation,cloud_cover&current=cloud_cover,relative_humidity_2m&timezone=auto&start_date=2026-03-06&end_date=2026-06-12"
            
        data_response = requests.get(data_url, headers=headers_config)
        if data_response.status_code == 200:
            return data_response.json()
        else:
            print(f"Archive API failure for {city}: Status {data_response.status_code}")
            return None
                
    except Exception as execution_error:
        print(f"Exception processing '{city}': {execution_error}")
        return None

def main():
    target_cities = ["Buenos Aires", "New York", "Tokyo", "Quito", "Manta"]
    
    print("=== STARTING SYNCHRONOUS EXTRACT PHASE (BLOCKING) ===")
    
    for city in target_cities:
        raw_json = fetch_historical_weather_sync(city)
        
        if not raw_json or 'hourly' not in raw_json:
            print(f"Skipping transformation for: {city}")
            continue
            
        print(f"\n=== STARTING PANDAS TRANSFORM PHASE FOR {city.upper()} ===")
        hourly_payload = raw_json["hourly"]
        timestamp_dt = pd.to_datetime(hourly_payload["time"])
        
        # Vectorized DataFrame construction
        df = pd.DataFrame({
            "radiation": hourly_payload["shortwave_radiation"],
            "cloud_cover": hourly_payload["cloud_cover"],
            "humidity": hourly_payload["relative_humidity_2m"]
        })
        
        # Chronological feature separation
        df["date"] = timestamp_dt.date
        df["time"] = timestamp_dt.time
        df.set_index("date", inplace=True)
        
        # Data cleansing pipeline
        df.dropna(inplace=True)
        df_diurnal = df[df["radiation"] > 0].copy()
        df_final = df_diurnal.reset_index()
        
        # Normalize structure
        df_final = df_final[["date", "time", "radiation", "cloud_cover", "humidity"]]
        
        print(f"Location Entity: {city} | Extracted Records: {len(df_final)}")
        print(df_final.head(3))

if __name__ == "__main__":  
    start_benchmark = time.time()
    main()
    end_benchmark = time.time()
    print(f"\nTotal Pipeline Execution Time (Sequential): {end_benchmark - start_benchmark:.2f} seconds")