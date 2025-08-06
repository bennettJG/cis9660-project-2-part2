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
from dotenv import load_dotenv
from together import Together

# Initialize geocoder
geolocator = Nominatim(user_agent="CIS 9660 Project 2 Weather App")
# Initialize client and set up retry requests for Openmeteo API
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# load virtual environment and initialize client for Together API (alternative to Ollama for Streamlit deployment, limited tokens. If you wish to use this option locally, you need a TOGETHER_API_KEY saved to your virtual environment.)
# load_dotenv()
# together_client = Together()

# Error messages to show if model is unable to be reached
model_unavailable_responses = {'ollama': "Please check that Ollama is running and the model you've selected is available!",
'together': "The Together API is currently not available (perhaps the token quota has been reached). Please try again later!"}

# Ollama models currently available on user's computer
ollama_models = [model["model"] for model in ollama.list()["models"]]

st.title("How's the weather?")

# Initialize session variables and basic system prompt. Because the user submitting a message causes the app to refresh, most things have to be stored as session state.
if 'messages' not in st.session_state:
    st.session_state.chat_enabled = False
    st.session_state.sys_temp = 0.4
    st.session_state.sys_prompt = 'You are a weather assistant designed to help users explore past, current, and forecasted weather conditions around the world. If the user asks a question unrelated to the weather or location you have been told about, redirect them by suggesting they choose a new location or date for weather information. If they ask a follow-up question about the weather, use the forecast you have already been provided to answer. If they ask for a different forecast, explain that they need to use the controls at the top of the page to select a location and date.'
    st.session_state.messages = [{'role':'system', 'content':st.session_state.sys_prompt}]
    st.session_state.forecast_text=""

# Function to stream messages from Ollama with a given model and temperature
def ollama_generator(messages: Dict, temp: float, model: str) -> Generator:
    try:
        stream = ollama.chat(
            model=model, messages=messages, stream=True, options={'temperature':temp})
        for chunk in stream:
            yield chunk['message']['content']
    except Exception as e:
        yield model_unavailable_responses['ollama']
        
# Function to stream messages from Together API with a given temperature. I didn't allow the model to be selected here although Together does offer different options, because I didn't want the user to choose a token-hungry one and burn through my free allowance.
def together_generator(messages: Dict, temp: float) -> Generator:
    try:
        stream = client.chat.completions.create(
          model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
          messages=messages, stream=True, options={'temperature':temp}
        )
        for chunk in stream:
            yield(chunk.choices[0].delta.content)
    except Exception as e:
        yield model_unavailable_responses['together']
           
st.set_page_config(page_title="How's the weather?", layout="wide", page_icon="☀️")

tz=None

col1, col2, col3, col4 = st.columns(4)

with col1:
    # Use geocoder to convert user input to lat/lon, which are needed for Openmeteo API call. If the location can't be parsed by the geocoder, display an error message.
    location_input = st.text_input("Location (City or address)", value="NYC")
    if location_input:
        try:
            location = geolocator.geocode(location_input)
            lat, lon = location.latitude, location.longitude
            tz = get_tz(lon, lat)
            tz_fordatetime = pytz.timezone(get_tz(lon, lat))
        except Exception as e:
            st.markdown("Please input a valid location!")
    else:
        st.markdown("Please input a valid location!")
with col2:
    units = st.pills("Temperature in:", ["Fahrenheit", "Celsius"], default="Fahrenheit")
with col3:
    forecast_date = st.date_input("Date", max_value=datetime.now()+timedelta(days=14))
    selected_date = forecast_date.strftime('%Y-%m-%d')
with col4:
    st.session_state["model"] = st.selectbox("Choose your model", ollama_models)
    
