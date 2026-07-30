import os
import json
import tempfile
import streamlit as st
import whisper
from pydub import AudioSegment
import google.generativeai as genai

st.set_page_config(page_title="Video Transcript & AI Companion", layout="wide")
st.title("🎙️ Trích xuất thoại & Bảng âm thanh thực hành")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Chưa cấu hình GEMINI_API_KEY trong Streamlit Secrets!")

@st.cache_resource
def load_whisper_model():
    return whisper.load_model("base")

model = load_whisper_model()

uploaded_file = st.file_uploader("Tải lên file âm thanh hoặc video", type=["mp3", "wav", "m4a", "mp4"])

if uploaded_file:
    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, uploaded_file.name)
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        with st.spinner("1/3. Whisper đang ngắt từng phân đoạn thoại..."):
            # Cấu hình buộc Whisper chia nhỏ đoạn âm thanh khi có khoảng dừng ngắn
            raw_result = model.transcribe(
                input_path,
                language="en",
                temperature=0.0,
                condition_on_previous_text=False,
                no_speech_threshold=0.3
            )
            raw_segments = raw_result.get("segments", [])

        sentences = [s['text'].strip() for s in raw_segments]

        with st.spinner("2/3. Gemini đang gán người nói và dịch thuật..."):
            prompt = f"""
Dưới đây là danh sách các câu thoại tách theo mốc thời gian:
{json.dumps(sentences, ensure_ascii=False, indent=2)}

Nhiệm vụ:
1. Dịch từng câu sang tiếng Việt.
2. Gán Speaker A hoặc Speaker B cho từng câu (luân phiên người nói theo ngữ cảnh).
3. Tóm tắt nội dung bài học bằng tiếng Anh và tiếng Việt.

Trả về duy nhất JSON với số lượng phần tử trong `items` ĐÚNG BẰNG {len(sentences)}:
{{
  "summary_en": "Tóm tắt tiếng Anh",
  "summary_vi": "Tóm tắt tiếng Việt",
  "items": [
    {{
      "speaker": "Speaker A",
      "english": "Nội dung câu 1",
      "vietnamese": "Dịch tiếng Việt câu 1"
    }}
  ]
}}
"""
            gemini_model = genai.GenerativeModel('gemini-2.5-pro')
            response = gemini_model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            try:
                res_json = json.loads(response.text)
                items = res_json.get("items", [])
            except Exception:
                items = []

        st.subheader("📝 Tóm tắt bài học")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**English Summary:**\n{res_json.get('summary_en', '')}")
        with col2:
            st.markdown(f"**Tóm tắt tiếng Việt:**\n{res_json.get('summary_vi', '')}")

        st.divider()
        st.subheader("🗣️ Chi tiết lượt thoại & Phát âm")

        audio_segment = AudioSegment.from_file(input_path)

        for idx, seg in enumerate(raw_segments):
            start_ms = int(seg["start"] * 1000)
            end_ms = int(seg["end"] * 1000)
            
            chunk = audio_segment[start_ms:end_ms]
            chunk_path = os.path.join(temp_dir, f"chunk_{idx}.mp3")
            chunk.export(chunk_path, format="mp3")

            speaker_label = items[idx]["speaker"] if idx < len(items) else f"Speaker {idx+1}"
            text_en = seg["text"].strip()
            text_vi = items[idx]["vietnamese"] if idx < len(items) else ""

            c1, c2, c3 = st.columns([1.5, 4, 3])
            with c1:
                st.markdown(f"**{speaker_label}**")
            with c2:
                st.write(text_en)
                st.caption(text_vi)
            with c3:
                with open(chunk_path, "rb") as audio_file:
                    st.audio(audio_file.read(), format="audio/mp3")