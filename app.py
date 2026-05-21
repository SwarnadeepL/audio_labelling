import streamlit as st
import pandas as pd
import requests
import os
from io import BytesIO

st.set_page_config(page_title="Audio Labeling Tool", layout="wide")
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

    if "Ground_Truth" not in df.columns:
        df["Ground_Truth"] = ""
    if "Ground_Truth_Changed" not in df.columns:
        df["Ground_Truth_Changed"] = False
    if "Is_Reviewed" not in df.columns:
        df["Is_Reviewed"] = False

    df["Ground_Truth"] = df["Ground_Truth"].fillna("")
    df["Ground_Truth_Changed"] = df["Ground_Truth_Changed"].fillna(False)
    df["Is_Reviewed"] = df["Is_Reviewed"].fillna(False)

    # ── Reset state if new file uploaded ──────────────────
    file_id = uploaded_file.name + str(uploaded_file.size)

    if "file_id" not in st.session_state or st.session_state.file_id != file_id:
        st.session_state.file_id = file_id
        st.session_state.index = 0
        st.session_state.data = df.copy()
        st.session_state.input_file = uploaded_file.name
        st.session_state.original_gt = df["Ground_Truth"].tolist()

    data = st.session_state.data
    original_gt = st.session_state.original_gt
    total_count = len(data)
    input_file = st.session_state.input_file

    base_name = os.path.splitext(input_file)[0]
    download_name = f"labeled_{base_name}.xlsx"

    # ── Unverified list (only these are navigable) ────────
    unverified = data.index[~data["Is_Reviewed"].astype(bool)].tolist()
    verified_count = total_count - len(unverified)

    # ── Clamp session index to unverified list ────────────
    if "unverified_pos" not in st.session_state:
        st.session_state.unverified_pos = 0

    # Keep pos in bounds
    if unverified:
        st.session_state.unverified_pos = min(
            st.session_state.unverified_pos, len(unverified) - 1
        )
        idx = unverified[st.session_state.unverified_pos]
    else:
        idx = None  # all done

    # ── Save helper ───────────────────────────────────────
    def save_and_go(current_idx, gt, skipped=False, navigating=False):
        st.session_state.data.at[current_idx, "Ground_Truth"] = gt
        original = str(original_gt[current_idx]).strip()
        submitted = str(gt).strip()
        st.session_state.data.at[current_idx, "Ground_Truth_Changed"] = (submitted != original)

        if navigating:
            pass
        elif skipped:
            st.session_state.data.at[current_idx, "Is_Reviewed"] = False
        else:
            st.session_state.data.at[current_idx, "Is_Reviewed"] = True

    # ── Helper: build Excel bytes ─────────────────────────
    def build_excel(df_to_save):
        output = BytesIO()
        df_export = df_to_save.drop(columns=["Is_Reviewed"], errors="ignore").copy()
        df_export["Ground_Truth_Changed"] = df_export["Ground_Truth_Changed"].astype(int)
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_export.to_excel(writer, index=False)
        output.seek(0)
        return output

    # ── Sidebar ───────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 📋 Verification Status")
        st.caption(f"Verified: {verified_count} / {total_count}")
        st.markdown("---")

        for i, row in data.iterrows():
            has_gt = str(row["Ground_Truth"]).strip() != ""
            is_verified = bool(row["Is_Reviewed"])

            if is_verified:
                icon = "✅"
            elif has_gt:
                icon = "✍️"
            else:
                icon = "⬜"

            label = f"{icon} {i + 1}. {str(row['Audio_Name'])[:26]}"
            is_current = (idx is not None and i == idx)
            btn_type = "primary" if is_current else "secondary"

            # Only unverified rows are clickable
            if not is_verified:
                if st.button(label, key=f"jump_{i}", use_container_width=True, type=btn_type):
                    pos = unverified.index(i)
                    st.session_state.unverified_pos = pos
                    st.rerun()
            else:
                st.button(label, key=f"jump_{i}", use_container_width=True, disabled=True)

    # ── Progress Bar ──────────────────────────────────────
    st.markdown("### 📊 Verification Progress")
    progress = verified_count / total_count if total_count > 0 else 0
    st.progress(progress)
    st.caption(f"Verified: {verified_count} / {total_count}")

    # ── All done ──────────────────────────────────────────
    if idx is None:
        st.success("✅ All audio files verified!")
        st.download_button(
            label="📥 Download Labeled Excel",
            data=build_excel(data),
            file_name=download_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.stop()

    # ── Current Row ───────────────────────────────────────
    row = data.iloc[idx]
    pos = st.session_state.unverified_pos
    unverified_total = len(unverified)

    st.markdown(f"### 🎵 Audio {idx + 1} / {total_count}")
    st.write(f"**File:** `{row['Audio_Name']}`")

    # ── Audio Player ──────────────────────────────────────
    try:
        response = requests.get(row["Audio_Link"], timeout=10)
        response.raise_for_status()
        st.audio(response.content)
    except Exception as e:
        st.warning(f"Could not load audio: {e}")
        st.markdown(f"[🔗 Open audio link]({row['Audio_Link']})")

    # ── Ground Truth Input ────────────────────────────────
    current_gt = str(data.at[idx, "Ground_Truth"])
    ground_truth = st.text_area(
        "✍️ Please review or fill text",
        value=current_gt,
        height=150,
        placeholder="Type Ground_Truth here...",
        key=f"Ground_Truth_{idx}",
    )

    # ── Navigation Buttons ────────────────────────────────
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("⬅️ Back", disabled=pos == 0):
            save_and_go(idx, ground_truth, navigating=True)
            st.session_state.unverified_pos = max(0, pos - 1)
            st.rerun()

    with col2:
        if st.button("⏭️ Skip"):
            save_and_go(idx, ground_truth, skipped=True)
            # Move to next unverified (pos stays, list shrinks only on submit)
            next_pos = pos + 1
            if next_pos >= len(unverified):
                next_pos = 0
            st.session_state.unverified_pos = next_pos
            st.rerun()

    with col3:
        if st.button("✅ Submit & Next", type="primary"):
            save_and_go(idx, ground_truth)
            # After submit this row leaves unverified, pos stays (next item slides in)
            # But clamp in case it was the last one
            st.session_state.unverified_pos = pos  # will be clamped at top
            st.rerun()


# streamlit run app.py