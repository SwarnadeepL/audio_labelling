import streamlit as st
import pandas as pd
import requests
import os

st.set_page_config(page_title="Audio Labeling Tool", layout="centered")
st.title("🎧 Audio Labeling App")

# ── Upload CSV ─────────────────────────────────────────────
uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Required columns check
    required_cols = {"audio_name", "audio_link"}
    if not required_cols.issubset(df.columns):
        st.error(f"CSV must contain columns: {required_cols}")
        st.stop()

    if "transcription" not in df.columns:
        df["transcription"] = ""
    df["transcription"] = df["transcription"].fillna("")

    # ── Reset state if new file uploaded ──────────────────
    file_id = uploaded_file.name + str(uploaded_file.size)
    if "file_id" not in st.session_state or st.session_state.file_id != file_id:
        st.session_state.file_id   = file_id
        st.session_state.index     = 0
        st.session_state.data      = df.copy()
        st.session_state.input_csv = uploaded_file.name

    data      = st.session_state.data
    idx       = st.session_state.index
    input_csv = st.session_state.input_csv

    # ── Download filename: labeled_<original_name> ────────
    base_name     = os.path.splitext(input_csv)[0]
    download_name = f"labeled_{base_name}.csv"

    # ── Sidebar ────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 📊 Progress")
        labeled = data[data["transcription"].str.strip() != ""]
        st.metric("Total",     len(data))
        st.metric("Labeled",   len(labeled))
        st.metric("Remaining", len(data) - len(labeled))

        st.divider()

        st.markdown("### 🔢 Jump to Row")
        jump = st.number_input(
            "Row number",
            min_value=1,
            max_value=len(data),
            value=min(idx + 1, len(data)),
        )
        if st.button("Go"):
            st.session_state.index = jump - 1
            st.rerun()

    # ── Completed ──────────────────────────────────────────
    if idx >= len(data):
        st.success("✅ All audio files labeled!")
        csv_bytes = data.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Labeled CSV",
            data=csv_bytes,
            file_name=download_name,
            mime="text/csv",
        )
        st.stop()

    # ── Current Row ────────────────────────────────────────
    row = data.iloc[idx]

    st.markdown(f"### 🎵 Audio {idx + 1} / {len(data)}")
    st.write(f"**File:** `{row['audio_name']}`")

    # ── Audio Player ───────────────────────────────────────
    try:
        audio_bytes = requests.get(row["audio_link"], timeout=10).content
        st.audio(audio_bytes)
    except Exception as e:
        st.warning(f"Could not load audio: {e}")
        st.markdown(f"[🔗 Open audio link]({row['audio_link']})")

    # ── Transcription Input ────────────────────────────────
    current_transcription = str(data.at[idx, "transcription"])

    transcription = st.text_area(
        "✍️ Pleas check and complete transcription",
        value=current_transcription,
        height=150,
        placeholder="Type transcription here...",
        key=f"transcription_{idx}",
    )

    # ── Progress Bar ───────────────────────────────────────
    st.progress((idx + 1) / len(data))

    # ── Navigation Buttons ─────────────────────────────────
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("⬅️ Back", disabled=idx == 0):
            st.session_state.data.at[idx, "transcription"] = transcription
            st.session_state.index = max(0, idx - 1)
            st.rerun()

    with col2:
        if st.button("⏭️ Skip"):
            st.session_state.data.at[idx, "transcription"] = transcription
            st.session_state.index += 1
            st.rerun()

    with col3:
        if st.button("✅ Submit & Next", type="primary"):
            st.session_state.data.at[idx, "transcription"] = transcription
            st.session_state.index += 1
            st.rerun()

# streamlit run app.py
