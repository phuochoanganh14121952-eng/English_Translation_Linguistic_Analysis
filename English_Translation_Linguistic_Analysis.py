import streamlit as st
from google import genai
from google.genai import types
import re
from gtts import gTTS
import io
import json
import os

# Đường dẫn tệp lưu trữ lịch sử cục bộ trên ổ cứng
HISTORY_FILE = "history_db.json"

def load_persistent_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("history", []), data.get("extracted_en_clean", "")
        except Exception:
            return [], ""
    return [], ""

def save_persistent_history(history, extracted_en_clean):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "history": history,
                "extracted_en_clean": extracted_en_clean
            }, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"Lỗi lưu trữ dữ liệu: {e}")

# 1. Cấu hình giao diện và API ổn định bằng thư viện mới
st.set_page_config(page_title="English Translation & Linguistic Analysis", layout="wide")

# Khởi tạo Client mới của thư viện google-genai
client = genai.Client()
# Khóa thông số sáng tạo thấp nhất để đảm bảo tính nhất quán tuyệt đối
generation_config = types.GenerateContentConfig(
    temperature=0.1,
)
MODEL_NAME = "gemini-3.5-flash"

# Khôi phục dữ liệu lịch sử từ tệp cục bộ lên session_state
saved_history, saved_extracted = load_persistent_history()

if "history" not in st.session_state:
    st.session_state.history = saved_history
if "extracted_en_clean" not in st.session_state:
    st.session_state.extracted_en_clean = saved_extracted
if "companion_input_value" not in st.session_state:
    st.session_state.companion_input_value = ""

# Tên App và dòng mô tả tiếng Việt
st.title("English Translation & Linguistic Analysis")
st.caption("Trợ lý chuyên gia hỗ trợ dịch thuật tối ưu, sửa lỗi hệ thống và phân tích cấu trúc ngôn ngữ Anh ngữ chuyên sâu.")
st.markdown("---")

col_left, col_middle, col_right = st.columns([0.8, 2, 1.2])

# KHUNG TRÁI: History
with col_left:
    col_hist_title, col_hist_del = st.columns([3, 1])
    with col_hist_title:
        st.subheader("History")
    with col_hist_del:
        if st.button("🗑️", help="Xóa vĩnh viễn toàn bộ lịch sử", key="clear_all_history_btn", use_container_width=True):
            st.session_state.history = []
            st.session_state.extracted_en_clean = ""
            if os.path.exists(HISTORY_FILE):
                try:
                    os.remove(HISTORY_FILE)
                except Exception:
                    pass
            st.rerun()
            
    with st.expander("Xem lịch sử trước đó", expanded=True):
        if not st.session_state.history:
            st.write("Chưa có dữ liệu.")
        else:
            for i in range(len(st.session_state.history) - 1, -1, -1):
                item = st.session_state.history[i]
                st.markdown(f"**{item['type']}**")
                st.caption(f"_{item['text'][:40]}..._")
                
                col_btn_view, col_btn_del = st.columns([2, 1])
                with col_btn_view:
                    with st.popover("Xem lại", key=f"popover_view_{i}"):
                        st.write(item['result'])
                with col_btn_del:
                    if st.button("Xóa", key=f"del_history_item_{i}"):
                        st.session_state.history.pop(i)
                        save_persistent_history(st.session_state.history, st.session_state.extracted_en_clean)
                        st.rerun()
                st.markdown("---")

