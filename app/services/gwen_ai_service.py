import requests
import streamlit as st
from typing import Tuple

GWEN_AI_BASE_URL = "https://simatoa.web.id/site/qwen"

def call_gwen_ai(prompt: str) -> Tuple[bool, str]:
    """
    Calls the Gwen AI endpoint with the given prompt.
    Fetches credentials from Streamlit secrets at the time of function call.
    Returns a tuple: (success: bool, result: str).
    The result is the AI's response (text) on success, or an error message on failure.
    """
    gwen_username_value = st.secrets.get("GWEN_USERNAME")
    gwen_password_value = st.secrets.get("GWEN_PASSWORD")

    if not gwen_username_value or not gwen_password_value:
        return False, "Gwen AI credentials (GWEN_USERNAME, GWEN_PASSWORD) are not set in Streamlit secrets."

    params = {
        "username": gwen_username_value,
        "password": gwen_password_value,
        "prompt": prompt
    }

    try:
        response = requests.get(GWEN_AI_BASE_URL, params=params)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        return True, response.text # Assuming the response is plain text from the API
    except requests.exceptions.RequestException as e:
        return False, f"Failed to get response from Gwen AI: {e}"