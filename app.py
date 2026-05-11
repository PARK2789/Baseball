# -*- coding: utf-8 -*-
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
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

# 1. 페이지 설정 (가장 먼저 실행)
st.set_page_config(page_title="CEO Talk+ Victory", page_icon="⚾️", layout="centered")

# --- [수정: 화면 전환 시 최상단 고정 스크립트] ---
def force_scroll_top():
    """
    Streamlit은 화면 전환/재실행 시 브라우저 스크롤 위치를 유지하는 경우가 있어,
    전환 직후와 렌더링 완료 직후 모두 최상단 이동을 강제로 실행합니다.
    """
    scroll_seq = st.session_state.get("scroll_seq", 0)

    components.html(
        f"""
        <script>
        (function() {{
            const token = "{scroll_seq}";

            function scrollTopNow() {{
                const doc = window.parent.document;

                const selectors = [
                    'section[data-testid="stMain"]',
                    'div[data-testid="stAppViewContainer"]',
                    'div[data-testid="stAppViewBlockContainer"]',
                    'div[data-testid="stVerticalBlock"]',
                    '.main',
                    '.stApp'
                ];

                const targets = selectors
                    .map(selector => doc.querySelector(selector))
                    .filter(Boolean);

                targets.push(doc.scrollingElement, doc.documentElement, doc.body, window.parent);

                targets.forEach(el => {{
                    try {{
                        if (el === window.parent) {{
                            el.scrollTo(0, 0);
                        }} else {{
                            el.scrollTop = 0;
                            el.scrollLeft = 0;
                            if (typeof el.scrollTo === "function") {{
                                el.scrollTo({{ top: 0, left: 0, behavior: "instant" }});
                            }}
                        }}
                    }} catch(e) {{}}
                }});
            }}

            function runScrollBurst() {{
                scrollTopNow();
                requestAnimationFrame(scrollTopNow);
                setTimeout(scrollTopNow, 0);
                setTimeout(scrollTopNow, 80);
                setTimeout(scrollTopNow, 180);
                setTimeout(scrollTopNow, 350);
                setTimeout(scrollTopNow, 700);
                setTimeout(scrollTopNow, 1200);
            }}

            runScrollBurst();

            // 이미지/비디오/폰트 로딩 후 레이아웃이 밀리는 경우까지 보정
            window.parent.addEventListener("load", runScrollBurst, {{ once: true }});
        }})();
        </script>
        """,
        height=0,
    )

# --- [데이터 처리 및 상태 결정 (UI 렌더링 전)] ---

# 세션 초기화
if 'view' not in st.session_state: st.session_state.view = 'home'
if 'prev_view' not in st.session_state: st.session_state.prev_view = 'home'
if 'target' not in st.session_state: st.session_state.target = None
if 'modal_post' not in st.session_state: st.session_state.modal_post = None
if 'force_scroll' not in st.session_state: st.session_state.force_scroll = False
if 'scroll_seq' not in st.session_state: st.session_state.scroll_seq = 0

# URL 파라미터 감지 (갤러리 클릭 시)
query_params = st.query_params
clicked_id = query_params.get("post_id")

# [플래시 방지] 클릭 시 즉시 뷰 상태를 고정하여 홈 화면 노출을 막음
if clicked_id:
    st.session_state.view = 'cheer'

# 내비게이션 함수
def navigate_to(view, target=None):
    # 모든 화면 전환 시 다음 렌더링에서 최상단으로 이동
    st.session_state.view = view
    st.session_state.target = target
    st.session_state.modal_post = None
    st.session_state.force_scroll = True
    st.session_state.scroll_seq += 1
    st.rerun()

# DB 및 이미지 함수 (캐싱 적용)
@st.cache_resource
def get_db():
    try:
        creds_dict = json.loads(st.secrets["textkey"])
        creds = service_account.Credentials.from_service_account_info(creds_dict)
        return firestore.Client(credentials=creds)
    except: return None

@st.cache_data
def get_base64_img(file_path):
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def compress_image(uploaded_file):
    img = Image.open(uploaded_file)
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
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

# --- [UI 렌더링 로직 시작] ---

# 1. 화면 전환 시 스크롤 실행
#    - 렌더링 전 1차 실행
#    - 화면을 모두 그린 뒤 하단에서 2차 실행
need_scroll_top = st.session_state.force_scroll or st.session_state.prev_view != st.session_state.view
if need_scroll_top:
    force_scroll_top()

