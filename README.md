# Accent-Aware Multilingual Translator — Streamlit

A Streamlit-only multilingual translator. Translation requests are sent server-side to OpenRouter; text-to-speech uses Edge neural voices.

## Features
- Auto-detect or manually select the source language.
- Translate into Spanish, French, German, Italian, Portuguese, Japanese, Korean, Simplified Chinese, English, Hindi, Arabic, Kannada, Telugu, Tamil, Malayalam, Marathi, Urdu, and Bhojpuri.
- Natural, formal, conversational, and literal styles.
- Indian, British, American, and Australian English output preferences.
- Neural speech with female/male voices, adjustable speed, and text/audio downloads.

## Run locally
1. Create and activate a Python virtual environment.
2. Run `pip install -r requirements.txt`.
3. Create `.streamlit/secrets.toml` with:

```toml
OPENROUTER_API_KEY = "your_openrouter_api_key"
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
```

4. Run `streamlit run app.py`.

## Deploy on Streamlit Community Cloud
1. Open https://share.streamlit.io and sign in with GitHub.
2. Create an app using this repository, branch `main`, and main file `app.py`.
3. In Advanced settings > Secrets, add the two TOML values shown above.
4. Deploy.

Never commit API keys, `.env` files, or `.streamlit/secrets.toml`. OpenRouter free models may be rate-limited or unavailable; change OPENROUTER_MODEL in Streamlit Secrets when needed.

Note: Bhojpuri uses a Hindi neural voice fallback for audio; it is not a dedicated Bhojpuri voice.

Windows PowerShell local setup:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```