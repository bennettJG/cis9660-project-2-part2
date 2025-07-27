import streamlit as st
import pandas as pd
import numpy as np
import openmeteo_requests
import requests_cache
from retry_requests import retry

weather_codes = {
    0: 'Clear sky',
    1: 'Mainly clear',
    2: 'Partly cloudy',
    3: 'Overcast',
    45: 'Fog'
    48: 'Depositing rime fog',
    51: 'Light drizzle',
    53: 'Moderate drizzle',
    55: 'Dense drizzle',
    56: 'Light freezing drizzle',
    57: 'Dense freezing drizzle',
    61: 'Slight rain',
    63: 'Moderate rain',
    65: 'Heavy rain',
    66: 'Light freezing rain',
    67: 'Heavy freezing rain)',
    71: 'Slight snow',
    73: 'Moderate snow',
    75: 'Heavy snow',
    77: 'Snow grains',
    80: 'Slight rain showers',
    81: 'Moderate rain showers',
    82: 'Violent rain showers',
    85: 'Slight snow showers',
    86: 'Heavy snow showers',
    95: 'Thunderstorm',
    96: 'Thunderstorm with slight hail',
    99: 'Thunderstorm with heavy hail'
}

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
    
    daily_vars = ["weather_code", "temperature_2m_max", "temperature_2m_min", "apparent_temperature_max", "apparent_temperature_min", "wind_speed_10m_max"]
    current_vars = ["weather_code", "temperature_2m", "apparent_temperature",  "wind_speed_10m", "is_day", "relative_humidity_2m"]
    if end_date is None:
        end_date = start_date
    forecast_api = "https://api.open-meteo.com/v1/forecast"
    forecast_params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": tz,
        "daily": daily_vars,
        "current": current_vars,
        "start_date":start_date,
        "end_date":end_date
    }
    if (st.session_state.likely_us):
        forecast_params = forecast_params | {"wind_speed_unit": "mph", "temperature_unit": "fahrenheit", "precipitation_unit": "inch"}
    try:
        forecast_response = openmeteo.weather_api(forecast_api, params=forecast_params)[0]
        
        daily = forecast_response.Daily()
        daily_response = pd.DataFrame(list(map(lambda i: daily.Variables(i).ValuesAsNumpy(), range(0, daily.VariablesLength()))), index = daily_vars).T
        
        current = forecast_response.Current()
        current_response = list(map(lambda i: current.Variables(i).Value(), range(0, current.VariablesLength())))
        current_response = dict(zip(current_vars, current_response))
        return {'daily': daily_response, 'current':current_response}
        
    except Exception as e:
        return("Forecast not available")