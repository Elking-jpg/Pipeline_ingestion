library(DBI)
library(RPostgres)
library(ggplot2)


#Abrir el puente con la Base de Datos
con <- dbConnect(
  RPostgres::Postgres(),
  dbname   = "postgres",
  user     = "postgres",
  password = "1234",
  host     = "localhost",
  port     = 5432
)


# query para los datos de Manta
query_manta <- "
  SELECT 
    measurement_date::text AS Date,
    measurement_time::text AS Hour,
    fw.radiation,
    fw.cloud_cover,
    fw.humidity
  FROM fact_weather_measurement AS fw
  INNER JOIN dim_location AS dl ON fw.location_id = dl.location_id
  WHERE dl.city_name = 'Manta'
  
  ORDER BY measurement_time ASC;
"


df_manta <- dbGetQuery(con, query_manta)


dbDisconnect(con)




# -------------------------------- PLOT------------------------------
ggplot(data = df_manta, aes(x = radiation, y = humidity)) +
  geom_point(color = "#34495e", alpha = 0.5, size = 2) +
  geom_smooth(method = "lm", color = "#c0392b", linewidth = 1.2) +
  theme_minimal(base_size = 14) +
  labs(
    title = "Análisis de Correlación Térmica en Manta",
    subtitle = "Evidencia estocástica del impacto de la radiación sobre la humedad relativa",
    x = "Radiación Solar (W/m²)",
    y = "Humedad Relativa (%)"
  )