# Prompt model for clothing recommendations and write response, then enable chat for follow-up question.
# tinyllama will frequently violate the prompt instructions no matter how specific I make them, so if you are able to run a more powerful model locally I would recommend that.
def get_clothing_recs():
    reset_chat()
    try:
       if location:
           pass
       try:
           # Call helper function to retrieve weather forecast from API
           st.session_state.forecast_text = helpers.openmeteo_getforecast(location, units, selected_date)
           st.session_state.sys_prompt = f'Suggest appropriate clothing and accessories for the following weather. When making suggestions, consider whether the clothing would be comfortable given the predicted high and low temperatures and the weather conditions. If the date given is in the past, discuss what would have been good to wear and bring when spending time outside. Keep the response brief but informative, paying attention to whether the weather is hot, cold, or in between. Do not recommend scarves, jackets, or multiple layers if the weather is hot, and do not recommend lightweight clothing if it is cold. {st.session_state.forecast_text} What are your clothing suggestions?'
           st.session_state.messages = [{'role':'system', 'content':st.session_state.sys_prompt}]
           st.session_state.sys_temp = 0.5
       except Exception as e:
           st.session_state.sys_prompt = 'Explain to the user that the API used to collect weather information cannot currently be reached.'
           st.session_state.sys_temp = 0.2
    except Exception as e:
       st.session_state.sys_prompt = 'Explain to the user that the location they input was not valid and ask them to try again.'
       st.session_state.sys_temp = 0.2   
    with chat_area.container():
        with st.chat_message("assistant"):  
            response = st.write_stream(ollama_generator([{'role':'system', 'content': st.session_state.sys_prompt}], st.session_state.sys_temp, st.session_state.model))
            # Comment out above line and uncomment this one to use Together instead of Ollama
            #response = st.write_stream(together_generator([{'role':'system', 'content': st.session_state.sys_prompt}], st.session_state.sys_temp, st.session_state.model))
            if (not (response in model_unavailable_responses.values())):
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.session_state.chat_enabled = True
# Get story function (same as above, the only things different are higher temperature for more "creativity" and different prompt of course.           
def get_story():
    reset_chat()
    try:
        if location:
            pass
        try:
            st.session_state.forecast_text = helpers.openmeteo_getforecast(location, units, selected_date)
            st.session_state.sys_prompt = f"You will be given a description of a location and its weather conditions at a specific date and time. Based on this information, write a short story about a character in this location. Describe how the weather makes the character feel, what they choose to do with their day, and why they chose that activity. {st.session_state.forecast_text}. Make sure that your story is consistent with the information provided. For example, if the weather described is rainy and cold, do not describe a sunny day."
            st.session_state.messages = [{'role':'system', 'content':st.session_state.sys_prompt}]
            st.sys_temp = .9
            st.session_state.chat_enabled = True
        except Exception as e:
            st.session_state.sys_prompt = 'Explain to the user that the API used to collect weather information cannot currently be reached.'
            st.session_state.sys_temp = 0.1
    except Exception as e:
        st.session_state.sys_prompt = 'Explain to the user that the location they input was not valid and ask them to try again.'
        st.session_state.sys_temp = 0.2   
    with chat_area.container():
        with st.chat_message("assistant"):  
            response = st.write_stream(ollama_generator([{'role':'system', 'content': st.session_state.sys_prompt}], st.session_state.sys_temp, st.session_state.model))
            # Comment out above line and uncomment this one to use Together instead of Ollama
            #response = st.write_stream(together_generator([{'role':'system', 'content': st.session_state.sys_prompt}], st.session_state.sys_temp, st.session_state.model))
            if (not (response in model_unavailable_responses.values())):
                st.session_state.chat_enabled = True
                st.session_state.messages.append({"role": "assistant", "content": response})

col4, col5, col6, col7 = st.columns(4)
with col4:
    st.button("What should I wear?", on_click=get_clothing_recs)
with col5:
    st.button("Tell me a story set in this place and time", on_click=get_story)

st.markdown("---")
chat_area = st.empty()
chat_input_area = st.empty()

# Chat display area
container = chat_area.container()
container2 = chat_input_area.container()
with container:
    if st.session_state.chat_enabled:
        for message in st.session_state.messages:
            if message['role'] != 'system':
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
with container2:
    if st.session_state.chat_enabled:
        if prompt := st.chat_input("Ask a follow-up question, or use the controls at the top of the page for a new request!", key="chat input"):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            with container:
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):  
                    response = st.write_stream(ollama_generator(st.session_state.messages, st.session_state.sys_temp, st.session_state.model))
                    # Comment out above line and uncomment this one to use Together instead of Ollama
                    #response = st.write_stream(together_generator([{'role':'system', 'content': st.session_state.sys_prompt}], st.session_state.sys_temp, st.session_state.model))
                    st.session_state.messages.append({"role": "assistant", "content": response})

# Reset message history when one of the buttons is pressed
def reset_chat():
    st.session_state.sys_prompt = 'You are a weather assistant designed to help users explore past, current, and forecasted weather conditions around the world. If the user asks a question unrelated to the weather or location you have been told about, redirect them by suggesting they choose a new location or date for weather information. If they ask a follow-up question about the weather, use the forecast you have already been provided to answer. If they ask for a different forecast, explain that they need to use the controls at the top of the page to select a location and date.'
    st.session_state.messages = [{'role':'system', 'content':st.session_state.sys_prompt}]
    st.session_state.forecast_text = ""
    st.session_state.chat_enabled = False
    chat_area.empty()
    chat_input_area.empty()
    
st.markdown("---")
if st.button("Reset"):
    reset_chat()

if((st.session_state.forecast_text!="") & st.session_state.chat_enabled):
    st.markdown(":warning: **Generative AI outputs can be inaccurate. Verify output against the data from Openmeteo API:**")
    st.markdown(st.session_state.forecast_text)