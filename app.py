# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import base64
import os
import json
import re
import unicodedata
from datetime import datetime
from google.cloud import firestore
from google.oauth2 import service_account
from PIL import Image
import io

# 1. 페이지 설정
st.set_page_config(page_title="CEO Talk+ Victory", page_icon="⚾️", layout="centered")

# 2. Firebase / Firestore 보안 설정
@st.cache_resource
def get_db():
    try:
        # Streamlit Secrets에서 보안 키 로드 (GitHub 노출 방지)
        creds_dict = json.loads(st.secrets["textkey"])
        creds = service_account.Credentials.from_service_account_info(creds_dict)
        return firestore.Client(credentials=creds)
    except Exception as e:
        return None

db = get_db()
app_id = "ceo-talk-victory-2026"
# 보안 권장 경로 준수
COLLECTION_PATH = f"artifacts/{app_id}/public/data/cheers"

# 3. 이미지 압축 로직 (DDoS 및 용량 초과 방지)
def compress_image(uploaded_file):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    width, height = img.size
    if width > 800:
        ratio = 800 / width
        img = img.resize((800, int(height * ratio)), Image.Resampling.LANCZOS)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=65) # 보안과 성능을 위해 65% 압축
    return base64.b64encode(img_byte_arr.getvalue()).decode()

# 4. 데이터 로드 및 처리 (기존 로직 유지)
@st.cache_data
def get_base64_img(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f: data = f.read()
            return base64.b64encode(data).decode()
        except: pass
    return ""

def load_app_data():
    p_data = {}
    if os.path.exists("programs.json"):
        try:
            with open("programs.json", "r", encoding="utf-8") as f: p_data = json.load(f)
        except: pass
    return p_data

program_data = load_app_data()
img_stadium = get_base64_img("stadium.jpg") 
hero_bg = f"data:image/jpeg;base64,{img_stadium}" if img_stadium else ""

# 5. 프리미엄 CSS (변동 없음)
st.markdown(f"""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp {{ font-family: 'Pretendard', sans-serif; }}
    .block-container {{ padding-top: 1.2rem !important; padding-bottom: 0.5rem !important; }}
    .hero-section {{
        background: linear-gradient(rgba(0,0,0,0.2), rgba(0,0,0,0.55)), url('{hero_bg}');
        background-size: cover; background-position: center;
        padding: 130px 25px 40px 25px; border-radius: 0 0 35px 35px;
        color: white; margin: -5rem -1rem 1rem -1rem;
    }}
    .info-box {{ background-color: #F2F2F7; padding: 14px 18px; border-radius: 20px; border: 1px solid #E5E5EA; margin-bottom: 6px; }}
    .stButton>button {{ width: 100%; border-radius: 12px; background-color: #003087; color: white; height: 2.8em; font-size: 14px; }}
    .cheer-card {{ background-color: white; border-radius: 18px; padding: 15px; border: 1px solid #E5E5EA; margin-bottom: 12px; }}
    .cheer-img {{ width: 100%; border-radius: 12px; margin-top: 10px; }}
</style>
""", unsafe_allow_html=True)

# --- 내비게이션 및 정규화 ---
if 'view' not in st.session_state: st.session_state.view = 'home'
def navigate_to(view, target=None):
    st.session_state.view, st.session_state.target = view, target
    st.rerun()

def normalize_name(text):
    clean = re.sub(r'<[^>]+>', '', text or "").strip()
    return "".join(unicodedata.normalize('NFC', clean).split())

# --- 메인 화면 ---
if st.session_state.view == 'home':
    st.markdown(f'<div class="hero-section"><div style="font-weight:900; font-size:36px; line-height:1.1;">CEO Talk⁺<br>Victory Wall</div></div>', unsafe_allow_html=True)

    # 지도 및 가이드 (기존과 동일)
    st.markdown("#### 🏟️ 구장 안내 (잠실 102블록)")
    m = folium.Map(location=[37.5122, 127.0719], zoom_start=16, tiles="cartodbvoyager")
    for name, info in program_data.items():
        folium.Marker([info["lat"], info["lon"]], popup=folium.Popup(name, max_width=150)).add_to(m)
    st_folium(m, width="100%", height=250, key="stadium_map")

    # [응원벽 게시판]
    st.markdown('<h4 style="margin-top:30px;">📸 승리의 응원벽</h4>', unsafe_allow_html=True)
    with st.expander("✨ 메시지 남기기 (보안 모드)", expanded=False):
        c_name = st.text_input("닉네임/조")
        c_text = st.text_area("응원 메시지 (100자 내외)")
        c_file = st.file_uploader("현장 사진 업로드", type=['jpg', 'jpeg', 'png'])
        
        if st.button("안전하게 게시하기"):
            if c_name and c_text and db:
                img_b64 = compress_image(c_file) if c_file else ""
                db.collection(COLLECTION_PATH).add({
                    "name": c_name, "text": c_text, "image": img_b64, "timestamp": datetime.now()
                })
                st.success("게시 완료!")
                st.rerun()
            else: st.warning("내용을 입력해주세요.")

    if db:
        posts = [doc.to_dict() for doc in db.collection(COLLECTION_PATH).stream()]
        posts.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
        for post in posts[:15]:
            img_html = f'<img src="data:image/jpeg;base64,{post["image"]}" class="cheer-img">' if post.get("image") else ""
            st.markdown(f'<div class="cheer-card"><b>{post["name"]}</b><br>{post["text"]}{img_html}</div>', unsafe_allow_html=True)
    else: st.info("데이터베이스 연결 대기 중...")

elif st.session_state.view == 'detail':
    # 상세 페이지 (기존 유지)
    st.write(f"상세 정보: {st.session_state.target}")
    if st.button("돌아가기"): navigate_to('home')

