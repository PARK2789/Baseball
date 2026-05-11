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
from PIL import Image
import io

# 1. 페이지 설정
st.set_page_config(page_title="CEO Talk+ Victory", page_icon="⚾️", layout="centered")

# 2. 강력한 스크롤 초기화 함수 (제안해주신 로직 반영)
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
                } catch(e) {
                    el.scrollTop = 0;
                }
                el.scrollTop = 0;
            });
            try {
                window.parent.scrollTo(0, 0);
            } catch(e) {}
        }
        // 즉시 실행 및 렌더링 타이밍을 고려한 다단계 실행
        scrollTopNow();
        setTimeout(scrollTopNow, 50);
        setTimeout(scrollTopNow, 150);
        setTimeout(scrollTopNow, 300);
        </script>
        """,
        height=0,
    )

# 3. Firebase / Firestore 설정
@st.cache_resource
def get_db():
    try:
        creds_dict = json.loads(st.secrets["textkey"])
        creds = service_account.Credentials.from_service_account_info(creds_dict)
        return firestore.Client(credentials=creds)
    except:
        return None

db = get_db()
app_id = "ceo-talk-victory-2026"
COLLECTION_PATH = f"artifacts/{app_id}/public/data/cheers"

# 4. 이미지 처리 및 데이터 로드
@st.cache_data
def get_base64_img(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            return base64.b64encode(data).decode()
        except: pass
    return ""

def compress_image(uploaded_file):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    width, height = img.size
    if width > 800:
        ratio = 800 / width
        img = img.resize((800, int(height * ratio)), Image.Resampling.LANCZOS)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=70)
    return base64.b64encode(img_byte_arr.getvalue()).decode()

def load_app_data():
    p_data = {}
    if os.path.exists("programs.json"):
        try:
            with open("programs.json", "r", encoding="utf-8") as f:
                p_data = json.load(f)
        except: pass
    return p_data

program_data = load_app_data()
img_stadium = get_base64_img("stadium.jpg") 
hero_bg = f"data:image/jpeg;base64,{img_stadium}" if img_stadium else ""

# 5. 세션 상태 관리 및 내비게이션
if 'view' not in st.session_state:
    st.session_state.view = 'home'
if 'prev_view' not in st.session_state:
    st.session_state.prev_view = 'home'
if 'target' not in st.session_state:
    st.session_state.target = None

# 페이지 전환 감지 및 스크롤 초기화 실행
if st.session_state.prev_view != st.session_state.view:
    force_scroll_top()
    st.session_state.prev_view = st.session_state.view

def navigate_to(view, target=None):
    st.session_state.view = view
    st.session_state.target = target
    st.rerun()

def normalize_name(text):
    if not text: return ""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = "".join(unicodedata.normalize('NFC', clean).split())
    return clean

# 6. 관리자 설정 (사이드바)
with st.sidebar:
    st.title("🛡️ Admin")
    admin_password = st.text_input("관리자 암호", type="password")
    is_admin = (admin_password == "1234") 
    if is_admin:
        st.success("관리자 모드 활성화")

# 7. 프리미엄 CSS
st.markdown(f"""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp {{ font-family: 'Pretendard', sans-serif; }}
    html, body, [data-testid="stAppViewContainer"] {{ overflow-x: hidden !important; width: 100% !important; }}
    
    .block-container {{ 
        padding-top: 4.5rem !important; 
        padding-bottom: 2rem !important; 
        max-width: 100% !important; 
    }}
    
    .hero-section {{
        background: linear-gradient(rgba(0,0,0,0.2), rgba(0,0,0,0.55)), url('{hero_bg}');
        background-size: cover; background-position: center;
        padding: 130px 25px 40px 25px; border-radius: 0 0 35px 35px;
        color: white; text-align: left; 
        margin: -6rem -1rem 1rem -1rem;
    }}
    
    .hero-title {{ font-weight: 900; font-size: 36px; line-height: 1.1; letter-spacing: -2px; }}
    .info-box {{ background-color: #F2F2F7; padding: 14px 18px; border-radius: 20px; border: 1px solid #E5E5EA; margin-bottom: 10px; }}
    
    .program-card {{
        position: relative; height: 160px; border-radius: 22px; margin-bottom: 4px; 
        overflow: hidden; background-size: cover; background-position: center; 
        display: flex; flex-direction: column; justify-content: flex-end; padding: 18px; color: white;
    }}
    .card-overlay {{ position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(to bottom, rgba(0,0,0,0) 30%, rgba(0,0,0,0.85) 100%); z-index: 1; }}
    
    .stButton>button {{ 
        width: 100%; border-radius: 16px; background-color: #003087;
        color: white; font-weight: 700; border: none; height: 3.5em; font-size: 15px; margin-bottom: 10px; 
        box-shadow: 0 4px 12px rgba(0,48,135,0.2);
    }}
    
    .secondary-btn button {{
        background-color: #F2F2F7 !important; color: #1C1C1E !important; box-shadow: none !important;
    }}

    .cheer-card {{
        background-color: white; border-radius: 20px; padding: 15px;
        border: 1px solid #E5E5EA; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
    .cheer-img {{ width: 100%; border-radius: 12px; margin-top: 10px; object-fit: cover; max-height: 400px; }}
</style>
""", unsafe_allow_html=True)

# --- 화면 렌더링 ---

# [1] HOME VIEW
if st.session_state.view == 'home':
    st.markdown(f'<div class="hero-section"><div class="hero-title">CEO Talk⁺<br>Victory Edition</div><div style="font-size: 16px; opacity: 0.9; margin-top: 8px;">함께 소통하고 함께 응원합니다!</div></div>', unsafe_allow_html=True)

    st.markdown("#### 💬 실시간 소통")
    if st.button("📸 승리의 응원벽 참여하기"):
        navigate_to('cheer')

    st.markdown("#### 🏟️ 구장 안내 (잠실 102블록)")
    m = folium.Map(location=[37.5122, 127.0719], zoom_start=16, tiles="cartodbvoyager")
    for name, info in program_data.items():
        folium.Marker([info["lat"], info["lon"]], popup=folium.Popup(name, max_width=150), icon=folium.Icon(color=info["color"], icon=info["icon"], prefix='fa')).add_to(m)
        label_html = f'<div style="font-size: 10px; font-weight: 800; color: #1C1C1E; text-align: center; background-color: rgba(255, 255, 255, 0.85); padding: 2px 6px; border-radius: 8px; border: 1px solid #E5E5EA; white-space: nowrap;">{name}</div>'
        folium.Marker([info["lat"], info["lon"]], icon=folium.features.DivIcon(icon_size=(100,20), icon_anchor=(50, -15), html=label_html)).add_to(m)
    
    st_folium(m, width="100%", height=250, key="stadium_map")

    st.markdown('<h4 style="margin-top:25px; margin-bottom:10px;">🚩 관전 가이드</h4>', unsafe_allow_html=True)
    for name, info in program_data.items():
        img_raw = get_base64_img(info.get("bg_file", ""))
        bg_url = f"data:image/jpeg;base64,{img_raw}" if img_raw else ""
        st.markdown(f'<div class="program-card" style="background-image: url(\'{bg_url}\');"><div class="card-overlay"></div><div class="card-content"><div style="font-size:11px; font-weight:700; opacity:0.8;">{info.get("tag")}</div><div style="font-size: 20px; font-weight: 800;">{name}</div></div></div>', unsafe_allow_html=True)
        if st.button(f"{name} 상세보기", key=f"btn_{name}"):
            navigate_to('detail', name)

# [2] CHEER VIEW (피드 목록 화면)
elif st.session_state.view == 'cheer':
    st.markdown('<h2 style="font-weight:900; margin-bottom:5px;">📸 승리의 응원벽</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#636366; margin-bottom:20px;">현장의 뜨거운 열기를 공유해주세요!</p>', unsafe_allow_html=True)

    if st.button("✨ 나도 응원 남기기"):
        navigate_to('upload')

    st.markdown("---")
    
    if db:
        docs = db.collection(COLLECTION_PATH).stream()
        posts = []
        for doc in docs:
            p = doc.to_dict()
            p['id'] = doc.id
            posts.append(p)
        posts.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)

        if not posts:
            st.info("아직 올라온 응원이 없습니다.")
        else:
            for post in posts[:40]:
                img_html = f'<img src="data:image/jpeg;base64,{post["image"]}" class="cheer-img">' if post.get("image") else ""
                time_str = post['timestamp'].strftime('%H:%M') if 'timestamp' in post else ""
                st.markdown(f"""
                <div class="cheer-card">
                    <div style="font-weight:800; font-size:14px; display:flex; justify-content:space-between;">
                        <span>👤 {post['name']}</span>
                        <span style="color:#8E8E93; font-weight:400; font-size:11px;">{time_str}</span>
                    </div>
                    <div style="margin-top:10px; font-size:16px; color:#1C1C1E; line-height:1.4;">{post['text']}</div>
                    {img_html}
                </div>
                """, unsafe_allow_html=True)
                
                if is_admin:
                    if st.button(f"🗑️ 삭제", key=f"del_{post['id']}"):
                        db.collection(COLLECTION_PATH).document(post['id']).delete()
                        st.rerun()
    
    st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
    if st.button("🏠 메인으로 돌아가기", key="back_home"):
        navigate_to('home')
    st.markdown('</div>', unsafe_allow_html=True)

# [3] UPLOAD VIEW (글쓰기 전용 화면)
elif st.session_state.view == 'upload':
    st.markdown('<h2 style="font-weight:900; margin-bottom:5px;">✨ 응원 남기기</h2>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        c_name = st.text_input("닉네임 또는 조", placeholder="예: 5조 승리요정")
        c_text = st.text_area("응원 메시지", placeholder="LG이노텍 화이팅!", max_chars=100)
        c_file = st.file_uploader("사진 선택", type=['jpg', 'jpeg', 'png'])
        st.markdown('</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 게시하기"):
                if c_name and c_text and db:
                    with st.spinner("전송 중..."):
                        img_b64 = compress_image(c_file) if c_file else ""
                        db.collection(COLLECTION_PATH).add({
                            "name": c_name, "text": c_text, "image": img_b64, "timestamp": datetime.now()
                        })
                        navigate_to('cheer')
                else: st.warning("이름과 메시지를 입력해주세요.")
        with col2:
            st.markdown('<div class="secondary-btn">', unsafe_allow_html=True)
            if st.button("❌ 취소"):
                navigate_to('cheer')
            st.markdown('</div>', unsafe_allow_html=True)

# [4] DETAIL VIEW
elif st.session_state.view == 'detail':
    name = st.session_state.target
    item = program_data.get(name, {})
    img_raw = get_base64_img(item.get("bg_file", ""))
    bg_url = f"data:image/jpeg;base64,{img_raw}" if img_raw else ""
    
    points_html = "".join([f'<div style="margin-bottom:10px; font-size:15px;">• {p}</div>' for p in item.get("points", [])])
    
    st.markdown(f"""
    <div style="background: linear-gradient(rgba(0,0,0,0.1), rgba(0,0,0,0.5)), url('{bg_url}'); 
                background-size: cover; background-position: center; height: 180px; 
                border-radius: 20px; margin: 0 0 15px 0; display: flex; align-items: flex-end; padding: 20px;">
        <div style="color: white;">
            <div style="font-size: 11px; font-weight: 700; opacity: 0.8;">{item.get('tag')}</div>
            <div style="font-size: 26px; font-weight: 900;">{name}</div>
        </div>
    </div>
    <div style="background-color: #F8F9FA; padding: 25px; border-radius: 25px; border: 1px solid #E5E5EA;">
        <h3 style="margin:0 0 12px 0; font-weight:800; color:#1C1C1E;">{item.get('detail_title')}</h3>
        <p style="font-size: 16px; color: #3A3A3C; line-height: 1.6;">{item.get('desc')}</p>
        <hr style="border: 0; border-top: 1px solid #E5E5EA; margin: 20px 0;">
        {points_html}
    </div>
    <div style="margin-top:20px;"></div>
    """, unsafe_allow_html=True)

    if st.button("🏠 메인으로 돌아가기"):
        navigate_to('home')

st.markdown("<p style='text-align:center; color:#C7C7CC; font-size:12px; margin-top:30px;'>© 2026 LG Innotek Talent Development Team</p>", unsafe_allow_html=True)

