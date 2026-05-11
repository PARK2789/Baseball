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
if 'modal_post' not in st.session_state: # 모달에 띄울 게시물 정보
    st.session_state.modal_post = None

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
    """사진 회전 방지 및 압축 (썸네일/상세용 고해상도 유지)"""
    img = Image.open(uploaded_file)
    img = ImageOps.exif_transpose(img) 
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    # 상세 보기에서 깨지지 않도록 해상도를 조금 높게 잡습니다 (예: 1200px)
    img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=80)
    return base64.b64encode(img_byte_arr.getvalue()).decode()

db = get_db()
app_id = "ceo-talk-victory-2026"
CHEER_COLLECTION = f"artifacts/{app_id}/public/data/cheers"
EVENT_COLLECTION = f"artifacts/{app_id}/public/data/events"

if os.path.exists("programs.json"):
    with open("programs.json", "r", encoding="utf-8") as f:
        program_data = json.load(f)
else: program_data = {}

img_stadium = get_base64_img("stadium.jpg") 
hero_bg = f"data:image/jpeg;base64,{img_stadium}" if img_stadium else ""

# 5. 프리미엄 CSS (갤러리 및 모달 스타일 추가)
st.markdown(f"""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp {{ font-family: 'Pretendard', sans-serif; background-color: #FFFFFF; }}
    .block-container {{ padding-top: 4.5rem !important; padding-bottom: 2.5rem !important; max-width: 100% !important; }}
    
    .hero-section {{
        background: linear-gradient(rgba(0,0,0,0.1), rgba(0,0,0,0.4)), url('{hero_bg}');
        background-size: cover; background-position: center;
        padding: 130px 25px 40px 25px; border-radius: 0 0 35px 35px;
        color: white; margin: -6rem -1rem 1.5rem -1rem;
    }}
    .hero-title {{ font-weight: 900; font-size: 36px; line-height: 1.1; letter-spacing: -1.5px; }}
    .info-box {{ background-color: #F8F8FA; padding: 18px 22px; border-radius: 20px; border: 1px solid #E5E5EA; margin-bottom: 12px; }}
    
    .stButton>button {{ 
        width: 100%; border-radius: 16px; background-color: #3A3A3C;
        color: white; font-weight: 600; height: 3.6em; font-size: 15px; margin-bottom: 12px; 
        border: none; transition: all 0.2s ease;
        box-shadow: 0 4px 10px rgba(0,0,0,0.08);
    }}
    .secondary-btn button {{ background-color: #E5E5EA !important; color: #1C1C1E !important; box-shadow: none !important; }}
    .nav-btn-container {{ margin-top: 35px !important; }}

    /* [신규] 갤러리 스타일 */
    .gallery-item {{
        position: relative; width: 100%; padding-bottom: 100%; /* 정사각형 비율 */
        border-radius: 12px; overflow: hidden; margin-bottom: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); cursor: pointer;
        transition: transform 0.2s;
    }}
    .gallery-item:hover {{ transform: scale(1.02); }}
    .gallery-img {{
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        object-fit: cover;
    }}
    
    /* [신규] 이벤트 배너 스타일 */
    .event-banner {{
        background-color: #FFF9F9; border-left: 5px solid #FF3B30;
        padding: 15px; border-radius: 12px; margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }}
    .event-item {{
        background-color: white; padding: 10px 15px; border-radius: 10px;
        border: 1px solid #F2F2F7; margin-bottom: 8px; font-size: 13px;
    }}

    .program-card {{
        position: relative; height: 170px; border-radius: 24px; margin-bottom: 8px; 
        overflow: hidden; background-size: cover; background-position: center; 
        display: flex; flex-direction: column; justify-content: flex-end; padding: 20px;
        border: 1px solid #E5E5EA;
    }}
    .card-content {{ position: relative; z-index: 2; pointer-events: none; text-shadow: 0px 2px 4px rgba(0,0,0,0.5); }}
    .example-box {{ background-color: #FFF9F9; border: 1px dashed #FF3B30; padding: 15px; border-radius: 15px; margin-bottom: 20px; }}
</style>
""", unsafe_allow_html=True)

