import requests
import pandas as pd


URL = "https://api.open-meteo.com/v1/forecast?latitude=-34.6037&longitude=-58.3816&hourly=shortwave_radiation,relative_humidity_2m,direct_radiation,cloud_cover&current=cloud_cover,relative_humidity_2m&timezone=auto&start_date=2026-03-06&end_date=2026-06-12"

headers_config = {
    "User-Agent": "AstronomyPipeline/1.0",
    "Accept": "application/json"
}

crudo = requests.get(URL, headers=headers_config)
datos = crudo.json()
estado = crudo.status_code

if estado == 200:
    hourly_data = datos["hourly"]

    # 1. Temporal extraction from the parsed series index
    fecha_dt = pd.to_datetime(hourly_data["time"])
    
    

    # 2. Build the baseline dimensional DataFrame
    df = pd.DataFrame({
        "radiation": hourly_data["shortwave_radiation"],
        "cloud_cover": hourly_data["cloud_cover"],
        "humidity": hourly_data["relative_humidity_2m"]
    })
    
    # 3. Time-series feature engineering: isolate chronological dimensions
    df["date"] = fecha_dt.date  # Extracts YYYY-MM-DD
    df["time"] = fecha_dt.time  # Extracts HH:MM:SS
    
    # 4. Set temporal index to perform vector operations
    df.set_index("date", inplace=True)
    
    # 5. Data cleaning pipeline
    df.dropna(inplace=True)                     # Purge null records
    df_diurnal = df[df["radiation"] > 0].copy()  # Filter nocturnal noise out (radiation > 0)
    
    # 6. Database ingestion preparation (Reset index to expose 'date' as a regular column)
    df_final = df_diurnal.reset_index()
    
    # 7. Structural normalization: drop static variables (lat, long, elevation)
    # These metrics belong strictly to Table 1 (Dim_City) to preserve data normalization rules.
    # The 'city_id' Foreign Key will be appended during the database insertion transaction loop.
    df_final = df_final[["date", "time", "radiation", "cloud_cover", "humidity"]]
    
    print("\n=== METADATA PIPELINE: READY FOR POSTGRESQL INGESTION ===")
    print(df_final.head(10))



    


# dataframe con los 


























# prueba del calulo de la declinación solar
# constante solar teórica: I_0 = 1361 W/m^2 
# usando la ecuación general de la geometría solar: 
#   sin(α) = sin(Φ) * sin(δ) + cos(Φ) * cos(δ) * cos(h)
#  donde:
#  α = ángulo de elevación solar
#  Φ = latitud del observador
#  δ = declinación solar
#  h = ángulo horario (0 a las 12:00 solar, positivo hacia la tarde, negativo hacia la mañana)

# simplificada a: α = 90° - |Φ - δ| para el mediodía solar (h=0)

# y α se consigue mediante la ley del coseno de Lambert: I = I_0 * cos(θ) donde θ es el ángulo entre el sol y la normal a la superficie (90° - α)
# entonce α = arsen(I / I_0)

# finalmente δ = Φ +- arsen(I / I_0) 


# prueba del calulo de la declinación solar
# constante solar teórica: I_0 = 1361 W/m^2 
# usando la ecuación general de la geometría solar: 
#   sin(α) = sin(Φ) * sin(δ) + cos(Φ) * cos(δ) * cos(h)
#  donde:
#  α = ángulo de elevación solar
#  Φ = latitud del observador
#  δ = declinación solar
#  h = ángulo horario (0 a las 12:00 solar, positivo hacia la tarde, negativo hacia la mañana)

# simplificada a: α = 90° - |Φ - δ| para el mediodía solar (h=0)

# y α se consigue mediante la ley del coseno de Lambert: I = I_0 * cos(θ) donde θ es el ángulo entre el sol y la normal a la superficie (90° - α)
# entonce α = arsen(I / I_0)

# finalmente δ = Φ - arsen(I / I_0) 
