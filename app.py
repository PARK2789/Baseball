# -*- coding: utf-8 -*-
import streamlit as st
import streamlit.components.v1 as components
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
from PIL import Image, ImageOps
import io

# 1. 페이지 설정 및 초기화
st.set_page_config(page_title="CEO Talk+ Victory", page_icon="⚾️", layout="centered")

# 세션 상태 초기화
if 'view' not in st.session_state:
    st.session_state.view = 'home'
if 'prev_view' not in st.session_state:
    st.session_state.prev_view = 'home'
if 'target' not in st.session_state:
    st.session_state.target = None

# 2. 강력한 스크롤 초기화 함수 (부모 DOM 제어)
def force_scroll_top():
    components.html(
        """
        <script>
        function scrollTopNow() {
            const doc = window.parent.document;
            const targets = [
                doc.querySelector('section[data-testid="stMain"]'),
                doc.querySelector('div[data-testid="stAppViewContainer"]'),
                doc.scrollingElement,
                doc.documentElement,
                doc.body
            ].filter(Boolean);
            
            targets.forEach(el => {
                try {
                    el.scrollTo({ top: 0, left: 0, behavior: "instant" });
                } catch(e) { el.scrollTop = 0; }
                el.scrollTop = 0;
            });
            try { window.parent.scrollTo(0, 0); } catch(e) {}
        }
        scrollTopNow();
        setTimeout(scrollTopNow, 30);
        setTimeout(scrollTopNow, 100);
        setTimeout(scrollTopNow, 400);
        </script>
        """,
        height=0,
    )

# 3. 내비게이션 함수
def navigate_to(view, target=None):
    st.session_state.view = view
    st.session_state.target = target
    st.rerun()

# 4. 데이터 및 이미지 처리
@st.cache_resource
def get_db():
    try:
        creds_dict = json.loads(st.secrets["textkey"])
        creds = service_account.Credentials.from_service_account_info(creds_dict)
        return firestore.Client(credentials=creds)
    except: return None

@st.cache_data
def get_base64_img(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def compress_image(uploaded_file):
    """사진 회전 방지 및 압축"""
    img = Image.open(uploaded_file)
    img = ImageOps.exif_transpose(img) # EXIF 정보를 기반으로 회전 자동 보정
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail((800, 800), Image.Resampling.LANCZOS)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=75)
    return base64.b64encode(img_byte_arr.getvalue()).decode()

db = get_db()
app_id = "ceo-talk-victory-2026"
COLLECTION_PATH = f"artifacts/{app_id}/public/data/cheers"

if os.path.exists("programs.json"):
    with open("programs.json", "r", encoding="utf-8") as f:
        program_data = json.load(f)
else: program_data = {}

img_stadium = get_base64_img("stadium.jpg") 
hero_bg = f"data:image/jpeg;base64,{img_stadium}" if img_stadium else ""

# 5. 프리미엄 CSS (여백 및 버튼 디자인)
st.markdown(f"""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp {{ font-family: 'Pretendard', sans-serif; }}
    .block-container {{ padding-top: 4.5rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }}
    
    .hero-section {{
        background: linear-gradient(rgba(0,0,0,0.2), rgba(0,0,0,0.55)), url('{hero_bg}');
        background-size: cover; background-position: center;
        padding: 130px 25px 40px 25px; border-radius: 0 0 35px 35px;
        color: white; margin: -6rem -1rem 1rem -1rem;
    }}
    .hero-title {{ font-weight: 900; font-size: 36px; line-height: 1.1; }}
    .info-box {{ background-color: #F2F2F7; padding: 16px 20px; border-radius: 20px; border: 1px solid #E5E5EA; margin-bottom: 12px; }}
    
    .program-card {{
        position: relative; height: 160px; border-radius: 22px; margin-bottom: 4px; 
        overflow: hidden; background-size: cover; background-position: center; 
        display: flex; flex-direction: column; justify-content: flex-end; padding: 18px; color: white;
    }}
    .card-overlay {{ position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(to bottom, rgba(0,0,0,0) 30%, rgba(0,0,0,0.85) 100%); z-index: 1; }}
    
    .stButton>button {{ 
        width: 100%; border-radius: 16px; background-color: #003087;
        color: white; font-weight: 700; height: 3.5em; font-size: 15px; margin-bottom: 12px; 
        box-shadow: 0 4px 12px rgba(0,48,135,0.15);
    }}
    
    .nav-btn-container {{ margin-top: 40px !important; }}
    .secondary-btn button {{ background-color: #F2F2F7 !important; color: #1C1C1E !important; box-shadow: none !important; }}

    .cheer-card {{ background-color: white; border-radius: 20px; padding: 18px; border: 1px solid #E5E5EA; margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }}
    .cheer-img {{ width: 100%; border-radius: 12px; margin-top: 10px; object-fit: cover; max-height: 500px; }}
</style>
""", unsafe_allow_html=True)

