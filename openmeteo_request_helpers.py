import streamlit as st
import openmeteo_requests
import requests_cache
from retry_requests import retry

def openmeteo_getaqi():
    aqi_api = "https://air-quality-api.open-meteo.com/v1/air-quality"
    aqi_params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": tz,
        "hourly": ["pm10", "pm2_5", "us_aqi", "us_aqi_pm2_5", "us_aqi_pm10", "us_aqi_nitrogen_dioxide", "us_aqi_ozone", "us_aqi_sulphur_dioxide", "us_aqi_carbon_monoxide", "uv_index", "dust"],
     "current": ["pm10", "pm2_5", "carbon_monoxide", "nitrogen_dioxide", "sulphur_dioxide", "ozone", "dust", "uv_index"]
    }
    aqi_response = openmeteo.weather_api(aqi_api, params=aqi_params)[0]

def openmeteo_getforecast(lat, lon, tz, start_date, end_date=None):
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    if end_date is None:
        end_date = start_date
    forecast_api = "https://api.open-meteo.com/v1/forecast"
    forecast_params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": tz,
        "daily": ["temperature_2m_max", "temperature_2m_min", "apparent_temperature_max", "apparent_temperature_min", "precipitation_probability_max", "wind_speed_10m_max", "uv_index_max"],
        "hourly": ["temperature_2m", "apparent_temperature", "precipitation_probability", "rain", "showers", "snowfall", "wet_bulb_temperature_2m"],
        "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation", "rain", "showers", "snowfall", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"],
        "start_date":start_date,
        "end_date":end_date
    }
    if (st.session_state.likely_us):
        forecast_params = forecast_params | {"wind_speed_unit": "mph", "temperature_unit": "fahrenheit", "precipitation_unit": "inch"}
    try:
        st.markdown(forecast_params)
        forecast_response = openmeteo.weather_api(forecast_api, params=forecast_params)[0]
        st.markdown(openmeteo.weather_api(forecast_api, params=forecast_params)[0])
        
    except Exception as e:
        return("Forecast not available")