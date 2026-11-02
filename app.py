from __future__ import annotations

import os
from io import BytesIO

import requests
import streamlit as st
from gtts import gTTS
from gtts.lang import tts_langs

st.set_page_config(page_title="Accent-Aware Multilingual Translator", page_icon="🌍", layout="centered")

LANGUAGES = {
    "Spanish": ("es", "Latin"), "French": ("fr", "Latin"),
    "German": ("de", "Latin"), "Italian": ("it", "Latin"),
    "Portuguese": ("pt", "Latin"), "Japanese": ("ja", "Japanese"),
    "Korean": ("ko", "Hangul"), "Chinese (Simplified)": ("zh-CN", "Simplified Chinese"),
    "Hindi": ("hi", "Devanagari"), "Arabic": ("ar", "Arabic"),
    "Kannada (ಕನ್ನಡ)": ("kn", "Kannada"), "Telugu (తెలుగు)": ("te", "Telugu"),
    "Tamil (தமிழ்)": ("ta", "Tamil"), "Malayalam (മലയാളം)": ("ml", "Malayalam"),
    "Marathi (मराठी)": ("mr", "Devanagari"), "Urdu (اردو)": ("ur", "Urdu"),
    "Bhojpuri (भोजपुरी)": ("bho", "Devanagari"),
}
DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_CHARS = 10_000

st.markdown("""
<style>
.block-container {max-width: 900px; padding-top: 2rem; padding-bottom: 3rem;}
.hero {padding: 1.45rem 1.6rem; border: 1px solid #e3eaf7; border-radius: 20px;
       background: linear-gradient(130deg,#edf3ff,#fff); margin-bottom: 1.2rem;}
.hero h1 {margin:0 0 .3rem; color:#172744; font-size:2rem;}
.hero p {margin:0; color:#5e6b80;}
.section-label {font-weight:700; color:#263650; margin:.5rem 0 .35rem;}
footer {visibility:hidden;}
</style>
<div class="hero">
<h1>🌍 Accent-Aware Multilingual Translator</h1>
<p>Translate naturally across languages and listen to the result.</p>
</div>
""", unsafe_allow_html=True)


def secret(name: str, default: str | None = None) -> str | None:
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    return value or os.getenv(name) or default


def translate(text: str, language: str) -> str:
    key = secret("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is missing. Add it under your Streamlit app's Settings → Secrets.")
    lang_code, script = LANGUAGES[language]
    payload = {
        "model": secret("OPENROUTER_MODEL", DEFAULT_MODEL),
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": (
                f"You are an expert multilingual translator. Translate the user's text into {language}. "
                f"Preserve meaning, tone, names, numbers and formatting. Use natural native phrasing and "
                f"the correct writing system ({script}). Do not add explanations or commentary. "
                "Return only the translated text."
            )},
            {"role": "user", "content": text},
        ],
    }
    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://streamlit.io/",
                "X-Title": "Accent-Aware Multilingual Translator",
            },
            json=payload,
            timeout=60,
        )
    except requests.RequestException as exc:
        raise RuntimeError("Could not reach OpenRouter. Check your connection and try again.") from exc
    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError(f"OpenRouter returned an unreadable response (HTTP {response.status_code}).") from exc
    if not response.ok:
        detail = result.get("error", {})
        message = detail.get("message") if isinstance(detail, dict) else str(detail)
        raise RuntimeError(message or f"Translation failed (HTTP {response.status_code}).")
    choices = result.get("choices", [])
    translated = choices[0].get("message", {}).get("content") if choices else None
    if not isinstance(translated, str) or not translated.strip():
        raise RuntimeError("The translation provider returned an empty result.")
    return translated.strip()


def make_speech(text: str, language: str, slow: bool) -> tuple[bytes, str | None]:
    code = LANGUAGES[language][0]
    available = tts_langs()
    note = None
    if code not in available:
        if language.startswith("Bhojpuri") and "hi" in available:
            code = "hi"
            note = "Bhojpuri is not listed by this speech engine, so the audio uses a Hindi voice. The translation text remains Bhojpuri."
        else:
            raise RuntimeError("A speech voice is not available for this language. You can still copy or download the translation.")
    buffer = BytesIO()
    gTTS(text=text, lang=code, slow=slow).write_to_fp(buffer)
    return buffer.getvalue(), note


with st.sidebar:
    st.subheader("About")
    st.write("Text translation uses OpenRouter. Speech audio uses Google Text-to-Speech.")
    st.caption("Your OpenRouter key is read from Streamlit Secrets or the server environment.")
    st.caption("Free model endpoints can be rate-limited or temporarily unavailable.")

c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="section-label">Target language</div>', unsafe_allow_html=True)
    language = st.selectbox("Target language", list(LANGUAGES), label_visibility="collapsed")
with c2:
    st.markdown('<div class="section-label">Speech speed</div>', unsafe_allow_html=True)
    speed = st.selectbox("Speech speed", ["Normal", "Slow"], label_visibility="collapsed")

st.markdown('<div class="section-label">Your text</div>', unsafe_allow_html=True)
source = st.text_area(
    "Text to translate",
    value="Hello, world! How are you doing today?",
    height=170,
    max_chars=MAX_CHARS,
    placeholder="Type or paste your text...",
    label_visibility="collapsed",
)
st.caption(f"{len(source):,} / {MAX_CHARS:,} characters")

if st.button("✨ Translate text", type="primary", use_container_width=True):
    if not source.strip():
        st.warning("Please enter text to translate.")
    else:
        with st.spinner(f"Translating into {language}..."):
            try:
                st.session_state["translated"] = translate(source.strip(), language)
                st.session_state["target_language"] = language
                st.session_state["speech"] = None
                st.session_state["speech_note"] = None
                st.session_state["translation_error"] = None
            except RuntimeError as exc:
                st.session_state["translated"] = None
                st.session_state["translation_error"] = str(exc)
        if st.session_state.get("translation_error"):
            st.error(st.session_state["translation_error"])

translated = st.session_state.get("translated")
if translated:
    st.divider()
    st.markdown('<div class="section-label">Translation result</div>', unsafe_allow_html=True)
    st.text_area("Translated text", value=translated, height=190, disabled=True, label_visibility="collapsed")
    st.download_button(
        "⬇️ Download translation (.txt)",
        data=translated.encode("utf-8"),
        file_name="translation.txt",
        mime="text/plain; charset=utf-8",
        use_container_width=True,
    )
    if st.button("🔊 Generate speech", use_container_width=True):
        with st.spinner("Generating speech audio..."):
            try:
                audio, note = make_speech(translated, st.session_state["target_language"], speed == "Slow")
                st.session_state["speech"] = audio
                st.session_state["speech_note"] = note
            except Exception as exc:
                st.session_state["speech"] = None
                st.error(f"Could not generate speech: {exc}")
    if st.session_state.get("speech_note"):
        st.info(st.session_state["speech_note"])
    if st.session_state.get("speech"):
        st.audio(st.session_state["speech"], format="audio/mp3")

st.divider()
st.caption("Powered by OpenRouter · Speech by gTTS · Keep your API key private")