# 2. 전역 스타일 및 디자인
st.markdown(f"""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    .stApp {{ font-family: 'Pretendard', sans-serif; background-color: #FFFFFF; }}
    .block-container {{ padding-top: 4.5rem !important; padding-bottom: 5rem !important; max-width: 100% !important; }}
    
    .hero-section {{
        background: linear-gradient(rgba(0,0,0,0.1), rgba(0,0,0,0.4)), url('data:image/jpeg;base64,{get_base64_img("stadium.jpg")}');
        background-size: cover; background-position: center;
        padding: 130px 25px 40px 25px; border-radius: 0 0 35px 35px;
        color: white; margin: -6.5rem -1rem 1.5rem -1rem;
    }}
    .hero-title {{ font-weight: 900; font-size: 36px; line-height: 1.1; letter-spacing: -1.5px; }}
    .info-box {{ background-color: #F8F8FA; padding: 18px 22px; border-radius: 20px; border: 1px solid #E5E5EA; margin-bottom: 12px; }}
    
    .stButton>button {{ 
        width: 100%; border-radius: 16px; background-color: #3A3A3C;
        color: white; font-weight: 600; height: 3.6em; font-size: 15px; margin-bottom: 12px; border: none;
    }}
    .secondary-btn button {{ background-color: #E5E5EA !important; color: #1C1C1E !important; box-shadow: none !important; }}

    /* [해결] 버튼 간격(Gap) 60px 확보 */
    .nav-btn-container {{ margin-top: 60px !important; padding-top: 10px; }}

    .program-card {{
        position: relative; height: 180px; border-radius: 24px; margin-bottom: 10px; 
        overflow: hidden; background-size: cover; background-position: center; 
        display: flex; flex-direction: column; justify-content: flex-end; padding: 22px; border: 1px solid #E5E5EA;
    }}
    .example-box {{ background-color: #FFF9F9; border: 1px dashed #FF3B30; padding: 15px; border-radius: 15px; margin-bottom: 20px; }}
</style>
""", unsafe_allow_html=True)

# 3. 상세 보기 모달 (속도 최적화)
@st.dialog("📸 응원 상세 보기")
def show_post_modal(post):
    st.image(f"data:image/jpeg;base64,{post['image']}", use_container_width=True)
    st.markdown(f"### 👤 {post['name']}")
    st.write(post['text'])
    st.caption(f"작성 시간: {post.get('timestamp', datetime.now()).strftime('%H:%M')}")
    if st.session_state.get("is_admin", False):
        if st.button("🗑️ 관리자 삭제", key="final_del_btn"):
            db.collection(CHEER_COLLECTION).document(post['id']).delete()
            st.session_state.modal_post = None
            st.query_params.clear()
            st.rerun()

# 관리자 인증
with st.sidebar:
    admin_pw = st.text_input("Admin", type="password")
    st.session_state.is_admin = (admin_pw == "1234")

# --- [메인 앱 본체: 이 안에서만 화면을 그려 플래시 현상 제거] ---
main_view_container = st.container()

