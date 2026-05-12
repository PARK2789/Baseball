# -*- coding: utf-8 -*-
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import base64
import os
import json
import re
import unicodedata
from urllib.parse import quote
from datetime import datetime
from google.cloud import firestore
from google.oauth2 import service_account
from PIL import Image, ImageOps
import io

# 1. 페이지 설정 (최상단)
st.set_page_config(page_title="CEO Talk+ Victory", page_icon="⚾️", layout="centered")

# --- [성식님 제안 & GPT 수정: 최상단 고정 스크립트 완벽 유지] ---
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

# --- [데이터 처리 및 세션 관리 (UI 렌더링 전 완료)] ---

# 세션 초기화 (상태 보존용)
if 'view' not in st.session_state: st.session_state.view = 'home'
if 'prev_view' not in st.session_state: st.session_state.prev_view = 'home'
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'edit_mode' not in st.session_state: st.session_state.edit_mode = False
if 'scroll_seq' not in st.session_state: st.session_state.scroll_seq = 0
if 'force_scroll' not in st.session_state: st.session_state.force_scroll = False

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
        try:
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except: return ""
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

# programs.json 로드
program_data = {}
if os.path.exists("programs.json"):
    try:
        with open("programs.json", "r", encoding="utf-8") as f:
            program_data = json.load(f)
    except: pass

# 관리자 로그인 상태 유지
with st.sidebar:
    admin_pw = st.text_input("Admin Password", type="password")
    if admin_pw == "1234":
        st.session_state.is_admin = True
    elif admin_pw == "":
        pass 
    else:
        st.session_state.is_admin = False

def navigate_to(view, target=None):
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.session_state.view = view
    st.session_state.target = target
    st.session_state.force_scroll = True
    st.session_state.scroll_seq += 1
    st.rerun()

# 상세보기 다이얼로그 (팝업 확대)
@st.dialog("📸 응원 상세 보기")
def show_post_modal(post):
    st.image(f"data:image/jpeg;base64,{post['image']}", use_container_width=True)
    st.markdown(f"### 👤 {post['name']}")
    st.write(post['text'])
    st.caption(f"작성 시간: {post.get('timestamp', datetime.now()).strftime('%H:%M')}")
    if st.session_state.is_admin:
        st.markdown("---")
        if st.button("🗑️ 관리자 즉시 삭제", key=f"dlg_del_{post['id']}"):
            db.collection(CHEER_COLLECTION).document(post['id']).delete()
            st.rerun()


