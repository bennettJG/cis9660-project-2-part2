# CIS 9660 Project 2 Part 2

This app uses Ollama (https://ollama.com/) in combination with the Openmeteo API (open-meteo.com) to generate clothing recommendations and/or fictional stories based on the weather given a user-specified location and date. After receiving a response, the user can send follow-up messages or try again with another question.
When running the app locally (`streamlit run chat_app.py`), you will be able to select from the Ollama models downloaded on your machine. Larger models will likely be slower to run, but more reliable. 
The Openmeteo API is available without use of a key.
The Streamlit functionality is implemented in `chat_app.py` and helper functions are in `openmeteo_request_helpers.py`.

An online version is deployed at https://huggingface.co/spaces/battaway/cis9660-project-2-part2. Because I could not get HuggingFace Spaces to serve both Ollama and Streamlit at the same time, the deployed version instead uses the Together API (https://www.together.ai/inference) to call a Llama model. Because the number of tokens available on a free account is limited, please exercise moderation in interacting with this version.
It is simple to switch the app between Together and Ollama by commenting/uncommenting a few lines of code, indicated in `chat_app.py`. Use of the Together API requires a private key.

Because the focus of this class is on machine learning rather than chatbot guardrails, it is likely fairly easy to "jailbreak" the model, i.e. get it to talk about topics other than weather.