with main_view_container:
    # [1] HOME
    if st.session_state.view == 'home':
        st.markdown(f'<div class="hero-section"><div class="hero-title">CEO Talk⁺<br>Victory Edition</div><div style="font-size: 16px; opacity: 0.9; margin-top: 10px; font-weight:500;">함께 소통하고 함께 승리합니다!</div></div>', unsafe_allow_html=True)
        st.markdown("#### 🚌 이동 및 집결 안내")
        st.markdown(f"""<div class="info-box"><div style="font-weight:800; color:#FF3B30; font-size:15px; margin-bottom:6px;">📍 단체 버스 탑승 정보</div><div style="font-size:15px; color:#1C1C1E; line-height:1.6;">• <b>장소:</b> E1/E3 동 정문 앞 버스 탑승<br>• <b>집결:</b> 16:25까지 집결 완료<br>• <b>출발:</b> 16:30 정시 출발</div></div>""", unsafe_allow_html=True)
        st.markdown("#### 💬 현장 소통 & 응원")
        if st.button("📸 승리의 응원벽 참여"): navigate_to('cheer')
        if st.button("📣 LG트윈스 응원가 배우기"): navigate_to('cheer_video')
        st.markdown("#### 🏟️ 실시간 경기 정보")
        # [수정] 네이버 스포츠 실시간 응원 링크
        naver_url = "https://m.sports.naver.com/game/20260512SSLG02026/cheer"
        st.markdown(f"""<div style="margin-bottom: 25px;"><a href="{naver_url}" target="_blank" style="text-decoration: none;"><div style="background-color: #03C75A; color: white; padding: 18px; border-radius: 18px; text-align: center; font-weight: 700;">⚾️ 네이버 스포츠 실시간 응원톡</div></a></div>""", unsafe_allow_html=True)
        
        st.markdown('#### 🚩 관전 가이드')
        for name, info in program_data.items():
            bg_b64 = get_base64_img(info.get("bg_file", ""))
            st.markdown(f'<div class="program-card" style="background-image: url(\'data:image/jpeg;base64,{bg_b64}\');"><div style="position:relative; z-index:2; text-shadow: 0px 2px 4px rgba(0,0,0,0.5);"><div style="font-size:11px; font-weight:800; color:white; background:rgba(0,0,0,0.4); display:inline-block; padding:2px 8px; border-radius:4px; margin-bottom:4px;">{info.get("tag")}</div><div style="font-size: 20px; font-weight: 800; color:white;">{name}</div></div></div>', unsafe_allow_html=True)
            if st.button(f"{name} 상세보기", key=f"btn_{name}"): navigate_to('detail', name)
        st.markdown(f"""<div class="info-box" style="text-align:center; margin-top:35px; background-color: #F2F2F7; border: none;"><div style="font-weight:800; color:#3A3A3C; font-size:14px; margin-bottom:6px;">📞 운영 및 비상 연락처</div><div style="font-size:15px; color:#1C1C1E; line-height:1.6;">인재육성팀 <b>김선화 팀장</b><br><a href="tel:010-4488-5567" style="text-decoration:none; color:#007AFF; font-weight:700; font-size:16px;">010-4488-5567</a></div></div>""", unsafe_allow_html=True)

    # [2] CHEER FEED (바둑판 갤러리 및 예측 현황)
    elif st.session_state.view == 'cheer':
        st.markdown('<h2 style="font-weight:900; margin-bottom:5px;">📸 승리의 응원벽</h2>', unsafe_allow_html=True)
        cb1, cb2 = st.columns(2)
        with cb1: 
            if st.button("✨ 나도 응원 남기기"): navigate_to('upload')
        with cb2: 
            if st.button("🎯 이벤트 참여하기"): navigate_to('event_upload')

        if db:
            # 예측 현황 복구
            ev_docs = db.collection(EVENT_COLLECTION).stream()
            events = sorted([doc.to_dict() | {"id": doc.id} for doc in ev_docs], key=lambda x: x.get('timestamp', datetime.min), reverse=True)
            if events:
                with st.expander(f"🎯 오늘의 주인공 예측 현황 ({len(events)}명 참여)", expanded=True):
                    for ev in events[:5]:
                        st.markdown(f"• **{ev['name']}**: {ev['hr_player']}(홈런) / {ev['hit_player']}(안타)")

            # 갤러리 데이터 로드
            st.markdown("---")
            cheer_docs = db.collection(CHEER_COLLECTION).stream()
            cheers = sorted([doc.to_dict() | {"id": doc.id} for doc in cheer_docs], key=lambda x: x.get('timestamp', datetime.min), reverse=True)
            cheers = [c for c in cheers if c.get("image")]

            # [해결] 클릭 시 패스트 트랙 팝업
            if clicked_id:
                target_p = next((c for c in cheers if c["id"] == clicked_id), None)
                if target_p:
                    show_post_modal(target_p)
                st.query_params.clear()

            if not cheers:
                st.info("아직 사진이 없습니다.")
            else:
                gallery_html = "".join([f'<a class="gallery-item" href="?post_id={p["id"]}" target="_top"><img src="data:image/jpeg;base64,{p["image"]}"><div class="name-tag">{p.get("name","")}</div></a>' for p in cheers[:60]])
                rows = (len(cheers[:60]) + 2) // 3
                components.html(
                    f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>body {{ margin:0; padding:0; background:transparent; }} .grid {{ display:grid; grid-template-columns:repeat(3, 1fr); gap:8px; padding:5px; }} .gallery-item {{ display:block; position:relative; aspect-ratio:1/1; border-radius:10px; overflow:hidden; background:#F2F2F7; }} .gallery-item img {{ width:100%; height:100%; object-fit:cover; }} .name-tag {{ position:absolute; bottom:0; width:100%; background:rgba(0,0,0,0.4); color:white; font-size:9px; text-align:center; padding:2px 0; overflow:hidden; }}</style></head><body><div class="grid">{gallery_html}</div></body></html>""",
                    height=rows * 135 + 20, scrolling=False
                )

        st.markdown('<div class="nav-btn-container secondary-btn">', unsafe_allow_html=True)
        if st.button("🏠 메인으로 돌아가기"): navigate_to('home')
        st.markdown('</div>', unsafe_allow_html=True)

    # [3] CHEER VIDEO / [4] UPLOAD / [5] EVENT / [6] DETAIL
    elif st.session_state.view == 'cheer_video':
        st.markdown('<h2 style="font-weight:900;">📣 응원가 배우기</h2>', unsafe_allow_html=True)
        st.video("https://m.youtube.com/watch?v=BhwoJFjkAf8")
        st.markdown('<div class="nav-btn-container secondary-btn">', unsafe_allow_html=True)
        if st.button("🏠 메인으로 돌아가기"): navigate_to('home')
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.view == 'upload':
        st.markdown('<h2 style="font-weight:900; text-align:center;">✨ 응원 남기기</h2>', unsafe_allow_html=True)
        st.markdown(f"""<div class="example-box"><div style="font-weight:800; color:#FF3B30; font-size:15px; margin-bottom:8px;">🎁 참여 이벤트 안내</div><div style="font-size:14px; color:#3A3A3C; line-height:1.6;">현장 분위기를 잘 표현한 사진이나 소감을 남겨주세요!<br><b>(예시: CEO와 셀카, 응원 장면, 인증샷 등)</b></div></div>""", unsafe_allow_html=True)
        c_name = st.text_input("닉네임 또는 조")
        c_text = st.text_area("현장 소감")
        c_file = st.file_uploader("사진 업로드", type=['jpg', 'jpeg', 'png'])
        if st.button("✅ 게시하기"):
            if c_name and c_text and db:
                img_b64 = compress_image(c_file) if c_file else ""
                db.collection(CHEER_COLLECTION).add({"name": c_name, "text": c_text, "image": img_b64, "timestamp": datetime.now()})
                navigate_to('cheer')
        if st.button("❌ 취소"): navigate_to('cheer')

    elif st.session_state.view == 'event_upload':
        st.markdown('<h2 style="font-weight:900; text-align:center;">🎯 이벤트 참여</h2>', unsafe_allow_html=True)
        e_name = st.text_input("닉네임 또는 조")
        e_hr = st.text_input("⚾️ 첫 홈런 선수?")
        e_hit = st.text_input("⚾️ 첫 안타 선수?")
        if st.button("🚀 예측 제출"):
            if e_name and e_hr and e_hit and db:
                db.collection(EVENT_COLLECTION).add({"name": e_name, "hr_player": e_hr, "hit_player": e_hit, "timestamp": datetime.now()})
                navigate_to('cheer')
        if st.button("❌ 취소"): navigate_to('cheer')

    elif st.session_state.view == 'detail':
        name = st.session_state.target
        item = program_data.get(name, {})
        img_raw = get_base64_img(item.get("bg_file", ""))
        points_html = "".join([f'<div style="margin-bottom:12px; font-size:15px; color:#3A3A3C;">• {p}</div>' for p in item.get("points", [])])
        # [복구] 상단 이미지 헤더
        st.markdown(f"""
        <div style="background: linear-gradient(rgba(0,0,0,0.1), rgba(0,0,0,0.4)), url('data:image/jpeg;base64,{img_raw}'); 
                    background-size: cover; background-position: center; height: 180px; 
                    border-radius: 20px; margin: 0 0 15px 0; display: flex; align-items: flex-end; padding: 25px;">
            <div style="color: white; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">
                <div style="font-size: 11px; font-weight: 700; opacity: 0.8;">{item.get('tag')}</div>
                <div style="font-size: 26px; font-weight: 900;">{name}</div>
            </div>
        </div>
        <div style="background-color: #F8F8FA; padding: 30px; border-radius: 30px; border: 1px solid #E5E5EA;">
            <h3 style="margin:0 0 15px 0; font-weight:800; color:#1C1C1E;">{item.get('detail_title')}</h3>
            <p style="font-size: 16px; color: #48484A; line-height: 1.6;">{item.get('desc')}</p>
            <hr style="border: 0; border-top: 1px solid #E5E5EA; margin: 25px 0;">
            {points_html}
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="nav-btn-container secondary-btn">', unsafe_allow_html=True)
        if st.button("🏠 메인으로 돌아가기"): navigate_to('home')
        st.markdown('</div>', unsafe_allow_html=True)

# 화면 렌더링 후 2차 실행: 이미지/상세화면 로딩 이후 스크롤 위치 재보정
if need_scroll_top:
    force_scroll_top()
    st.session_state.force_scroll = False
    st.session_state.prev_view = st.session_state.view

st.markdown("<p style='text-align:center; color:#C7C7CC; font-size:12px; margin-top:40px; padding-bottom: 20px;'>© 2026 LG Innotek Talent Development Team</p>", unsafe_allow_html=True)