# 6. 화면 렌더링 로직

if st.session_state.prev_view != st.session_state.view:
    force_scroll_top()
    st.session_state.prev_view = st.session_state.view

with st.sidebar:
    admin_pw = st.text_input("Admin", type="password")
    is_admin = (admin_pw == "1234")

# [신규] 상세 보기 모달 (Dialog) 함수
@st.dialog("📸 응원 상세 보기")
def show_post_modal(post):
    st.markdown(f"""
    <div style="text-align:center;">
        <img src="data:image/jpeg;base64,{post['image']}" style="width:100%; border-radius:12px; max-height:60vh; object-fit:contain; margin-bottom:15px;">
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"### 👤 {post['name']}")
    st.write(post['text'])
    st.caption(f"작성일시: {post.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M')}")

    if is_admin:
        st.markdown("---")
        if st.button("🗑️ 관리자 삭제", key=f"modal_del_{post['id']}"):
            db.collection(CHEER_COLLECTION).document(post['id']).delete()
            st.toast("게시물이 삭제되었습니다.")
            st.session_state.modal_post = None # 모달 닫기
            st.rerun()

app_canvas = st.container()

with app_canvas:
    # [1] HOME VIEW
    if st.session_state.view == 'home':
        st.markdown(f'<div class="hero-section"><div class="hero-title">CEO Talk⁺<br>Victory Edition</div><div style="font-size: 16px; opacity: 0.9; margin-top: 10px; font-weight:500;">함께 소통하고 함께 승리합니다!</div></div>', unsafe_allow_html=True)

        st.markdown("#### 🚌 이동 및 집결 안내")
        st.markdown(f"""<div class="info-box"><div style="font-weight:800; color:#FF3B30; font-size:15px; margin-bottom:6px;">📍 단체 버스 탑승 정보</div><div style="font-size:15px; color:#1C1C1E; line-height:1.6;">• <b>장소:</b> E1/E3 동 정문 앞 버스 탑승<br>• <b>집결:</b> 16:25까지 집결 완료<br>• <b>출발:</b> 16:30 정시 출발</div></div>""", unsafe_allow_html=True)

        st.markdown("#### 💬 현장 소통 & 응원")
        if st.button("📸 승리의 응원벽 참여 (사진/댓글)"):
            navigate_to('cheer')
        if st.button("📣 LG트윈스 응원가 배우기"):
            navigate_to('cheer_video')

        st.markdown("#### 🏟️ 실시간 경기 정보")
        st.markdown(f"""<div style="margin-bottom: 25px;"><a href="https://m.sports.naver.com/baseball/index" target="_blank" style="text-decoration: none;"><div style="background-color: #F2F2F7; color: #1C1C1E; padding: 18px; border-radius: 18px; text-align: center; font-weight: 700; border: 1px solid #E5E5EA;">⚾️ 네이버 스포츠 중계 센터 바로가기</div></a></div>""", unsafe_allow_html=True)

        st.markdown("#### 🏟️ 구장 안내 (잠실 102블록)")
        m = folium.Map(location=[37.5122, 127.0719], zoom_start=16, tiles="cartodbvoyager")
        for name, info in program_data.items():
            folium.Marker([info["lat"], info["lon"]], popup=folium.Popup(name, max_width=150), icon=folium.Icon(color=info["color"], icon=info["icon"], prefix='fa')).add_to(m)
        st_folium(m, width="100%", height=250, key="stadium_map")

        st.markdown('<h4 style="margin-top:25px; margin-bottom:12px;">🚩 관전 가이드</h4>', unsafe_allow_html=True)
        for name, info in program_data.items():
            img_raw = get_base64_img(info.get("bg_file", ""))
            bg_url = f"data:image/jpeg;base64,{img_raw}" if img_raw else ""
            st.markdown(f'<div class="program-card" style="background-image: url(\'{bg_url}\');"><div class="card-content"><div style="font-size:11px; font-weight:800; color:white; background:rgba(0,0,0,0.3); display:inline-block; padding:2px 8px; border-radius:4px; margin-bottom:4px;">{info.get("tag")}</div><div style="font-size: 20px; font-weight: 800; color:white;">{name}</div></div></div>', unsafe_allow_html=True)
            if st.button(f"{name} 상세보기", key=f"btn_{name}"):
                navigate_to('detail', name)

        st.markdown(f"""<div class="info-box" style="text-align:center; margin-top:35px; background-color: #F2F2F7; border: none;"><div style="font-weight:800; color:#3A3A3C; font-size:14px; margin-bottom:6px;">📞 운영 및 비상 연락처</div><div style="font-size:15px; color:#1C1C1E; line-height:1.6;">인재육성팀 <b>김선화 팀장</b><br><a href="tel:010-4488-5567" style="text-decoration:none; color:#007AFF; font-weight:700; font-size:16px;">010-4488-5567</a></div></div>""", unsafe_allow_html=True)

    # [2] CHEER FEED VIEW (바둑판 갤러리 및 이벤트 배너)
    elif st.session_state.view == 'cheer':
        st.markdown('<h2 style="font-weight:900; margin-bottom:5px;">📸 승리의 응원벽</h2>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✨ 나도 응원 남기기"): navigate_to('upload')
        with col2:
            if st.button("🎯 이벤트 참여하기"): navigate_to('event_upload')

        if db:
            # 1. 이벤트 데이터 가져오기 및 상단 배너 표시
            events = [doc.to_dict() | {"id": doc.id} for doc in db.collection(EVENT_COLLECTION).stream()]
            events.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
            
            if events:
                with st.expander(f"🎯 오늘의 주인공 예측 현황 ({len(events)}명 참여 중)", expanded=True):
                    st.markdown('<div style="margin-bottom:10px; font-size:14px; color:#666;">최근 참여자들의 예측을 확인해보세요!</div>', unsafe_allow_html=True)
                    # 최신 5개만 표시
                    for event in events[:5]:
                        st.markdown(f"""
                        <div class="event-item">
                            <span style="font-weight:700;">👤 {event['name']}</span>님의 예측 → 
                            홈런: <span style="color:#FF3B30; font-weight:700;">{event['hr_player']}</span> / 
                            안타: <span style="color:#007AFF; font-weight:700;">{event['hit_player']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        if is_admin:
                            if st.button("삭제", key=f"del_evt_{event['id']}", help="관리자용"):
                                db.collection(EVENT_COLLECTION).document(event['id']).delete()
                                st.rerun()

            # 2. 사진 응원 데이터 가져오기
            cheers = [doc.to_dict() | {"id": doc.id} for doc in db.collection(CHEER_COLLECTION).stream()]
            cheers.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
            cheers = [c for c in cheers if c.get("image")] # 이미지가 있는 것만 필터링

            # 3. 바둑판 갤러리 구현 (3열)
            st.markdown("---")
            st.markdown('<h4 style="font-weight:800; margin-bottom:15px;">📸 현장 사진 모아보기</h4>', unsafe_allow_html=True)
            
            if not cheers:
                st.info("아직 올라온 사진이 없습니다. 첫 번째 주인공이 되어보세요!")
            else:
                # 3개의 컬럼 생성
                cols = st.columns(3)
                for i, post in enumerate(cheers[:60]): # 최대 60개까지만 표시
                    with cols[i % 3]: # 컬럼에 순차적으로 분배
                        # 이미지를 클릭 가능한 버튼처럼 만듦 (실제로는 버튼 위에 이미지를 덮어씌우는 방식)
                        if st.button(label="image_btn", key=f"img_{post['id']}", help="클릭하여 크게 보기", use_container_width=True):
                            st.session_state.modal_post = post # 클릭한 게시물 정보 저장
                            st.rerun() # 리렌더링하여 모달 띄움

                        # 버튼 위에 실제 이미지를 CSS로 덮어씌움 (Hack)
                        st.markdown(f"""
                        <div class="gallery-item" style="pointer-events: none;">
                            <img src="data:image/jpeg;base64,{post['image']}" class="gallery-img">
                        </div>
                        <div style="margin-top:-100%; height:100%;"></div> 
                        """, unsafe_allow_html=True)
                        
                        # 닉네임 살짝 표시
                        st.caption(f"👤 {post['name']}")

        # 4. 모달 띄우기 (st.session_state.modal_post가 있을 때만)
        if st.session_state.modal_post:
            show_post_modal(st.session_state.modal_post)

        st.markdown('<div class="nav-btn-container secondary-btn">', unsafe_allow_html=True)
        if st.button("🏠 메인으로 돌아가기"): navigate_to('home')
        st.markdown('</div>', unsafe_allow_html=True)

    # [3] CHEER VIDEO VIEW
    elif st.session_state.view == 'cheer_video':
        st.markdown('<h2 style="font-weight:900; margin-bottom:5px;">📣 응원가 배우기</h2>', unsafe_allow_html=True)
        st.video("https://m.youtube.com/watch?v=BhwoJFjkAf8")
        st.markdown('<div class="nav-btn-container secondary-btn">', unsafe_allow_html=True)
        if st.button("🏠 메인으로 돌아가기"): navigate_to('home')
        st.markdown('</div>', unsafe_allow_html=True)

    # [4] UPLOAD VIEW (사진 응원)
    elif st.session_state.view == 'upload':
        st.markdown("""<div style="text-align: center; margin-bottom: 10px;"><svg width="60" height="60" viewBox="0 0 100 100"><circle cx="50" cy="50" r="45" fill="white" stroke="#E5E5EA" stroke-width="2"/><path d="M20 30 Q50 50 20 70" fill="none" stroke="#FF3B30" stroke-width="3"/><path d="M80 30 Q50 50 80 70" fill="none" stroke="#FF3B30" stroke-width="3"/><text x="50" y="55" font-size="12" font-weight="900" text-anchor="middle" fill="#FF3B30" font-family="Pretendard">LG TWINS</text></svg></div>""", unsafe_allow_html=True)
        st.markdown('<h2 style="font-weight:900; text-align:center; margin-bottom:5px;">✨ 응원 남기기</h2>', unsafe_allow_html=True)
        st.markdown(f"""<div class="example-box"><div style="font-weight:800; color:#FF3B30; font-size:15px; margin-bottom:8px;">🎁 참여 이벤트 안내</div><div style="font-size:14px; color:#3A3A3C; line-height:1.6;">현장 분위기를 잘 표현한 사진이나 소감을 남겨주세요!<br><b>(예시: CEO와 셀카, 응원 장면, LG 득점 순간 등)</b><br><br><span style="color:#FF3B30;">✨ 참여해주신 분들께는 추첨을 통해 소정의 상품을 드립니다!</span></div></div>""", unsafe_allow_html=True)
        with st.container():
            c_name = st.text_input("닉네임 또는 조 (예: 5조 홍길동)")
            c_text = st.text_area("현장 소감 및 응원 메시지")
            c_file = st.file_uploader("현장 사진 업로드", type=['jpg', 'jpeg', 'png'])
            if st.button("✅ 게시판에 등록하기"):
                if c_name and c_text and db:
                    with st.spinner("최적화 중..."):
                        img_b64 = compress_image(c_file) if c_file else ""
                        db.collection(CHEER_COLLECTION).add({"name": c_name, "text": c_text, "image": img_b64, "timestamp": datetime.now()})
                        navigate_to('cheer')
                else: st.warning("정보를 모두 입력해주세요.")
            st.markdown('<div class="nav-btn-container secondary-btn">', unsafe_allow_html=True)
            if st.button("❌ 취소"): navigate_to('cheer')
            st.markdown('</div>', unsafe_allow_html=True)

    # [5] EVENT UPLOAD VIEW (텍스트 전용 이벤트)
    elif st.session_state.view == 'event_upload':
        st.markdown("""<div style="text-align: center; margin-bottom: 10px;"><svg width="60" height="60" viewBox="0 0 100 100"><circle cx="50" cy="50" r="45" fill="white" stroke="#E5E5EA" stroke-width="2"/><path d="M20 30 Q50 50 20 70" fill="none" stroke="#FF3B30" stroke-width="3"/><path d="M80 30 Q50 50 80 70" fill="none" stroke="#FF3B30" stroke-width="3"/><text x="50" y="55" font-size="12" font-weight="900" text-anchor="middle" fill="#FF3B30" font-family="Pretendard">EVENT</text></svg></div>""", unsafe_allow_html=True)
        st.markdown('<h2 style="font-weight:900; text-align:center; margin-bottom:5px;">🎯 이벤트 참여하기</h2>', unsafe_allow_html=True)
        st.markdown(f"""<div class="example-box"><div style="font-weight:800; color:#FF3B30; font-size:15px; margin-bottom:8px;">⚾️ 오늘의 주인공을 맞춰라!</div><div style="font-size:14px; color:#3A3A3C; line-height:1.6;">오늘 첫 홈런과 첫 안타의 주인공은 누구일까요?<br>선수 이름을 정확히 입력해주세요!<br><br><span style="color:#FF3B30;">✨ 정답을 맞히신 분들께는 특별한 선물을 드립니다!</span></div></div>""", unsafe_allow_html=True)
        
        with st.container():
            e_name = st.text_input("닉네임 또는 조 (예: 1조 홍길동)", key="ev_name")
            e_hr = st.text_input("⚾️ 오늘의 첫 홈런 선수는?", placeholder="선수 이름 입력", key="ev_hr")
            e_hit = st.text_input("⚾️ 오늘의 첫 안타 선수는?", placeholder="선수 이름 입력", key="ev_hit")
            
            if st.button("🚀 예측 완료! 게시하기"):
                if e_name and e_hr and e_hit and db:
                    db.collection(EVENT_COLLECTION).add({
                        "name": e_name, "hr_player": e_hr, "hit_player": e_hit, "timestamp": datetime.now()
                    })
                    st.success("이벤트 참여가 완료되었습니다!")
                    navigate_to('cheer')
                else: st.warning("모든 정보를 입력해주세요.")
            
            st.markdown('<div class="nav-btn-container secondary-btn">', unsafe_allow_html=True)
            if st.button("❌ 취소"): navigate_to('cheer')
            st.markdown('</div>', unsafe_allow_html=True)

    # [6] DETAIL VIEW
    elif st.session_state.view == 'detail':
        name = st.session_state.target
        item = program_data.get(name, {})
        img_raw = get_base64_img(item.get("bg_file", ""))
        bg_url = f"data:image/jpeg;base64,{img_raw}" if img_raw else ""
        points_html = "".join([f'<div style="margin-bottom:12px; font-size:15px; color:#3A3A3C;">• {p}</div>' for p in item.get("points", [])])
        st.markdown(f"""<div style="background: url('{bg_url}'); background-size: cover; background-position: center; height: 180px; border-radius: 20px; margin: 0 0 15px 0; display: flex; align-items: flex-end; padding: 25px;"><div style="color: white; text-shadow: 0 2px 4px rgba(0,0,0,0.5);"><div style="font-size: 11px; font-weight: 700; opacity: 0.8;">{item.get('tag')}</div><div style="font-size: 26px; font-weight: 900;">{name}</div></div></div><div style="background-color: #F8F8FA; padding: 30px; border-radius: 30px; border: 1px solid #E5E5EA;"><h3 style="margin:0 0 15px 0; font-weight:800; color:#1C1C1E;">{item.get('detail_title')}</h3><p style="font-size: 16px; color: #48484A; line-height: 1.6;">{item.get('desc')}</p><hr style="border: 0; border-top: 1px solid #E5E5EA; margin: 25px 0;">{points_html}</div>""", unsafe_allow_html=True)
        st.markdown('<div class="nav-btn-container secondary-btn">', unsafe_allow_html=True)
        if st.button("🏠 메인으로 돌아가기"): navigate_to('home')
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<p style='text-align:center; color:#C7C7CC; font-size:12px; margin-top:40px; padding-bottom: 20px;'>© 2026 LG Innotek Talent Development Team</p>", unsafe_allow_html=True)

