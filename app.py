from __future__ import annotations

import asyncio
import os

import requests
import streamlit as st

try:
    import edge_tts
except ImportError:
    edge_tts = None

APP_TITLE = "Accent-Aware Multilingual Translator"
DEFAULT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_CHARS = 8000

LANGUAGES = {
    "Spanish": ("es", "Latin"),
    "French": ("fr", "Latin"),
    "German": ("de", "Latin"),
    "Italian": ("it", "Latin"),
    "Portuguese": ("pt", "Latin"),
    "Japanese": ("ja", "Japanese"),
    "Korean": ("ko", "Korean"),
    "Chinese (Simplified)": ("zh-CN", "Simplified Chinese"),
    "English": ("en", "Latin"),
    "Hindi (हिन्दी)": ("hi", "Devanagari"),
    "Arabic (العربية)": ("ar", "Arabic"),
    "Kannada (ಕನ್ನಡ)": ("kn-IN", "Kannada"),
    "Telugu (తెలుగు)": ("te-IN", "Telugu"),
    "Tamil (தமிழ்)": ("ta-IN", "Tamil"),
    "Malayalam (മലയാളം)": ("ml-IN", "Malayalam"),
    "Marathi (मराठी)": ("mr-IN", "Devanagari"),
    "Urdu (اردو)": ("ur-PK", "Urdu"),
    "Bhojpuri (भोजपुरी)": ("bho-IN", "Devanagari"),
}

VOICES = {
    "Spanish": ("es-ES-ElviraNeural", "es-ES-AlvaroNeural"),
    "French": ("fr-FR-DeniseNeural", "fr-FR-HenriNeural"),
    "German": ("de-DE-KatjaNeural", "de-DE-ConradNeural"),
    "Italian": ("it-IT-ElsaNeural", "it-IT-DiegoNeural"),
    "Portuguese": ("pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"),
    "Japanese": ("ja-JP-NanamiNeural", "ja-JP-KeitaNeural"),
    "Korean": ("ko-KR-SunHiNeural", "ko-KR-InJoonNeural"),
    "Chinese (Simplified)": ("zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"),
    "English": ("en-IN-NeerjaNeural", "en-IN-PrabhatNeural"),
    "Hindi (हिन्दी)": ("hi-IN-SwaraNeural", "hi-IN-MadhurNeural"),
    "Arabic (العربية)": ("ar-SA-ZariyahNeural", "ar-SA-HamedNeural"),
    "Kannada (ಕನ್ನಡ)": ("kn-IN-SapnaNeural", "kn-IN-GaganNeural"),
    "Telugu (తెలుగు)": ("te-IN-ShrutiNeural", "te-IN-MohanNeural"),
    "Tamil (தமிழ்)": ("ta-IN-PallaviNeural", "ta-IN-ValluvarNeural"),
    "Malayalam (മലയാളം)": ("ml-IN-SobhanaNeural", "ml-IN-MidhunNeural"),
    "Marathi (मराठी)": ("mr-IN-AarohiNeural", "mr-IN-ManoharNeural"),
    "Urdu (اردو)": ("ur-PK-UzmaNeural", "ur-PK-AsadNeural"),
    "Bhojpuri (भोजपुरी)": ("hi-IN-SwaraNeural", "hi-IN-MadhurNeural"),
}

STYLES = {
    "Natural": "Use natural everyday wording while preserving the meaning.",
    "Formal": "Use polite, professional wording.",
    "Conversational": "Use warm, conversational wording that sounds natural when spoken.",
    "Literal": "Stay close to the source wording while remaining grammatically correct.",
}


def secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value or os.getenv(name, default)).strip()


def translate_text(text: str, source: str, target: str, style: str, accent: str) -> str:
    api_key = secret("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing. Add it in Streamlit Settings > Secrets.")
    model = secret("OPENROUTER_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL
    source_instruction = "Detect the source language automatically." if source == "Auto-detect" else f"The source language is {source}."
    accent_instruction = f"Use {accent} English spelling and vocabulary." if target == "English" else ""
    script = LANGUAGES[target][1]
    system_prompt = (
        f"You are a professional multilingual translator. Translate into {target}. "
        f"{source_instruction} {STYLES[style]} {accent_instruction} "
        f"Use the correct native writing system: {script}. Preserve names, numbers, meaning, intent and formatting. "
        "Do not add explanations, quotation marks, pronunciation guides or transliteration. Return only the translation."
    )
    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://streamlit.io/",
                "X-Title": APP_TITLE,
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.2,
                "max_tokens": 2048,
            },
            timeout=(15, 90),
        )
    except requests.Timeout as exc:
        raise RuntimeError("The translation provider timed out. Please try again.") from exc
    except requests.RequestException as exc:
        raise RuntimeError("Could not connect to OpenRouter. Check your connection.") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(f"OpenRouter returned an unexpected response (HTTP {response.status_code}).") from exc
    if not response.ok:
        error = data.get("error", {}) if isinstance(data, dict) else {}
        message = error.get("message") if isinstance(error, dict) else None
        if response.status_code == 401:
            raise RuntimeError("OpenRouter rejected the API key (401). Check the key in Streamlit Secrets.")
        if response.status_code == 429:
            raise RuntimeError("OpenRouter rate limit reached (429). Please wait and try again.")
        raise RuntimeError(message or f"Translation failed (HTTP {response.status_code}).")
    try:
        result = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("No translation was returned. Try another model.") from exc
    if not isinstance(result, str) or not result.strip():
        raise RuntimeError("The translation provider returned an empty result.")
    return result.strip()