# KHUNG GIỮA: Xử lý chính
with col_middle:
    st.subheader("Translation & Analysis")
    
    text_input = st.text_area("Nhập đoạn văn tiếng Anh (Nhiều câu/Đoạn văn dài):", height=150, key="main_text_input")
    context_input = st.text_input("Nhập mô tả ngữ cảnh bổ sung (Tùy chọn):", key="main_context_input")
    
    st.markdown("---")
    
    st.markdown("### 📝 Phần Dịch thuật & Sửa lỗi")
    if st.button("Tiến hành Dịch & Kiểm tra lỗi", key="run_translation_btn", use_container_width=True):
        if text_input.strip():
            ctx_prompt = context_input.strip() if context_input.strip() else "Người dùng chưa chỉ định. Hãy tự động phân tích sâu đoạn văn để xác định."
            
            prompt_translation = f"""
            Bạn là một chuyên gia ngôn ngữ học tiếng Anh thực hiện quét lỗi chính tả, ngữ pháp và tối ưu hóa văn phong một cách hệ thống và nhất quán tuyệt đối.
            
            [DỮ LIỆU ĐOẠN VĂN GỐC]
            ---
            {text_input}
            ---
            
            [GỢI Ý NGỮ CẢNH TỪ NGƯỜI DÙNG]
            ---
            {ctx_prompt}
            ---
            
            YÊU CẦU XỬ LÝ (Tuân thủ nghiêm ngặt và trình bày rõ ràng theo đúng 5 bước có tiêu đề sau):
            
            BƯỚC 1: XÁC ĐỊNH VÀ PHÂN TÍCH NGỮ CẢNH
            - Xác định rõ: Đoạn văn này thuộc thể loại nào (Email công việc, tin nhắn giao tiếp thường ngày, văn bản học thuật...)? Sắc thái văn phong nên là Trang trọng (Formal) hay Thân mật (Informal)?
            
            BƯỚC 2: ĐÁNH GIÁ CHUẨN XÁC VÀ NHẤT QUÁN
            - Quét kỹ từng từ, từng ký tự trong đoạn văn gốc dựa trên ngữ cảnh đã xác định ở Bước 1 để kiểm tra lỗi ngữ pháp, chính tả, dấu câu và sự tối ưu hóa văn phong.
            - Đưa ra kết luận rõ ràng bằng một trong hai nhãn: [ĐÚNG] hoặc [SAI / CẦN TỐI ƯU].
            
            BƯỚC 3: CHI TIẾT LỖI SAI VÀ SỬA LỖI
            - Chỉ rõ từng điểm chưa tối ưu hoặc lỗi sai: Vị trí lỗi, lý do sai hoặc lý do không phù hợp với ngữ cảnh, và phương án sửa đổi chi tiết.
            
            BƯỚC 4: XUẤT ĐOẠN VĂN TIẾNG ANH CHUẨN
            - Đặt đoạn văn tiếng Anh chuẩn xác nhất cuối cùng (đã sửa/tối ưu) vào giữa hai thẻ <EN> và </EN>. Chỉ để văn bản thuần túy, không dùng markdown bên trong thẻ này.
            
            BƯỚC 5: DỊCH THUẬT
            - Dịch đoạn văn trong thẻ <EN> sang tiếng Việt mượt mà, tự nhiên và phù hợp nhất với ngữ cảnh đã xác định ở Bước 1.
            """
            with st.spinner("AI đang xác định ngữ cảnh và quét lỗi toàn diện..."):
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt_translation,
                    config=generation_config
                )
                st.info(response.text)
                
                match = re.search(r'<EN>(.*?)</EN>', response.text, re.DOTALL)
                if match:
                    correct_en_text = match.group(1).strip()
                    st.session_state.extracted_en_clean = correct_en_text
                    try:
                        tts = gTTS(text=correct_en_text, lang='en', tld='com')
                        audio_bytes = io.BytesIO()
                        tts.write_to_fp(audio_bytes)
                        st.success("🔊 Nghe giọng đọc American English đoạn văn chuẩn:")
                        st.audio(audio_bytes.getvalue(), format='audio/mp3')
                    except Exception as e:
                        st.error("Không thể tạo giọng đọc cho đoạn văn này.")
                
                st.session_state.history.append({
                    "type": "Dịch & Sửa lỗi",
                    "text": text_input,
                    "result": response.text
                })
                save_persistent_history(st.session_state.history, st.session_state.extracted_en_clean)
        else:
            st.warning("Vui lòng nhập đoạn văn tiếng Anh trước khi bấm nút dịch.")
            
    st.markdown("---")
    
    st.markdown("### 📊 Phần Phân tích cú pháp & Ngôn ngữ")
    level_choice = st.radio(
        "Chọn cấp độ phân tích:",
        ("Level 1: Cơ bản (Cấu trúc câu, từ vựng khó, Idioms, Collocations...)", 
         "Level 2: Trung bình (Sự phối hợp thì, mệnh đề quan hệ, cấu trúc đảo ngữ...)", 
         "Level 3: Chuyên sâu (Phong cách học, ngữ dụng học, liên kết câu, sắc thái...)"),
        horizontal=True,
        key="analysis_level_radio"
    )
    
    if st.button("Tiến hành Phân tích", key="run_analysis_btn", use_container_width=True):
        if text_input.strip():
            text_to_analyze = text_input.strip()
            if st.session_state.extracted_en_clean:
                text_to_analyze = st.session_state.extracted_en_clean
            else:
                if st.session_state.history:
                    for item in reversed(st.session_state.history):
                        if item['type'] == "Dịch & Sửa lỗi":
                            match = re.search(r'<EN>(.*?)</EN>', item['result'], re.DOTALL)
                            if match:
                                text_to_analyze = match.group(1).strip()
                                st.session_state.extracted_en_clean = text_to_analyze
                                break

            level_name = level_choice.split(':')[0]
            
            if "Level 1" in level_choice:
                analysis_structure_prompt = """
                1. Phân tích Cấu trúc câu (Sentence Structure): Phân tích chi tiết các thành phần S-V-O, các mệnh đề chính/phụ của câu.
                2. Phân tích Từ vựng (Vocabulary): Liệt kê các từ vựng cốt lõi, từ khó xuất hiện kèm định nghĩa tiếng Việt rõ ràng.
                3. Phân tích Cụm từ cố định (Collocations): Liệt kê và giải thích các cụm từ luôn đi liền với nhau trong đoạn văn.
                4. Phân tích Thành ngữ (Idioms): Tìm và giải thích chi tiết các thành ngữ được sử dụng (nếu có).
                """
            elif "Level 2" in level_choice:
                analysis_structure_prompt = """
                1. Sự Phối Hợp Giữa Các Thì (Tense Coordination): Phân tích cách sử dụng thì, sự phối hợp thì giữa các mệnh đề trong đoạn văn.
                2. Phân Tích Về Mệnh Đề Quan Hệ (Relative Clauses): Chỉ ra và phân tích vai trò của các mệnh đề quan hệ (nếu có).
                3. Phân Tích Về Cấu Trúc Đảo Ngữ (Inversion): Phân tích cấu trúc đảo ngữ hoặc các điểm nhấn nhấn mạnh cấu trúc (nếu có).
                4. Phân Tích Thêm Khác (Nếu cần thiết để làm sâu sắc thêm cấu trúc ngữ pháp tầm trung).
                Kết luận: Đánh giá tổng quan về tính mạch lạc ngữ pháp và độ đa dạng cấu trúc trung cấp của đoạn văn.
                """
            else:  # Level 3
                analysis_structure_prompt = """
                1. Phân tích về Ngữ dụng học (Pragmatics Analysis): Phân tích mục đích giao tiếp, ngữ cảnh văn hóa xã hội và ý nghĩa ẩn ý của người nói.
                2. Phân tích về Phong cách học (Stylistics Analysis): Đánh giá phong cách ngôn ngữ (trang trọng, mỉa mai, học thuật...), biện pháp tu từ, nhịp điệu câu văn.
                3. Phân tích về Liên kết văn bản (Textual Cohesion and Coherence): Phân tích sự liên kết từ vựng, ngữ pháp (Cohesion) và tính mạch lạc về mặt ý tưởng (Coherence).
                4. Phân tích về Sắc thái biểu đạt nâng cao (Advanced Nuances of Expression): Phân tích các từ mang tính giảm nhẹ, nhấn mạnh, sắc thái biểu cảm sâu sắc của người viết.
                Kết luận: Đánh giá tổng quan cấp độ chuyên gia về tính nghệ thuật, độ mượt mà và sức ảnh hưởng của văn bản.
                """

            prompt_analysis = f"""
            Bạn là một chuyên gia ngôn ngữ học. Hãy bắt đầu bài phân tích bằng câu chào cố định sau (giữ đúng cấu trúc chính xác không thay đổi):
            "Chào bạn, với vai trò là một chuyên gia ngôn ngữ học, tôi xin phân tích đoạn văn tối ưu theo đúng cấp độ {level_name}."
            
            Tiếp theo, hãy phân tích đoạn văn tiếng Anh chuẩn xác đã qua tối ưu sau đây:
            "{text_to_analyze}"
            
            Yêu cầu phân tích chi tiết theo đúng cấu trúc tiêu đề được quy định sau đây:
            {analysis_structure_prompt}
            
            Hãy trình bày một cách logic, dễ hiểu, chia rõ các mục gạch đầu dòng khoa học.
            """
            with st.spinner(f"AI đang tiến hành phân tích đoạn văn chuẩn theo {level_name}..."):
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt_analysis,
                    config=generation_config
                )
                st.success(response.text)
                
                st.session_state.history.append({
                    "type": f"Phân tích ({level_name})",
                    "text": text_to_analyze,
                    "result": response.text
                })
                save_persistent_history(st.session_state.history, st.session_state.extracted_en_clean)
        else:
            st.warning("Vui lòng nhập đoạn văn tiếng Anh trước khi bấm nút phân tích.")

