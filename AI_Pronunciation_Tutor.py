import io
import google.generativeai as genai
import streamlit as st
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="AI Pronunciation & Speaking Tutor", layout="wide"
)
# Ô nhập API Key tại Sidebar
with st.sidebar:
  st.header("⚙️ Cấu hình API")
  default_key = st.secrets.get("GEMINI_API_KEY", "")
  user_api_key = st.text_input(
      "Nhập Google Gemini API Key:",
      value=default_key,
      type="password",
      help="Lấy API key tại https://aistudio.google.com/",
  )

  if not user_api_key:
    st.warning("⚠️ Vui lòng nhập Gemini API Key!")
    st.stop()
  else:
    genai.configure(api_key=user_api_key)
    st.success("✅ Đã kết nối API Key")
st.title("🎙️ AI Pronunciation & Speaking Tutor")
st.subheader("Luyện phát âm, Trợ lý AI Companion & Quản lý Lịch sử")

# Khởi tạo Session State
if "history" not in st.session_state:
  st.session_state.history = []
if "target_sentence" not in st.session_state:
  st.session_state.target_sentence = ""
if "last_processed_audio" not in st.session_state:
  st.session_state.last_processed_audio = None
if "current_analysis" not in st.session_state:
  st.session_state.current_analysis = None
if "recorder_key" not in st.session_state:
  st.session_state.recorder_key = 0


# Hàm xóa dữ liệu phân tích và làm sạch bộ nhớ thu âm khi đổi/xóa văn bản
def reset_audio_state():
  st.session_state.current_analysis = None
  st.session_state.last_processed_audio = None
  st.session_state.recorder_key += 1  # Đổi key để xả sạch bộ nhớ mic_recorder


def clear_text_callback():
  st.session_state.target_sentence = ""
  reset_audio_state()


def on_text_change():
  reset_audio_state()


# --- SIDEBAR: CẤU HÌNH API KEY ---
st.sidebar.header("🔑 Cấu hình API Key")
api_key = st.sidebar.text_input(
    "Nhập Gemini API Key của bạn:",
    value="",
    type="password",
    help="Lấy API key tại: https://aistudio.google.com/app/apikey",
)

if not api_key:
  st.warning("Vui lòng nhập Gemini API Key ở thanh bên (Sidebar) để tiếp tục.")
  st.stop()

genai.configure(api_key=api_key)

# --- GIAO DIỆN CHÍNH ---
col1, col2 = st.columns([1, 1])

with col1:
  st.markdown("### 1. Mẫu câu luyện tập & AI Companion")

  target_sentence = st.text_area(
      "Nhập hoặc dán câu tiếng Anh cần luyện nói:",
      key="target_sentence",
      height=100,
      on_change=on_text_change,
  )

  col_btn1, col_btn2 = st.columns([1, 1])
  with col_btn1:
    st.button("❌ Xóa văn bản", on_click=clear_text_callback)

  with col_btn2:
    if st.button("🔊 Phát âm mẫu câu này"):
      if target_sentence.strip():
        try:
          tts = gTTS(text=target_sentence.strip(), lang="en")
          fp = io.BytesIO()
          tts.write_to_fp(fp)
          fp.seek(0)
          st.audio(fp, format="audio/mp3")
        except Exception as e:
          st.error(f"Lỗi phát âm: {e}")
      else:
        st.warning("Vui lòng nhập câu cần nghe phát âm.")

  st.markdown("---")
  st.markdown("### 2. Thu âm giọng nói")
  st.write("Bấm **Bắt đầu thu âm**, bấm lại lần nữa để **Dừng & Phân tích**:")

  # Dynamic key giúp xả hoàn toàn bộ nhớ âm thanh cũ khi nhập câu mới
  audio = mic_recorder(
      start_prompt="🔴 Bắt đầu thu âm",
      stop_prompt="⏹️ Dừng & Phân tích",
      key=f"recorder_{st.session_state.recorder_key}",
  )

with col2:
  st.markdown("### 3. Kết quả phân tích & Sửa lỗi")

  # Kiểm tra và xử lý khi có file thu âm MỚI
  if (
      audio is not None
      and "bytes" in audio
      and audio["bytes"] != st.session_state.last_processed_audio
  ):
    if target_sentence.strip():
      st.audio(audio["bytes"], format="audio/wav")

      with st.spinner("Gemini đang lắng nghe và phân tích giọng nói..."):
        try:
          audio_data = {"mime_type": "audio/wav", "data": audio["bytes"]}

          prompt = f"""
                    Bạn là một chuyên gia huấn luyện phát âm tiếng Anh.
                    
                    Nhiệm vụ của bạn:
                    1. Nghe file âm thanh đi kèm và chép lại chính xác từng từ mà người nói đã phát âm (Spoken text).
                    2. So sánh giọng nói thực tế với câu chuẩn: "{target_sentence}"
                    
                    Hãy đưa ra nhận xét chi tiết, đi thẳng vào trọng tâm:
                    - **Văn bản nhận diện (Transcribed Text)**: [Viết lại câu nghe được]
                    - **Đánh giá chung**: Độ chính xác (%)
                    - **Chi tiết lỗi**: Từ phát âm chưa chuẩn, nuốt âm, ngọng, hoặc thiếu âm đuôi (ending sounds).
                    - **Hướng dẫn sửa**: Chi tiết vị trí đặt lưỡi, bật hơi hoặc mở khẩu hình miệng.
                    - **Phiên âm IPA chuẩn**: Cung cấp IPA cho các từ phát âm chưa chuẩn.
                    """

          # Sử dụng mô hình thế hệ mới
          model = genai.GenerativeModel("gemini-3.5-flash")
          response = model.generate_content([prompt, audio_data])

          # Cập nhật kết quả phân tích vào bộ nhớ
          st.session_state.current_analysis = response.text
          st.session_state.last_processed_audio = audio["bytes"]

          # Lưu vào lịch sử
          st.session_state.history.append(
              {"target": target_sentence, "result": response.text}
          )

        except Exception as e:
          st.error(f"Có lỗi khi xử lý âm thanh: {e}")
    else:
      st.warning("Vui lòng nhập mẫu câu ở Bước 1 trước khi phân tích thu âm.")

  # Hiển thị kết quả phân tích hiện tại
  if st.session_state.current_analysis and target_sentence.strip():
    st.markdown(st.session_state.current_analysis)

# --- QUẢN LÝ LỊCH SỬ LUYỆN TẬP ---
st.markdown("---")
st.markdown("## 📜 Lịch sử luyện tập")

if st.session_state.history:
  if st.button("🗑️ Xóa tất cả lịch sử"):
    st.session_state.history = []
    st.session_state.current_analysis = None
    st.rerun()

  for idx, item in enumerate(reversed(st.session_state.history)):
    real_idx = len(st.session_state.history) - 1 - idx
    col_hist1, col_hist2 = st.columns([5, 1])

    with col_hist1:
      with st.expander(f"Mục {real_idx + 1}: {item['target'][:50]}..."):
        st.markdown(f"**Câu mẫu:** {item['target']}")
        st.markdown(item["result"])

    with col_hist2:
      if st.button(f"❌ Xóa", key=f"del_{real_idx}"):
        st.session_state.history.pop(real_idx)
        st.rerun()
else:
  st.info("Chưa có lịch sử luyện tập trong phiên làm việc này.")