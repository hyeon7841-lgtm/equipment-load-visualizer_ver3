import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import io

st.set_page_config(layout="wide", page_title="Equipment Load Visualizer")
st.title("장비 하중 배치 툴 (관리 + 실시간 미리보기)")

# 세션 상태 초기화
if "items" not in st.session_state:
    st.session_state["items"] = []
if "placed_items" not in st.session_state:
    st.session_state["placed_items"] = []

# Sidebar: 캔버스 설정
st.sidebar.subheader("캔버스 설정")
canvas_w = st.sidebar.number_input("캔버스 가로(mm)", min_value=200, max_value=5000, value=930)
canvas_h = st.sidebar.number_input("캔버스 세로(mm)", min_value=200, max_value=5000, value=615)
padding = 10  # 장비 간 간격

# Sidebar: 장비 추가
with st.sidebar.form("add_equipment"):
    label = st.text_input("장비 이름", f"장비{len(st.session_state['items'])+1}")
    w = st.number_input("가로(mm)", min_value=10, max_value=2500, value=80)
    h = st.number_input("세로(mm)", min_value=10, max_value=2500, value=60)
    weight = st.number_input("무게(kg)", min_value=1, max_value=10000, value=100)
    submitted = st.form_submit_button("장비 추가")
    if submitted:
        st.session_state['items'].append({
            "label": label, "w": w, "h": h, "weight": weight
        })

# 장비 관리
st.sidebar.subheader("장비 목록 관리")
to_remove = None
for i, it in enumerate(st.session_state["items"]):
    col1, col2 = st.sidebar.columns([3,1])
    col1.write(f"{it['label']} ({it['w']}x{it['h']} mm, {it['weight']} kg)")
    if col2.button("삭제", key=f"del_{i}"):
        to_remove = i
if to_remove is not None:
    st.session_state["items"].pop(to_remove)

# 선택 장비
st.sidebar.subheader("배치할 장비 선택")
selected_index = st.sidebar.radio("장비 선택", options=range(len(st.session_state["items"])),
                                  format_func=lambda x: st.session_state["items"][x]["label"] if st.session_state["items"] else "없음")
selected_item = st.session_state["items"][selected_index] if st.session_state["items"] else None

# 배치 캔버스
st.subheader("장비 배치 미리보기")
fig, ax = plt.subplots(figsize=(canvas_w/100, canvas_h/100))
ax.set_xlim(0, canvas_w)
ax.set_ylim(0, canvas_h)
ax.set_aspect('equal')
ax.invert_yaxis()
ax.set_title("장비 배치 캔버스")

# 기존 배치 장비 표시
for it in st.session_state["placed_items"]:
    rect = plt.Rectangle((it['x'], it['y']), it['w'], it['h'],
                         facecolor='skyblue', edgecolor='red', linewidth=2, alpha=0.7)
    ax.add_patch(rect)
    ax.text(it['x'] + it['w']/2, it['y'] + it['h']/2, it['label'],
            ha='center', va='center', fontsize=8, color='black')

st.pyplot(fig)

# 간단한 배치 시뮬레이션
st.subheader("장비 배치 시뮬레이션")
col1, col2 = st.columns([2,1])
if selected_item:
    x = col1.number_input("배치 X 좌표", min_value=0, max_value=canvas_w, value=0)
    y = col1.number_input("배치 Y 좌표", min_value=0, max_value=canvas_h, value=0)
    if col2.button("배치"):
        st.session_state["placed_items"].append({
            "label": selected_item["label"],
            "w": selected_item["w"],
            "h": selected_item["h"],
            "weight": selected_item["weight"],
            "x": x,
            "y": y
        })
        st.experimental_rerun()  # 배치 후 화면 업데이트

# 하중분포 생성
if st.button("하중분포 생성"):
    grid_array = np.zeros((canvas_h, canvas_w))
    for it in st.session_state["placed_items"]:
        x = int(it['x'])
        y = int(it['y'])
        w = int(it['w'])
        h = int(it['h'])
        weight = float(it['weight'])
        x2 = min(canvas_w, x + w)
        y2 = min(canvas_h, y + h)
        grid_array[y:y2, x:x2] += weight

    fig2, ax2 = plt.subplots(figsize=(canvas_w/100, canvas_h/100))
    im = ax2.imshow(grid_array, cmap="jet", origin="lower")
    ax2.set_title("하중 분포 Heatmap")
    plt.colorbar(im, ax=ax2)
    st.pyplot(fig2)

    buf = io.BytesIO()
    fig2.savefig(buf, format="png", dpi=200)
    st.download_button("PNG 다운로드", data=buf.getvalue(),
                       file_name="loadmap.png", mime="image/png")
