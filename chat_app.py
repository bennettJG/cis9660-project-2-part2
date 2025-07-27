import streamlit as st
import numpy as np
import pandas as pd
import requests_cache
from retry_requests import retry
from tzfpy import get_tz
import ollama
import pytz
from geopy.geocoders import Nominatim
import openmeteo_requests
from typing import Dict, Generator
from datetime import date, datetime, timedelta
import openmeteo_request_helpers as helpers

geolocator = Nominatim(user_agent="CIS 9660 Project 2 Weather App")
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

st.title("How's the weather today?")

if 'messages' not in st.session_state:
    st.session_state.messages = []

def ollama_generator(messages: Dict) -> Generator:
    stream = ollama.chat(
        model="tinyllama", messages=messages, stream=True)
    for chunk in stream:
        yield chunk['message']['content']

st.set_page_config(page_title="How's the weather today?", layout="wide", page_icon="☀️")

tz=None
st.session_state.start_date = None
st.session_state.end_date=None

col1, col2, col3 = st.columns(3)

with col1:
    if location_input := st.text_input("Location (City or address)", value="NYC"):
        location = geolocator.geocode(location_input)
        lat, lon = location.latitude, location.longitude
        tz = get_tz(lon, lat)
        tz_fordatetime = pytz.timezone(get_tz(lon, lat))
        st.session_state.location = location.address
with col2:
    units = st.pills("Temperature in:", ["Fahrenheit", "Celsius"], default="Fahrenheit")
with col3:
    forecast_date = st.date_input("Date", max_value=datetime.now(tz=tz_fordatetime)+timedelta(days=14))
    selected_date = forecast_date.strftime('%Y-%m-%d')

if st.button("Tell me about the weather"):
    #try:
        forecast = helpers.openmeteo_getforecast(lat, lon, tz, units, selected_date)
        forecast_text = helpers.forecast_to_text(forecast, selected_date, units)
        st.markdown(forecast_text)
    #except Exception as e:
    #    st.markdown("Issue retrieving Openmeteo data")
    #msg = {"role":"system", "content":"Tell me about the weather"}
    #st.session_state.messages = [msg]
        
    #model = "tinyllama"
    #for message in st.session_state.messages:
    #    if (message["role"] != "system"):
    #        with st.chat_message(message["role"]):
    #            st.write(message["content"])

    #if prompt := st.chat_input("Any questions?"):
    #    # Add user message to chat history
    #    st.session_state.messages.append({"role": "user", "content": prompt})
    #    # Display user message in chat message container
    #    with st.chat_message("user"):
    #        st.markdown(prompt)
            
    #with st.chat_message("assistant"):
    #    response = st.write_stream(ollama_generator(st.session_state.messages))
        
    #    st.session_state.messages.append({"role": "assistant", "content": response})

st.markdown(st.session_state.messages)