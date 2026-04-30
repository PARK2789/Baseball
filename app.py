```python
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

# 1. 페이지 설정
st.set_page_config(page_title="CEO Talk+ Victory", page_icon="⚾️", layout="centered")

# 2. 세션 상태 관리
if 'view' not in st.session_state:
    st.session_state.view = 'home'
if 'target' not in st.session_state:
    st.session_state.target = None

# 3. 이미지 및 데이터 처리 (캐싱 적용)
@st.cache_data
def get_base64_img(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            return base64.b64encode(data).decode()
        except: pass
    return ""

def load_app_data():
    p_data = {}
    if os.path.exists("programs.json"):
        try:
            with open("programs.json", "r", encoding="utf-8") as f:
                p_data = json.load(f)
        except: pass
    m_data = {}
    if os.path.exists("members.csv"):
        try:
            df = pd.read_csv("members.csv")
            m_data = dict(zip(df['조'], df['명단']))
        except: pass
    return p_data, m_data

program_data, member_data = load_app_data()
# 야구장 배경 사진으로 stadium.jpg를 준비해 주세요
img_stadium = get_base64_img("stadium.jpg") 
hero_bg = f"data:image/jpeg;base64,{img_stadium}" if img_stadium else ""

# 4. 프리미엄 CSS (여백 및 버튼 축소 유지)
st.markdown(f"""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp {{ font-family: 'Pretendard', sans-serif; }}
    html, body, [data-testid="stAppViewContainer"] {{ overflow-x: hidden !important; width: 100% !important; }}
    .block-container {{ padding-top: 1.2rem !important; padding-bottom: 0.5rem !important; max-width: 100% !important; }}
    [data-testid="stVerticalBlock"] > div {{ gap: 0.25rem !important; }}
    
    .hero-section {{
        background: linear-gradient(rgba(0,0,0,0.2), rgba(0,0,0,0.55)), url('{hero_bg}');
        background-size: cover; background-position: center;
        padding: 130px 25px 40px 25px; border-radius: 0 0 35px 35px;
        color: white; text-align: left; margin: -5rem -1rem 1rem -1rem;
    }}
    .hero-title {{ font-weight: 900; font-size: 36px; line-height: 1.1; letter-spacing: -2px; }}
    .info-box {{ background-color: #F2F2F7; padding: 14px 18px; border-radius: 20px; border: 1px solid #E5E5EA; margin-bottom: 6px; }}
    
    .program-card {{
        position: relative; height: 180px; border-radius: 22px; margin-bottom: 4px; 
        overflow: hidden; background-size: cover; background-position: center; 
        display: flex; flex-direction: column; justify-content: flex-end; padding: 18px; color: white;
    }}
    .card-overlay {{ position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(to bottom, rgba(0,0,0,0) 30%, rgba(0,0,0,0.85) 100%); z-index: 1; }}
    .card-content {{ position: relative; z-index: 2; pointer-events: none; }}
    .card-title {{ font-size: 20px; font-weight: 800; letter-spacing: -0.8px; }}
    
    /* 상세보기 및 돌아가기 버튼 (축소형) */
    .stButton>button {{ 
        width: 100%; border-radius: 12px; background-color: #003087; /* 야구 느낌 남색 */
        color: white; font-weight: 600; border: none; height: 2.8em; font-size: 14px; margin-bottom: 12px; 
    }}
</style>
""", unsafe_allow_html=True)

def navigate_to(view, target=None):
    st.session_state.view = view
    st.session_state.target = target
    st.rerun()

def normalize_name(text):
    if not text: return ""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = "".join(unicodedata.normalize('NFC', clean).split())
    return clean

# --- 화면 렌더링 ---
if st.session_state.view == 'home':
    st.markdown(f"""
    <div class="hero-section">
        <div class="hero-title">CEO Talk⁺<br>Victory Edition</div>
        <div style="font-size: 16px; opacity: 0.9; margin-top: 8px;">하나 된 함성, 승리를 향한 뜨거운 열정!<br>잠실 야구장에서 함께 응원합니다.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 🚌 이동 안내")
    st.markdown(f"""
    <div class="info-box">
        <div style="font-weight:800; color:#007AFF; font-size:14px;">📍 잠실행 단체 버스</div>
        <div style="font-size:15px; color:#1C1C1E; font-weight:600;">각 공장 정문 / 15:30 정시 출발</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 🏟️ 구장 안내 (잠실)")
    # 잠실야구장 중심 위치
    m = folium.Map(location=[37.5122, 127.0719], zoom_start=16, tiles="cartodbvoyager")
    for name, info in program_data.items():
        popup_html = f'<div style="font-size:13px; font-weight:600; font-family:Pretendard; text-align:center;">{name}</div>'
        folium.Marker([info["lat"], info["lon"]], 
                      popup=folium.Popup(popup_html, max_width=150),
                      icon=folium.Icon(color=info["color"], icon=info["icon"], prefix='fa')).add_to(m)
        label_html = f'<div style="font-size: 10px; font-weight: 800; color: #1C1C1E; text-align: center; background-color: rgba(255, 255, 255, 0.85); padding: 2px 6px; border-radius: 8px; border: 1px solid #E5E5EA; white-space: nowrap; font-family: Pretendard;">{name}</div>'
        folium.Marker([info["lat"], info["lon"]], icon=folium.features.DivIcon(icon_size=(100,20), icon_anchor=(50, -15), html=label_html)).add_to(m)
    
    map_res = st_folium(m, width="100%", height=250, key="stadium_map")
    
    if map_res and map_res.get("last_object_clicked_popup"):
        clicked_raw = map_res["last_object_clicked_popup"]
        clicked_normalized = normalize_name(clicked_raw)
        for key in program_data.keys():
            if normalize_name(key) == clicked_normalized:
                navigate_to('detail', key)
                break

    st.markdown('<h4 style="margin-top:25px; margin-bottom:8px;">🚩 관전 가이드</h4>', unsafe_allow_html=True)
    for name, info in program_data.items():
        img_raw = get_base64_img(info.get("bg_file", ""))
        bg_url = f"data:image/jpeg;base64,{img_raw}" if img_raw else ""
        st.markdown(f"""
        <div class="program-card" style="background-image: url('{bg_url}');">
            <div class="card-overlay"></div>
            <div class="card-content">
                <div style="font-size:11px; font-weight:700; opacity:0.8;">{info.get('tag')}</div>
                <div class="card-title">{name}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"{name} 자세히 보기", key=f"btn_{name}"):
            navigate_to('detail', name)

    st.markdown(f"""
    <div class="info-box" style="text-align:center; margin-top:20px;">
        <h6 style="margin:0; font-weight:800; color:#1C1C1E;">📞 운영 본부 안내</h6>
        <p style="color:#3A3A3C; font-size:13px; margin:2px 0 0 0;">
            박성식 책임 <a href="tel:010-1234-5678" style="color:#007AFF; text-decoration:none; font-weight:700;">010-1234-5678</a>
        </p>
    </div>
    """, unsafe_allow_html=True)

elif st.session_state.view == 'detail':
    name = st.session_state.target
    item = program_data.get(name, {})
    img_raw = get_base64_img(item.get("bg_file", ""))
    bg_url = f"data:image/jpeg;base64,{img_raw}" if img_raw else ""
    
    st.markdown(f"""
    <div style="background: linear-gradient(rgba(0,0,0,0.1), rgba(0,0,0,0.5)), url('{bg_url}'); 
                background-size: cover; background-position: center; height: 160px; 
                border-radius: 20px; margin: 0 0 8px 0; display: flex; align-items: flex-end; padding: 20px;">
        <div style="color: white;">
            <div style="font-size: 11px; font-weight: 700; opacity: 0.8;">{item.get('tag')}</div>
            <div style="font-size: 24px; font-weight: 900; line-height: 1.1;">{name}</div>
        </div>
    </div>
    <div style="background-color: #F8F9FA; padding: 18px 22px; border-radius: 22px; border: 1px solid #E5E5EA;">
        <h3 style="margin-top:0; margin-bottom:8px; font-weight:800; font-size: 20px;">{item.get('detail_title')}</h3>
        <p style="font-size: 15px; color: #3A3A3C; line-height: 1.5; margin-bottom: 10px;">{item.get('desc')}</p>
        <hr style="border: 0; border-top: 1px solid #E5E5EA; margin: 12px 0;">
        {"".join([f'<div style="margin-bottom:6px; font-size:15px;">• {p}</div>' for p in item.get('points', [])])}
    </div>
    <div style="margin-top:12px;"></div>
    """, unsafe_allow_html=True)

    if st.button("← 메인 화면으로 돌아가기"):
        navigate_to('home')

st.markdown("<p style='text-align:center; color:#C7C7CC; font-size:11px; margin-top:10px;'>© 2026 LG Innotek Talent Development Team</p>", unsafe_allow_html=True)

```
