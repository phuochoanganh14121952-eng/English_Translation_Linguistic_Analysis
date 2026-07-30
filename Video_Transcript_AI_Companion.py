import os
import json
import tempfile
import streamlit as st
import whisper
from pydub import AudioSegment
import google.generativeai as genai
import nltk

# Tải dữ liệu ngắt câu của NLTK
nltk.download('punkt')
from nltk.tokenize import sent_tokenize

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

        with st.spinner("1/3. Whisper đang nhận diện âm thanh..."):
            raw_result = model.transcribe(input_path, language="en", temperature=0.0)
            full_text = raw_result.get("text", "").strip()

            # Tách chính xác thành từng câu đơn
            raw_sentences = sent_tokenize(full_text)

        # Cắt mốc thời gian dựa trên tỉ lệ độ dài ký tự từng câu
        audio_segment = AudioSegment.from_file(input_path)
        total_duration_ms = len(audio_segment)
        total_chars = len(full_text) if len(full_text) > 0 else 1

        sentences = []
        current_time_ms = 0

        for s in raw_sentences:
            s_len = len(s)
            dur_ms = int((s_len / total_chars) * total_duration_ms)
            sentences.append({
                "text": s,
                "start_ms": current_time_ms,
                "end_ms": min(current_time_ms + dur_ms, total_duration_ms)
            })
            current_time_ms += dur_ms

        english_texts = [s["text"] for s in sentences]

        with st.spinner("2/3. Gemini đang gán người nói và dịch thuật..."):
            prompt = f"""
Dưới đây là danh sách các câu thoại theo đúng thứ tự:
{json.dumps(english_texts, ensure_ascii=False, indent=2)}

Nhiệm vụ:
1. Dịch từng câu sang tiếng Việt.
2. Gán Speaker A hoặc Speaker B cho từng câu dựa vào ngữ cảnh đối thoại (luân phiên đổi người nói khi hỏi/đáp).
3. Tóm tắt nội dung bài học.

Trả về duy nhất JSON với số lượng phần tử trong `items` ĐÚNG BẰNG {len(english_texts)}:
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

        for idx, sent in enumerate(sentences):
            chunk = audio_segment[sent["start_ms"]:sent["end_ms"]]
            chunk_path = os.path.join(temp_dir, f"chunk_{idx}.mp3")
            chunk.export(chunk_path, format="mp3")

            speaker_label = items[idx]["speaker"] if idx < len(items) else f"Speaker {idx+1}"
            text_en = sent["text"]
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