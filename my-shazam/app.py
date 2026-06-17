"""
My-Shazam — a tiny Streamlit app that transcribes sung speech and guesses the song.
"""

import tempfile
from pathlib import Path

import streamlit as st

from agent import identify_song, transcribe_audio


def to_audio_bytes(value) -> bytes:
    """Convert Streamlit audio inputs to raw bytes for tempfile handling."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value)
    if hasattr(value, "getvalue"):
        return bytes(value.getvalue())
    if hasattr(value, "read"):
        return value.read()
    return bytes(value)

st.set_page_config(page_title="My-Shazam", page_icon="🎵", layout="centered")

st.title("🎵 My-Shazam")
st.caption("Upload a short singing clip, let the deployed transcription model turn it into text, then use gpt-5.4-mini + web search to identify the song.")

with st.expander("How it works", expanded=False):
    st.markdown(
        """
        1. Upload an audio file (WAV, MP3, M4A, OGG).
        2. The app transcribes the clip with the deployed Azure OpenAI transcription model.
        3. A second pass with gpt-5.4-mini and web search proposes the most likely song and artist.
        """
    )

uploaded_file = st.file_uploader(
    "Upload a singing clip",
    type=["wav", "mp3", "m4a", "ogg", "webm"],
    help="Use a short clip with clear lyrics to improve the guess.",
)
recorded_audio = st.audio_input(
    "Or record a clip in your browser",
    help="This uses your browser microphone when available.",
)

source_audio = None
source_name = "your clip"

if uploaded_file is not None:
    source_audio = to_audio_bytes(uploaded_file)
    source_name = uploaded_file.name
elif recorded_audio is not None:
    source_audio = to_audio_bytes(recorded_audio)
    source_name = "recorded clip"

if source_audio is not None:
    st.audio(source_audio, format="audio/wav")
    if st.button("Identify the song", type="primary"):
        with st.spinner("Transcribing the audio and checking the web for the song..."):
            suffix = Path(source_name).suffix or ".wav"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(source_audio)
                tmp_path = Path(tmp.name)

            try:
                transcript = transcribe_audio(tmp_path)
                guess = identify_song(transcript)
            finally:
                if tmp_path.exists():
                    tmp_path.unlink(missing_ok=True)

        st.success("Done")

        st.subheader("Transcript")
        st.text_area("Transcription output", transcript, height=140)

        st.subheader("Likely song")
        if guess.get("title") or guess.get("artist"):
            st.markdown(f"**Title:** {guess.get('title') or 'Unknown'}")
            st.markdown(f"**Artist:** {guess.get('artist') or 'Unknown'}")
            st.markdown(f"**Confidence:** {guess.get('confidence', 'low').title()}")
            st.write(guess.get("why_it_matches", ""))

            if guess.get("evidence_links"):
                st.caption("Web search evidence")
                for link in guess["evidence_links"]:
                    st.markdown(f"- {link}")
        else:
            st.info("The transcript was too short or unclear to identify a song with confidence.")

        if guess.get("raw_response"):
            with st.expander("Raw model output"):
                st.code(guess["raw_response"])
else:
    st.info("Choose an audio file or record a short clip to begin.")