# 6. 화면 렌더링 컨트롤러 (View 가드)

if st.session_state.prev_view != st.session_state.view:
    force_scroll_top()
    st.session_state.prev_view = st.session_state.view

# 관리자 인증
with st.sidebar:
    admin_pw = st.text_input("Admin Password", type="password")
    is_admin = (admin_pw == "1234")

# 메인 컨테이너
app_main = st.container()

with app_main:
    # [1] HOME VIEW
    if st.session_state.view == 'home':
        st.markdown(f'<div class="hero-section"><div class="hero-title">CEO Talk⁺<br>Victory Edition</div><div style="font-size: 16px; opacity: 0.9; margin-top: 8px;">함께 소통하고 함께 응원합니다!</div></div>', unsafe_allow_html=True)

        st.markdown("#### 💬 실시간 소통")
        if st.button("📸 승리의 응원벽 참여하기 (사진/댓글)"):
            navigate_to('cheer')

        # [NEW] 응원가 및 경기 정보 섹션
        st.markdown("#### 🔥 응원 & 실시간 정보")
        with st.expander("⚾️ LG트윈스 응원가 배우기", expanded=False):
            st.video("https://www.youtube.com/watch?v=BhwoJFjkAf8")
            st.markdown('<p style="font-size:13px; color:#8E8E93; text-align:center;">미리 배우고 함께 목소리를 높여주세요!</p>', unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="margin-bottom: 20px;">
            <a href="https://m.sports.naver.com/baseball/index" target="_blank" style="text-decoration: none;">
                <div style="background-color: #03C75A; color: white; padding: 16px; border-radius: 16px; text-align: center; font-weight: 800; box-shadow: 0 4px 10px rgba(3,199,90,0.2);">
                    📢 네이버 실시간 경기 정보 확인하기
                </div>
            </a>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 🏟️ 구장 안내 (잠실 102블록)")
        m = folium.Map(location=[37.5122, 127.0719], zoom_start=16, tiles="cartodbvoyager")
        for name, info in program_data.items():
            folium.Marker([info["lat"], info["lon"]], popup=folium.Popup(name, max_width=150), icon=folium.Icon(color=info["color"], icon=info["icon"], prefix='fa')).add_to(m)
        st_folium(m, width="100%", height=250, key="stadium_map")

        st.markdown('<h4 style="margin-top:25px; margin-bottom:10px;">🚩 관전 가이드</h4>', unsafe_allow_html=True)
        for name, info in program_data.items():
            img_raw = get_base64_img(info.get("bg_file", ""))
            bg_url = f"data:image/jpeg;base64,{img_raw}" if img_raw else ""
            st.markdown(f'<div class="program-card" style="background-image: url(\'{bg_url}\');"><div class="card-overlay"></div><div class="card-content"><div style="font-size:11px; font-weight:700; opacity:0.8;">{info.get("tag")}</div><div style="font-size: 20px; font-weight: 800;">{name}</div></div></div>', unsafe_allow_html=True)
            if st.button(f"{name} 상세보기", key=f"btn_{name}"):
                navigate_to('detail', name)

    # [2] CHEER VIEW (피드)
    elif st.session_state.view == 'cheer':
        st.markdown('<h2 style="font-weight:900; margin-bottom:5px;">📸 승리의 응원벽</h2>', unsafe_allow_html=True)
        if st.button("✨ 나도 응원 남기기"):
            navigate_to('upload')

        st.markdown("---")
        if db:
            docs = db.collection(COLLECTION_PATH).stream()
            posts = [doc.to_dict() | {"id": doc.id} for doc in docs]
            posts.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
            for post in posts[:40]:
                img_html = f'<img src="data:image/jpeg;base64,{post["image"]}" class="cheer-img">' if post.get("image") else ""
                st.markdown(f'<div class="cheer-card"><b>👤 {post["name"]}</b><br>{post["text"]}{img_html}</div>', unsafe_allow_html=True)
                if is_admin:
                    if st.button(f"🗑️ 삭제", key=f"del_{post['id']}"):
                        db.collection(COLLECTION_PATH).document(post['id']).delete()
                        st.rerun()
        
        st.markdown('<div class="nav-btn-container secondary-btn">', unsafe_allow_html=True)
        if st.button("🏠 메인으로 돌아가기"):
            navigate_to('home')
        st.markdown('</div>', unsafe_allow_html=True)

    # [3] UPLOAD VIEW
    elif st.session_state.view == 'upload':
        st.markdown('<h2 style="font-weight:900; margin-bottom:5px;">✨ 응원 남기기</h2>', unsafe_allow_html=True)
        with st.container():
            c_name = st.text_input("닉네임 또는 조", placeholder="예: LG이노텍 3조")
            c_text = st.text_area("응원 메시지", placeholder="최강 LG! 필승 이노텍!")
            c_file = st.file_uploader("현장 사진 업로드", type=['jpg', 'jpeg', 'png'])
            
            if st.button("✅ 게시판에 등록하기"):
                if c_name and c_text and db:
                    with st.spinner("이미지 최적화 중..."):
                        img_b64 = compress_image(c_file) if c_file else ""
                        db.collection(COLLECTION_PATH).add({"name": c_name, "text": c_text, "image": img_b64, "timestamp": datetime.now()})
                        navigate_to('cheer')
                else: st.warning("이름과 메시지를 모두 입력해주세요.")
            
            st.markdown('<div class="nav-btn-container secondary-btn">', unsafe_allow_html=True)
            if st.button("❌ 취소"):
                navigate_to('cheer')
            st.markdown('</div>', unsafe_allow_html=True)

    # [4] DETAIL VIEW
    elif st.session_state.view == 'detail':
        name = st.session_state.target
        item = program_data.get(name, {})
        img_raw = get_base64_img(item.get("bg_file", ""))
        bg_url = f"data:image/jpeg;base64,{img_raw}" if img_raw else ""
        points_html = "".join([f'<div style="margin-bottom:12px; font-size:15px; color:#3A3A3C;">• {p}</div>' for p in item.get("points", [])])
        
        st.markdown(f"""
        <div style="background: linear-gradient(rgba(0,0,0,0.1), rgba(0,0,0,0.5)), url('{bg_url}'); 
                    background-size: cover; background-position: center; height: 180px; 
                    border-radius: 20px; margin: 0 0 15px 0; display: flex; align-items: flex-end; padding: 25px;">
            <div style="color: white;">
                <div style="font-size: 11px; font-weight: 700; opacity: 0.8;">{item.get('tag')}</div>
                <div style="font-size: 26px; font-weight: 900;">{name}</div>
            </div>
        </div>
        <div style="background-color: #F8F9FA; padding: 28px; border-radius: 28px; border: 1px solid #E5E5EA;">
            <h3 style="margin:0 0 15px 0; font-weight:800; color:#1C1C1E;">{item.get('detail_title')}</h3>
            <p style="font-size: 16px; color: #48484A; line-height: 1.6;">{item.get('desc')}</p>
            <hr style="border: 0; border-top: 1px solid #E5E5EA; margin: 25px 0;">
            {points_html}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="nav-btn-container secondary-btn">', unsafe_allow_html=True)
        if st.button("🏠 메인으로 돌아가기"):
            navigate_to('home')
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<p style='text-align:center; color:#C7C7CC; font-size:12px; margin-top:40px; padding-bottom: 20px;'>© 2026 LG Innotek Talent Development Team</p>", unsafe_allow_html=True)

