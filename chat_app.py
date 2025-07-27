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
        st.session_state.likely_us = "United States" in location.address
with col2:
    if day_or_week := st.pills("Hear about weather for", ["A specific day", "This week"], default="A specific day") == "A specific day":
        forecast_type = "day"
    else:
        forecast_type="week" 
        st.session_state.start_date = datetime.now(tz=tz_fordatetime).strftime('%Y-%m-%d')
        st.markdown(st.session_state.start_date)
        st.session_state.end_date = (datetime.now(tz=tz_fordatetime)+timedelta(days=7)).strftime('%Y-%m-%d')
with col3:
    if forecast_type == "day":
        forecast_date = st.date_input("What day's weather are you interested in?", min_value=datetime.now(tz=tz_fordatetime), max_value=datetime.now(tz=tz_fordatetime)+timedelta(days=14))
        st.session_state.start_date = forecast_date.strftime('%Y-%m-%d')

if st.button("Tell me about the weather"):
    forecast = helpers.openmeteo_getforecast(lat, lon, tz, st.session_state.start_date, st.session_state.end_date)
    st.markdown(forecast)
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