async def _speech(text: str, voice: str, rate: int) -> bytes:
    communicator = edge_tts.Communicate(text=text, voice=voice, rate=f"{rate:+d}%")
    chunks = []
    async for chunk in communicator.stream():
        if chunk.get("type") == "audio":
            chunks.append(chunk["data"])
    audio = b"".join(chunks)
    if not audio:
        raise RuntimeError("The speech provider returned no audio.")
    return audio


def make_speech(text: str, voice: str, rate: int) -> bytes:
    if edge_tts is None:
        raise RuntimeError("Speech support is unavailable. Reinstall requirements.txt.")
    try:
        return asyncio.run(_speech(text, voice, rate))
    except RuntimeError as exc:
        if "asyncio.run() cannot be called" not in str(exc):
            raise
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_speech(text, voice, rate))
        finally:
            loop.close()


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🌐", layout="centered")
    st.markdown(
        """
        <style>
        .stApp {background: radial-gradient(ellipse at 15% 0%, #eaf2ff 0%, #f6f8fc 50%, #f5f7fb 100%);}
        .block-container {max-width: 1000px; padding-top: 2rem;}
        .hero {padding: 1.5rem; border-radius: 20px; color: white; background: linear-gradient(120deg,#142b52,#2357a6,#3f80cc); margin-bottom: 1.2rem;}
        .hero h1 {color:white; margin:0 0 .3rem 0;}
        .hero p {color:#dceaff; margin:0;}
        .stButton>button {border-radius:12px; min-height:2.8rem; font-weight:700;}
        footer {visibility:hidden;}
        </style>
        <div class="hero"><h1>🌐 Accent-Aware Translator</h1>
        <p>Translate naturally across languages, choose regional English, and listen to the result.</p></div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.subheader("About")
        st.write("Translation: OpenRouter. Spoken output: neural text-to-speech.")
        st.caption("Your API key is read securely from Streamlit Secrets or environment variables.")

    source_text = st.text_area(
        "Text to translate",
        value=st.session_state.get("source_text", "Hello, world! How are you doing today?"),
        max_chars=MAX_CHARS,
        height=170,
        placeholder="Type or paste your text here...",
    )
    st.caption(f"{len(source_text):,} / {MAX_CHARS:,} characters")

    c1, c2 = st.columns(2)
    with c1:
        source_language = st.selectbox("Source language", ["Auto-detect", *LANGUAGES.keys()])
    with c2:
        target_language = st.selectbox("Translate into", list(LANGUAGES.keys()), index=0)

    c3, c4 = st.columns(2)
    with c3:
        style = st.selectbox("Translation style", list(STYLES.keys()))
    with c4:
        accent = st.selectbox("English accent", ["Indian", "British", "American", "Australian"]) if target_language == "English" else "Indian"

    if st.button("✨ Translate text", type="primary", use_container_width=True):
        if not source_text.strip():
            st.warning("Please enter text before translating.")
        elif source_language == target_language:
            st.warning("Choose a different target language or select Auto-detect.")
        else:
            try:
                with st.spinner(f"Translating into {target_language}..."):
                    st.session_state.translation = translate_text(
                        source_text.strip(), source_language, target_language, style, accent
                    )
                st.session_state.source_text = source_text
                st.session_state.target_language = target_language
                st.session_state.audio = None
                st.success("Translation completed.")
            except Exception as exc:
                st.error(str(exc))

    translated = st.session_state.get("translation", "")
    if translated:
        st.divider()
        st.subheader("Translation result")
        st.text_area("Translated text", value=translated, height=180, disabled=True)
        st.download_button(
            "⬇️ Download translation (.txt)",
            data=translated.encode("utf-8"),
            file_name="translation.txt",
            mime="text/plain; charset=utf-8",
        )

        st.markdown("#### Listen to translation")
        if st.session_state.get("target_language", "").startswith("Bhojpuri"):
            st.info("Bhojpuri uses a Hindi neural voice fallback for speech. The translation text remains Bhojpuri.")
        voice_names = ("Female voice", "Male voice")
        voice_choice = st.selectbox("Voice", voice_names)
        voice_id = VOICES.get(st.session_state.get("target_language", target_language), VOICES["English"])[0 if voice_choice == voice_names[0] else 1]
        rate = st.slider("Speaking speed", -25, 25, 0, step=5, format="%d%%")
        if st.button("🔊 Generate speech", use_container_width=True):
            try:
                with st.spinner("Generating spoken audio..."):
                    st.session_state.audio = make_speech(translated, voice_id, rate)
            except Exception as exc:
                st.session_state.audio = None
                st.error(f"Could not generate audio: {exc}")
        if st.session_state.get("audio"):
            st.audio(st.session_state.audio, format="audio/mp3")
            st.download_button(
                "⬇️ Download speech (.mp3)",
                data=st.session_state.audio,
                file_name="translation.mp3",
                mime="audio/mpeg",
            )

    st.divider()
    st.caption("Translation powered by OpenRouter. Speech generated by neural TTS. Provider availability may vary.")


if __name__ == "__main__":
    main()
