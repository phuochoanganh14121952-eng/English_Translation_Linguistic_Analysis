import streamlit as st
import json
import os
from google import genai
from google.genai import types

# 1. Cấu hình giao diện rộng toàn màn hình
st.set_page_config(layout="wide")

# 2. Khởi tạo State lưu trữ dữ liệu cục bộ
if "history" not in st.session_state:
    st.session_state.history = []
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "dark"

# 3. Ép cấu hình giao diện Sáng / Tối trực diện
if st.session_state.theme_mode == "dark":
    st.markdown(
        """
        <style>
        .stApp { background-color: #0E1117; color: #FFFFFF; }
        .stButton>button { background-color: #262730; color: white; border: 1px solid #4A4A4A; }
        </style>
        """, unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <style>
        .stApp { background-color: #FFFFFF; color: #000000; }
        .stButton>button { background-color: #F0F2F6; color: black; border: 1px solid #D6D6D6; }
        </style>
        """, unsafe_allow_html=True
    )

# Thanh nút bấm chuyển đổi chế độ sáng tối nhanh ở góc trên
t_col1, t_col2 = st.columns([28, 2])
with t_col2:
    if st.button("☀️/🌙", help="Thay đổi chế độ sáng/tối"):
        st.session_state.theme_mode = "light" if st.session_state.theme_mode == "dark" else "dark"
        st.rerun()

# 4. Phân chia tỷ lệ chính xác cho 3 cột: 8 / 12 / 10
col_left, col_mid, col_right = st.columns([8, 12, 10])

# ==========================================
# CỘT TRÁI (Tỷ lệ 8): Nhập API Key & Quản lý lịch sử
# ==========================================
with col_left:
    st.subheader("Cấu hình & Lịch sử")
    
    # Ô điền mã API key bảo mật dạng dấu chấm
    api_key = st.text_input("Nhập Gemini API Key:", type="password", help="Dán mã key của bạn vào đây")
    
    st.write("---")
    
    # Khu vực quản lý nút xóa lịch sử
    h_col1, h_col2 = st.columns([3, 1])
    with h_col1:
        st.markdown("**History (Lịch sử):**")
    with h_col2:
        # Biểu tượng thùng rác xóa TOÀN BỘ (ALL)
        if st.button("🗑️ ALL", help="Xóa toàn bộ lịch sử trò chuyện"):
            st.session_state.history = []
            st.rerun()
            
    # Duyệt hiển thị lịch sử và nút xóa từng phần
    if st.session_state.history:
        for idx, item in enumerate(st.session_state.history):
            item_col1, item_col2 = st.columns([5, 1])
            with item_col1:
                # Hiển thị tiêu đề câu hỏi rút gọn để tránh tràn cột
                label = item["question"][:20] + "..." if len(item["question"]) > 20 else item["question"]
                st.caption(f"{idx+1}. {label}")
            with item_col2:
                # Nút xóa từng phần tử riêng biệt
                if st.button("❌", key=f"del_{idx}", help="Xóa đoạn này"):
                    st.session_state.history.pop(idx)
                    st.rerun()
    else:
        st.caption("Chưa có lịch sử dữ liệu.")

# ==========================================
# CỘT GIỮA (Tỷ lệ 12): Tạm thời để trống
# ==========================================
with col_mid:
    st.subheader("Không gian xử lý")
    st.info("Cột giữa tạm để trống. Đang chờ mô tả công dụng app để thiết lập sau.")

# ==========================================
# CỘT PHẢI (Tỷ lệ 10): AI Companion (Dùng Gemini-3.5-Flash)
# ==========================================
with col_right:
    st.subheader("AI Companion")
    
    # Ô nhập nội dung hội thoại
    user_input = st.text_area("Hỏi AI Companion:", height=100, placeholder="Nhập nội dung cần hỏi...")
    
    if st.button("Gửi câu hỏi"):
        if not api_key:
            st.error("Vui lòng nhập API Key ở cột trái!")
        elif not user_input.strip():
            st.warning("Vui lòng gõ câu hỏi!")
        else:
            with st.spinner("Đang kết nối AI..."):
                try:
                    # Khởi tạo client cấu trúc thư viện google-genai thế hệ mới
                    client = genai.Client(api_key=api_key)
                    
                    # Gọi trực tiếp mô hình gemini-3.5-flash theo yêu cầu
                    response = client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=user_input,
                    )
                    
                    # Ghi nhận thông tin vào mảng lịch sử trò chuyện
                    st.session_state.history.append({
                        "question": user_input,
                        "answer": response.text
                    })
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Lỗi hệ thống: {str(e)}")
                    
    # Vùng hiển thị kết quả tương tác mới nhất ngay phía dưới
    if st.session_state.history:
        st.write("---")
        latest = st.session_state.history[-1]
        st.markdown(f"**Câu hỏi:** {latest['question']}")
        st.markdown(f"**Kết quả từ AI:**\n{latest['answer']}")