# KHUNG PHẢI: AI Companion
with col_right:
    st.subheader("AI Companion")
    st.markdown("**💡 Câu hỏi mẫu:**")
    
    if text_input.strip():
        short_text = text_input.strip().split('.')[0]
        sample_1 = f"Giải thích thêm về cụm từ '{short_text}'"
        sample_2 = "Tìm các từ đồng nghĩa hoặc cách diễn đạt khác hay hơn cho đoạn văn trên."
        sample_3 = "Chuyển đoạn văn trên sang dạng văn phong giao tiếp hằng ngày (Casual English)."
    else:
        sample_1 = "Làm sao để phân biệt nhanh giữa Danh từ ghép và Cụm động từ trong tiếng Anh?"
        sample_2 = "Chia sẻ phương pháp luyện nghe nối âm (Connected Speech) hiệu quả tại nhà."
        sample_3 = "Cách viết số đếm bằng chữ (two) và bằng số (2) trong văn phong trang trọng?"

    if st.button("👉 " + sample_1, key="companion_custom_btn_1"):
        st.session_state.companion_input_value = sample_1
        st.rerun()
    if st.button("👉 " + sample_2, key="companion_custom_btn_2"):
        st.session_state.companion_input_value = sample_2
        st.rerun()
    if st.button("👉 " + sample_3, key="companion_custom_btn_3"):
        st.session_state.companion_input_value = sample_3
        st.rerun()
        
    st.markdown("---")
    
    chat_input = st.text_area(
        "Nhập câu hỏi của Boss tại đây:", 
        value=st.session_state.companion_input_value, 
        height=130, 
        placeholder="Gõ câu hỏi hoặc bấm vào câu hỏi mẫu ở trên...",
        key="companion_text_area"
    )
    
    if chat_input != st.session_state.companion_input_value:
        st.session_state.companion_input_value = chat_input
    
    if st.button("Gửi câu hỏi", key="submit_companion_question_btn", use_container_width=True):
        if st.session_state.companion_input_value.strip():
            with st.spinner("AI đang trả lời..."):
                current_context = st.session_state.extracted_en_clean if st.session_state.extracted_en_clean else text_input
                context_payload = f"Đoạn văn đang học: '{current_context}'\n\nCâu hỏi: {st.session_state.companion_input_value}" if current_context.strip() else chat_input
                
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=context_payload,
                    config=generation_config
                )
                st.markdown("---")
                st.info(response.text)