def build_gallery_component_html(cheers):
    """
    갤러리 화면 전용 렌더링 (원본 보존)
    """
    safe_items = []
    for p in cheers:
        img = str(p.get("image", "")).strip()
        if not img: continue
        safe_items.append({
            "id": str(p.get("id", "")),
            "name": str(p.get("name", "사진")),
            "text": str(p.get("text", "")),
            "time": p.get("timestamp", datetime.now()).strftime("%H:%M") if hasattr(p.get("timestamp", None), "strftime") else "",
            "image": img,
        })

    items_json = json.dumps(safe_items, ensure_ascii=False)
    rows = max(1, (len(safe_items) + 2) // 3)
    component_height = min(max(rows * 150 + 40, 620), 1200)

    html_doc = f"""
<!doctype html>
<html lang=\"ko\">
<head>
<meta charset=\"utf-8\" /><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
<style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; width: 100%; min-height: 100%; background: transparent; font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; }}
    body.modal-open {{ overflow: hidden; background: transparent; }}
    .gallery-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; width: 100%; padding: 2px 0 8px 0; }}
    .gallery-item {{ display: block; width: 100%; aspect-ratio: 1 / 1; border: 0; padding: 0; margin: 0; background: #F2F2F7; border-radius: 12px; overflow: hidden; cursor: pointer; box-shadow: 0 1px 4px rgba(0,0,0,0.08); -webkit-tap-highlight-color: transparent; }}
    .gallery-item img {{ width: 100%; height: 100%; display: block; object-fit: cover; }}
    .modal {{ display: none; position: fixed; inset: 0; z-index: 999999; background: rgba(0,0,0,0.5); padding: 14px; align-items: flex-start; justify-content: center; pointer-events: none; }}
    .modal.open {{ display: flex; }}
    .modal-card {{ position: relative; width: min(100%, 520px); max-height: calc(100vh - 28px); background: #FFFFFF; border-radius: 20px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.18); display: flex; flex-direction: column; pointer-events: auto; }}
    .modal-img-area {{ width: 100%; background: #FFFFFF; padding: 14px 14px 0 14px; display: flex; align-items: center; justify-content: center; flex: 0 1 auto; min-height: 0; }}
    .modal-img {{ display: block; width: auto; height: auto; max-width: 100%; max-height: 52vh; object-fit: contain; border-radius: 12px; background: #FFFFFF; }}
    .modal-body {{ padding: 16px 18px 18px 18px; color: #1C1C1E; background: #FFFFFF; overflow-y: auto; -webkit-overflow-scrolling: touch; }}
    .modal-name {{ font-size: 20px; font-weight: 900; margin-bottom: 8px; line-height: 1.25; }}
    .modal-text {{ font-size: 16px; line-height: 1.45; white-space: pre-wrap; word-break: keep-all; }}
    .modal-time {{ margin-top: 12px; font-size: 13px; color: #8E8E93; }}
    .close-btn {{ position: absolute; top: 10px; right: 10px; z-index: 3; width: 38px; height: 38px; border: 0; border-radius: 999px; background: rgba(255,255,255,0.96); color: #111; font-size: 28px; line-height: 36px; cursor: pointer; box-shadow: 0 2px 10px rgba(0,0,0,0.22); }}
</style>
</head>
<body>
    <div id=\"gallery\" class=\"gallery-grid\"></div>
    <div id=\"modal\" class=\"modal\" aria-hidden=\"true\">
        <div class=\"modal-card\" role=\"dialog\" aria-modal=\"true\">
            <button class=\"close-btn\" id=\"closeBtn\" type=\"button\">×</button>
            <div class=\"modal-img-area\"><img id=\"modalImg\" class=\"modal-img\" src=\"\" /></div>
            <div class=\"modal-body\"><div id=\"modalName\" class=\"modal-name\"></div><div id=\"modalText\" class=\"modal-text\"></div><div id=\"modalTime\" class=\"modal-time\"></div></div>
        </div>
    </div>
<script>
(function() {{
    const items = {items_json};
    const gallery = document.getElementById('gallery');
    const modal = document.getElementById('modal');
    const modalImg = document.getElementById('modalImg');
    const modalName = document.getElementById('modalName');
    const modalText = document.getElementById('modalText');
    const modalTime = document.getElementById('modalTime');
    const closeBtn = document.getElementById('closeBtn');

    function openModal(item) {{
        modalImg.src = 'data:image/jpeg;base64,' + item.image;
        modalName.innerHTML = '👤 ' + item.name;
        modalText.innerText = item.text;
        modalTime.innerText = item.time ? ('작성 시간: ' + item.time) : '';
        document.body.classList.add('modal-open');
        modal.classList.add('open');
    }}
    function closeModal() {{ modal.classList.remove('open'); document.body.classList.remove('modal-open'); }}
    items.forEach(item => {{
        const btn = document.createElement('button');
        btn.className = 'gallery-item';
        btn.appendChild(document.createElement('img')).src = 'data:image/jpeg;base64,' + item.image;
        btn.onclick = () => openModal(item);
        gallery.appendChild(btn);
    }});
    closeBtn.onclick = closeModal;
    modal.onclick = (e) => {{ if(e.target === modal) closeModal(); }};
}})();
</script>
</body>
</html>
"""
    return html_doc, component_height

# --- [UI 렌더링 영역 시작] ---

if st.session_state.force_scroll or st.session_state.prev_view != st.session_state.view:
    force_scroll_top()
    st.session_state.force_scroll = False
    st.session_state.prev_view = st.session_state.view

# [해결] 다크모드 및 갤럭시 호환 통합 CSS
hero_bg = get_base64_img("stadium.jpg") or get_base64_img("cheer.jpg")
st.markdown(f"""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    /* 배경 및 글자색 강제 고정 (시스템 설정 무시) */
    .stApp {{ background-color: #FFFFFF !important; color: #1C1C1E !important; font-family: 'Pretendard', sans-serif; }}
    
    /* 모든 텍스트 및 스트림릿 요소 색상 명시적 지정 */
    h1, h2, h3, h4, p, span, div, li, label, .stMarkdown, [data-testid="stExpander"] {{ color: #1C1C1E !important; }}
    
    /* 갤럭시 겹침 방지: 음수 마진 제거 및 여백 정밀 조정 */
    .block-container {{ padding-top: 4.5rem !important; padding-bottom: 5rem !important; max-width: 100% !important; }}
    
    .hero-section {{
        background: linear-gradient(rgba(0,0,0,0.1), rgba(0,0,0,0.4)), url('data:image/jpeg;base64,{hero_bg}');
        background-size: cover; background-position: center;
        padding: 110px 25px 40px 25px; border-radius: 0 0 35px 35px;
        margin: -4.5rem -1rem 1.5rem -1rem; position: relative; z-index: 10;
    }}
    .hero-section * {{ color: #FFFFFF !important; }}
    .hero-title {{ font-weight: 900; font-size: 36px; line-height: 1.1; letter-spacing: -1.5px; }}

    .info-box {{ background-color: #F8F8FA; padding: 18px 22px; border-radius: 20px; border: 1px solid #E5E5EA; margin-bottom: 12px; }}
    .info-box * {{ color: #1C1C1E !important; }}
    
    .stButton>button {{ width: 100%; border-radius: 16px; background-color: #3A3A3C; color: white !important; font-weight: 600; height: 3.6em; border: none; }}
    .secondary-btn button {{ background-color: #E5E5EA !important; color: #1C1C1E !important; }}
    
    /* 모바일 가로 배열 유지 */
    div[data-testid="column"] {{ width: 32% !important; flex: 1 1 32% !important; min-width: 32% !important; }}
    div[data-testid="stHorizontalBlock"] {{ display: flex !important; flex-direction: row !important; flex-wrap: wrap !important; gap: 5px !important; }}
    
    .program-card {{ position: relative; height: 180px; border-radius: 24px; margin-bottom: 10px; overflow: hidden; background-size: cover; background-position: center; display: flex; flex-direction: column; justify-content: flex-end; padding: 22px; border: 1px solid #E5E5EA; }}
    .program-card * {{ color: white !important; }}
    .card-content {{ position: relative; z-index: 2; text-shadow: 0px 2px 4px rgba(0,0,0,0.5); }}
</style>
""", unsafe_allow_html=True)

main_app_canvas = st.container()

with main_app_canvas:
    # [1] HOME VIEW
    if st.session_state.view == 'home':
        st.markdown(f'<div class="hero-section"><div class="hero-title">CEO Talk⁺<br>Victory Edition</div><div style="font-size: 16px; opacity: 0.9; margin-top: 10px; font-weight:500;">함께 소통하고 함께 승리합니다!</div></div>', unsafe_allow_html=True)
        st.markdown("#### 🚌 이동 및 집결 안내")
        st.markdown(f"""<div class="info-box"><div style="font-weight:800; color:#FF3B30 !important; font-size:15px; margin-bottom:6px;">📍 단체 버스 탑승 정보</div><div style="font-size:15px; line-height:1.6;">• <b>장소:</b> E1/E3 동 정문 앞 버스 탑승<br>• <b>집결:</b> 16:25까지 집결 완료<br>• <b>출발:</b> 16:30 정시 출발</div></div>""", unsafe_allow_html=True)
        
        st.markdown("#### 💬 현장 소통 & 응원")
        if st.button("📸 함께 응원하기"): navigate_to('cheer')
        if st.button("📣 LG트윈스 응원가 배우기"): navigate_to('cheer_video')
        st.markdown("#### 🏟️ 실시간 경기 정보")
        naver_url = "https://m.sports.naver.com/game/20260512SSLG02026/cheer"
        st.markdown(f"""<div style="margin-bottom: 25px;"><a href="{naver_url}" target="_blank" style="text-decoration: none;"><div style="background-color: #03C75A; color: white !important; padding: 18px; border-radius: 18px; text-align: center; font-weight: 700;">⚾️ 네이버 스포츠 실시간 응원톡</div></a></div>""", unsafe_allow_html=True)
        for name, info in program_data.items():
            card_bg = get_base64_img(info.get("bg_file", ""))
            st.markdown(f"""<div class="program-card" style="background-image: url('data:image/jpeg;base64,{card_bg}');"><div class="card-content"><div style="font-size:11px; font-weight:800; background:rgba(0,0,0,0.4); display:inline-block; padding:2px 8px; border-radius:4px; margin-bottom:4px;">{info.get("tag")}</div><div style="font-size: 20px; font-weight: 800;">{name}</div></div></div>""", unsafe_allow_html=True)
            if st.button(f"{name} 상세보기", key=f"btn_{name}"): navigate_to('detail', name)
        st.markdown(f"""<div class="info-box" style="text-align:center; margin-top:35px; background-color: #F2F2F7; border: none;"><div style="font-weight:800; font-size:14px; margin-bottom:6px;">📞 운영 및 비상 연락처</div><div style="font-size:15px; line-height:1.6;">인재육성팀 <b>김선화 팀장</b><br><a href="tel:010-4488-5567" style="text-decoration:none; color:#007AFF !important; font-weight:700; font-size:16px;">010-4488-5567</a></div></div>""", unsafe_allow_html=True)

    # [2] CHEER FEED VIEW
    elif st.session_state.view == 'cheer':
        st.markdown('<h2 style="font-weight:900; margin-bottom:5px;">📸 함께 응원하기</h2>', unsafe_allow_html=True)
        if st.session_state.is_admin:
            st.session_state.edit_mode = st.toggle("🛠 관리자 삭제 모드 활성화", value=st.session_state.edit_mode)
        c1, c2 = st.columns(2)
        with c1: 
            if st.button("✨ 현장 사진 올리기"): navigate_to('upload')
        with c2: 
            if st.button("🎯 경기 예상하기"): navigate_to('event_upload')
        st.markdown('<div class="secondary-btn" style="margin-top:8px; margin-bottom:18px;">', unsafe_allow_html=True)
        if st.button("🏠 메인으로 돌아가기"): navigate_to('home')
        st.markdown('</div>', unsafe_allow_html=True)

        if db:
            ev_docs = db.collection(EVENT_COLLECTION).stream()
            events = sorted([doc.to_dict() | {"id": doc.id} for doc in ev_docs], key=lambda x: x.get('timestamp', datetime.min), reverse=True)
            if events:
                with st.expander(f"🎯 오늘의 주인공 예측 현황", expanded=True):
                    for ev in events[:5]:
                        ec, dc = st.columns([4, 1])
                        ec.markdown(f"• **{ev['name']}**: {ev['hr_player']}/{ev['hit_player']}")
                        if st.session_state.is_admin:
                            if dc.button("삭제", key=f"del_ev_{ev['id']}"):
                                db.collection(EVENT_COLLECTION).document(ev['id']).delete()
                                st.rerun()
            st.markdown("---")
            cheer_docs = db.collection(CHEER_COLLECTION).stream()
            cheers = sorted([doc.to_dict() | {"id": doc.id} for doc in cheer_docs], key=lambda x: x.get('timestamp', datetime.min), reverse=True)
            cheers = [c for c in cheers if c.get("image")]
            if cheers:
                gallery_html, gallery_height = build_gallery_component_html(cheers)
                components.html(gallery_html, height=gallery_height, scrolling=False)
                if st.session_state.is_admin and st.session_state.edit_mode:
                    for i in range(0, len(cheers), 3):
                        del_cols = st.columns(3, gap="small")
                        for j in range(3):
                            if i + j < len(cheers):
                                p = cheers[i + j]
                                with del_cols[j]:
                                    if st.button("삭제", key=f"th_del_{p['id']}"):
                                        db.collection(CHEER_COLLECTION).document(p['id']).delete()
                                        st.rerun()

    # [3] CHEER VIDEO / [4] UPLOAD / [5] EVENT
    elif st.session_state.view == 'cheer_video':
        st.markdown('<h2 style="font-weight:900;">📣 응원가 배우기</h2>', unsafe_allow_html=True)
        st.video("https://m.youtube.com/watch?v=BhwoJFjkAf8")
        st.markdown('<div class="nav-btn-container secondary-btn">', unsafe_allow_html=True)
        if st.button("🏠 메인으로 돌아가기"): navigate_to('home')
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.view == 'upload':
        st.markdown('<h2 style="font-weight:900; text-align:center;">✨ 응원 남기기</h2>', unsafe_allow_html=True)
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
        st.markdown('<h2 style="font-weight:900; text-align:center;">🎯 경기 예상하기</h2>', unsafe_allow_html=True)
        e_name = st.text_input("닉네임 또는 조")
        e_hr = st.text_input("⚾️ 첫 홈런 선수?")
        e_hit = st.text_input("⚾️ 첫 안타 선수?")
        if st.button("🚀 예측 제출"):
            if e_name and e_hr and e_hit and db:
                db.collection(EVENT_COLLECTION).add({"name": e_name, "hr_player": e_hr, "hit_player": e_hit, "timestamp": datetime.now()})
                navigate_to('cheer')
        if st.button("❌ 취소"): navigate_to('cheer')

    # [6] DETAIL VIEW (추가 이미지 삽입)
    elif st.session_state.view == 'detail':
        name = st.session_state.target
        item = program_data.get(name, {})
        detail_bg = get_base64_img(item.get("bg_file", ""))
        points_html = "".join([f'<div style="margin-bottom:12px; font-size:15px; color:#1C1C1E;">• {p}</div>' for p in item.get("points", [])])
        
        st.markdown(f"""
        <div style="background: linear-gradient(rgba(0,0,0,0.1), rgba(0,0,0,0.4)), url('data:image/jpeg;base64,{detail_bg}'); 
                    background-size: cover; background-position: center; height: 180px; 
                    border-radius: 20px; margin: 0 0 15px 0; display: flex; align-items: flex-end; padding: 25px;">
            <div style="color: white; text-shadow: 0 2px 4px rgba(0,0,0,0.5);">
                <div style="font-size: 11px; font-weight: 700; opacity: 0.8; color: white !important;">{item.get('tag')}</div>
                <div style="font-size: 26px; font-weight: 900; color: white !important;">{name}</div>
            </div>
        </div>
        <div style="background-color: #F8F8FA; padding: 30px; border-radius: 30px; border: 1px solid #E5E5EA;">
            <h3 style="margin:0 0 15px 0; font-weight:800; color:#1C1C1E;">{item.get('detail_title')}</h3>
            <p style="font-size: 16px; color: #1C1C1E; line-height: 1.6;">{item.get('desc')}</p>
        """, unsafe_allow_html=True)

        # [해결] extra_img가 있으면 설명 아래에 이미지 삽입
        extra_img_file = item.get("extra_img")
        if extra_img_file:
            ex_img_b64 = get_base64_img(extra_img_file)
            if ex_img_b64:
                st.markdown(f'<img src="data:image/jpeg;base64,{ex_img_b64}" style="width:100%; border-radius:15px; margin: 10px 0 20px 0;">', unsafe_allow_html=True)

        st.markdown(f"""
            <hr style="border: 0; border-top: 1px solid #E5E5EA; margin: 25px 0;">
            {points_html}
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="nav-btn-container secondary-btn">', unsafe_allow_html=True)
        if st.button("🏠 메인으로 돌아가기"): navigate_to('home')
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<p style='text-align:center; color:#C7C7CC !important; font-size:12px; margin-top:40px; padding-bottom: 20px;'>© 2026 LG Innotek Talent Development Team</p>", unsafe_allow_html=True)

