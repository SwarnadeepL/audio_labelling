import streamlit as st
import pandas as pd
import requests
import os
from io import BytesIO

st.set_page_config(page_title="Audio Labeling Tool", layout="centered")
st.title("🎧 Audio Labeling App")

# ── Upload Excel ───────────────────────────────────────────
uploaded_file = st.file_uploader("Upload Excel", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, engine="openpyxl")
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
        st.stop()

    # Required columns check
    required_cols = {"Audio_Name", "Audio_Link"}
    if not required_cols.issubset(df.columns):
        st.error(f"Excel must contain columns: {required_cols}")
        st.stop()

    # Create column if missing
    if "Transcription" not in df.columns:
        df["Transcription"] = ""

    df["Transcription"] = df["Transcription"].fillna("")

    # ── Reset state if new file uploaded ──────────────────
    file_id = uploaded_file.name + str(uploaded_file.size)

    if "file_id" not in st.session_state or st.session_state.file_id != file_id:
        st.session_state.file_id = file_id
        st.session_state.index = 0
        st.session_state.data = df.copy()
        st.session_state.input_file = uploaded_file.name

    data = st.session_state.data
    idx = st.session_state.index
    input_file = st.session_state.input_file

    # ── Download filename ─────────────────────────────────
    base_name = os.path.splitext(input_file)[0]
    download_name = f"labeled_{base_name}.xlsx"

    # ── Progress Calculations ─────────────────────────────
    labeled_count = (data["Transcription"].str.strip() != "").sum()
    total_count = len(data)
    progress = labeled_count / total_count if total_count > 0 else 0

    st.markdown("### 📊 Overall Progress")
    st.progress(progress)
    st.caption(f"Labeled: {labeled_count} / {total_count}")

    # ── Completed ─────────────────────────────────────────
    if idx >= total_count:
        st.success("✅ All audio files labeled!")

        # Save dataframe to Excel in memory
        output = BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            data.to_excel(writer, index=False)

        output.seek(0)
    
        st.download_button(
            label="📥 Download Labeled Excel",
            data=output,
            file_name=download_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.stop()

    # ── Current Row ───────────────────────────────────────
    row = data.iloc[idx]

    st.markdown(f"### 🎵 Audio {idx + 1} / {total_count}")
    st.write(f"**File:** `{row['Audio_Name']}`")

    # ── Audio Player ──────────────────────────────────────
    try:
        audio_bytes = requests.get(row["Audio_Link"], timeout=10).content
        st.audio(audio_bytes)
    except Exception as e:
        st.warning(f"Could not load audio: {e}")
        st.markdown(f"[🔗 Open audio link]({row['Audio_Link']})")

    # ── Transcription Input ───────────────────────────────
    current_transcription = str(data.at[idx, "Transcription"])

    transcription = st.text_area(
        "✍️ Please review or fill transcription",
        value=current_transcription,
        height=150,
        placeholder="Type transcription here...",
        key=f"Transcription_{idx}",
    )

    # ── Navigation Progress ───────────────────────────────
    st.markdown("### 📍 Position")
    nav_progress = (idx + 1) / total_count if total_count > 0 else 0
    st.progress(nav_progress)
    st.caption(f"{idx + 1} / {total_count}")

    # ── Navigation Buttons ────────────────────────────────
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("⬅️ Back", disabled=idx == 0):
            st.session_state.data.at[idx, "Transcription"] = transcription
            st.session_state.index = max(0, idx - 1)
            st.rerun()

    with col2:
        if st.button("⏭️ Skip"):
            st.session_state.data.at[idx, "Transcription"] = transcription
            st.session_state.index += 1
            st.rerun()

    with col3:
        if st.button("✅ Submit & Next", type="primary"):
            st.session_state.data.at[idx, "Transcription"] = transcription
            st.session_state.index += 1
            st.rerun()