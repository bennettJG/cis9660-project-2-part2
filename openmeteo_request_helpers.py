import streamlit as st
import pandas as pd
import numpy as np
import openmeteo_requests
import requests_cache
from retry_requests import retry
from datetime import datetime, timedelta
import pytz
from tzfpy import get_tz

# Dictionary for meanings of weather codes returned by Openmeteo API
# (https://open-meteo.com/en/docs#weather_variable_documentation)
weather_codes = {
    0: 'Clear sky',
    1: 'Mainly clear',
    2: 'Partly cloudy',
    3: 'Overcast',
    45: 'Fog',
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

# Air quality index API, not currently used but could be incorporated later if needed
def openmeteo_getaqi():
    aqi_api = "https://air-quality-api.open-meteo.com/v1/air-quality"
    aqi_params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": tz,
        "current": ["us_aqi"],
    }
    aqi_response = openmeteo.weather_api(aqi_api, params=aqi_params)[0]

# Convert numeric values from API into something more legible for both the user and the model.
def forecast_to_text(forecast_dict, selected_date, units, location):
    # Match tense to the date input -- "was" if it's in the past, "is" if it's today, "will be" if it's in the future
    match forecast_dict['when']:
        case "past":
            verb = "was"
            verb2 = "were"
        case "present":
            verb = "is"
            verb2 = "are"
        case "future":
            verb = "will be"
            verb2 = "will be"
    text = f"Weather for {location} on {datetime.strftime(datetime.strptime(selected_date, '%Y-%m-%d').astimezone(forecast_dict['tz']), '%A, %B %d, %Y')}:"        
    if 'current' in forecast_dict and forecast_dict['when'] == "present":
        current = forecast_dict['current']
        text += f"\n\nThat's today! It is currently {'daytime' if current['is_day'] else 'nighttime'}. Right now, the weather is {weather_codes[current['weather_code']].lower()}. The temperature is {round(current['temperature_2m'])} {units} (feels like {round(current['apparent_temperature'])} {units}). The wind speed is {round(current['wind_speed_10m'])} {'miles per hour' if units=='Fahrenheit' else 'kilometers per hour'}. The humidity is {round(current['relative_humidity_2m'])} percent."
    daily = forecast_dict['daily'].iloc[0]
    
    text += f"\n\nThe overall conditions for the day {verb2} {weather_codes[daily['weather_code']].lower()}. The high temperature {verb} {round(daily['temperature_2m_max'])} {units} (feels like {round(daily['apparent_temperature_max'])} {units}) and the low temperature {verb} {round(daily['temperature_2m_min'])} {units} (feels like {round(daily['apparent_temperature_min'])} {units}). The maximum wind speed {verb} {round(daily['wind_speed_10m_max'])} {'miles per hour' if units=='Fahrenheit' else 'kilometers per hour'}."

    return text
    
# Openmeteo API caller
# Input variables: Geocoded location (obtained from geocoder, has latitude and longitude properties), temperature units (Fahrenheit, Celsius), date in YYYY-MM-DD format
def openmeteo_getforecast(location, units, selected_date):
    lat, lon = location.latitude, location.longitude
    tz = get_tz(lon, lat)
    
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)
    tz_fordatetime = pytz.timezone(get_tz(lon, lat))

    daily_vars = ["weather_code", "temperature_2m_max", "temperature_2m_min", "apparent_temperature_max", "apparent_temperature_min", "wind_speed_10m_max"]
    current_vars = ["weather_code", "temperature_2m", "apparent_temperature",  "wind_speed_10m", "is_day", "relative_humidity_2m"]
    
    if datetime.now(tz=tz_fordatetime)-datetime.strptime(selected_date, '%Y-%m-%d').astimezone(tz_fordatetime) >= timedelta(days=3):
        # If date is more than a couple days in the past, need to use the historical data API rather than forecasts
        historical_api = "https://archive-api.open-meteo.com/v1/archive"
        historical_params = {
            "latitude": lat,
            "longitude": lon,
            "timezone": tz,
            "daily": daily_vars,
            "start_date":selected_date,
            "end_date":selected_date
        }
        if (units=="Fahrenheit"):
            historical_params = historical_params | {"wind_speed_unit": "mph", "temperature_unit": "fahrenheit", "precipitation_unit": "inch"}
        historical_response = openmeteo.weather_api(historical_api, params=historical_params)[0]
        
        daily = historical_response.Daily()
        daily_response = pd.DataFrame(list(map(lambda i: daily.Variables(i).ValuesAsNumpy(), range(0, daily.VariablesLength()))), index = daily_vars).T
        return forecast_to_text({'daily': daily_response, 'when':'past', 'tz':tz_fordatetime}, selected_date, units, location)

    else:
        # Use forecasts API
        forecast_api = "https://api.open-meteo.com/v1/forecast"
        forecast_params = {
            "latitude": lat,
            "longitude": lon,
            "timezone": tz,
            "daily": daily_vars,
            "current": current_vars,
            "start_date":selected_date,
            "end_date":selected_date
        }
        if (units=="Fahrenheit"):
            forecast_params = forecast_params | {"wind_speed_unit": "mph", "temperature_unit": "fahrenheit", "precipitation_unit": "inch"}
        forecast_response = openmeteo.weather_api(forecast_api, params=forecast_params)[0]
        
        daily = forecast_response.Daily()
        daily_response = pd.DataFrame(list(map(lambda i: daily.Variables(i).ValuesAsNumpy(), range(0, daily.VariablesLength()))), index = daily_vars).T
        
        # Figure out when the date is relative to now, so that the text can refer to it properly
        when = 'future'
        if (datetime.now(tz=tz_fordatetime) > datetime.strptime(selected_date, '%Y-%m-%d').astimezone(tz_fordatetime)):
            when = 'past'
            if(datetime.now(tz=tz_fordatetime) < datetime.strptime(selected_date, '%Y-%m-%d').astimezone(tz_fordatetime) + timedelta(hours=23.999)):
                when = 'present'
    
        current = forecast_response.Current()
        current_response = list(map(lambda i: current.Variables(i).Value(), range(0, current.VariablesLength())))
        current_response = dict(zip(current_vars, current_response))
        return forecast_to_text({'daily': daily_response, 'current':current_response, 'when':when, 'tz':tz_fordatetime}, selected_date, units, location)

