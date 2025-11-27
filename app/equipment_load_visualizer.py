# app/equipment_load_visualizer.py
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
import pandas as pd
import io

st.set_page_config(page_title="Equipment Load Visualizer (No-Drag)", layout="wide")

st.title("장비 하중 분포 시각화 (드래그 없이)")

# 작업 면적 (기본)
AREA_W = st.sidebar.number_input("면적 가로 (mm)", value=3100, step=100)
AREA_H = st.sidebar.number_input("면적 세로 (mm)", value=2050, step=50)

# 그리드 & 스무스 설정
st.sidebar.header("시각화 설정")
grid_x = st.sidebar.slider("Grid resolution (x cells)", 50, 600, 300)
grid_y = st.sidebar.slider("Grid resolution (y cells)", 50, 600, 200)
smooth_sigma = st.sidebar.slider("Smoothness (Gaussian sigma)", 0.0, 20.0, 4.0)

# 장비 상태 저장
if "equipments" not in st.session_state:
    st.session_state.equipments = []  # list of dicts: {id,label,w,h,weight,x,y,rot}

# 장비 추가 폼
st.sidebar.header("장비 추가")
with st.sidebar.form("add_eq", clear_on_submit=True):
    label = st.text_input("라벨 (이름)", value=f"장비{len(st.session_state.equipments)+1}")
    w = st.number_input("가로 (mm)", min_value=1, value=500)
    h = st.number_input("세로 (mm)", min_value=1, value=400)
    weight = st.number_input("무게 (kg)", min_value=0.1, value=50.0)
    x = st.number_input("좌상단 X 위치 (mm, 왼쪽=0)", min_value=0, value=0)
    y = st.number_input("좌상단 Y 위치 (mm, 위=0)", min_value=0, value=0)
    submitted = st.form_submit_button("장비 추가")
if submitted:
    # 위치가 영역 밖이면 맞춤
    x = float(min(max(0, x), max(0, AREA_W - w)))
    y = float(min(max(0, y), max(0, AREA_H - h)))
    st.session_state.equipments.append({
        "id": len(st.session_state.equipments),
        "label": label,
        "w": float(w),
        "h": float(h),
        "weight": float(weight),
        "x": float(x),
        "y": float(y),
        "rot": 0
    })

# 장비 목록, 수정 및 삭제 UI
st.sidebar.header("장비 목록 / 편집")
if len(st.session_state.equipments) == 0:
    st.sidebar.write("장비가 없습니다. 추가하세요.")
else:
    for i, eq in enumerate(st.session_state.equipments):
        st.sidebar.markdown(f"**#{i+1} — {eq['label']}**")
        col1, col2 = st.sidebar.columns([1,1])
        if col1.button("90° 회전", key=f"rot_{i}"):
            # swap w,h
            eq["w"], eq["h"] = eq["h"], eq["w"]
            eq["rot"] = (eq["rot"] + 90) % 360
        if col2.button("삭제", key=f"del_{i}"):
            st.session_state.equipments.pop(i)
            st.experimental_rerun()

# 자동 배치 (무충돌 랜덤)
st.sidebar.header("자동 배치")
if st.sidebar.button("무충돌 랜덤 자동배치"):
    import random
    placed = []
    for eq in st.session_state.equipments:
        placed_flag = False
        for _ in range(5000):
            rx = random.uniform(0, max(0, AREA_W - eq["w"]))
            ry = random.uniform(0, max(0, AREA_H - eq["h"]))
            rect = (rx, ry, rx + eq["w"], ry + eq["h"])
            collision = False
            for p in placed:
                # p: (x0,y0,x1,y1)
                if not (rect[2] <= p[0] or rect[0] >= p[2] or rect[3] <= p[1] or rect[1] >= p[3]):
                    collision = True
                    break
            if not collision:
                eq["x"], eq["y"] = rx, ry
                placed.append(rect)
                placed_flag = True
                break
        if not placed_flag:
            # 못찾으면 (0,0) 근처
            eq["x"], eq["y"] = 0.0, 0.0
    st.success("자동 배치 완료")
    st.experimental_rerun()

# 메인: 장비 테이블 + 위치 직접 편집
st.header("장비 테이블 — 위치 직접 편집")
if len(st.session_state.equipments) == 0:
    st.info("먼저 장비를 추가하세요.")
else:
    df = pd.DataFrame(st.session_state.equipments)
    # 표시용 칼럼 정리
    df_display = df[["id","label","w","h","weight","x","y","rot"]].copy()
    st.dataframe(df_display, use_container_width=True)

    st.markdown("**선택하여 위치 수정 / 임시저장**")
    sel_idx = st.number_input("편집할 장비 ID (위 표의 id 사용)", min_value=0, max_value=max(df["id"]), value=0, step=1)
    # find equipment
    editable = None
    for eq in st.session_state.equipments:
        if eq["id"] == sel_idx:
            editable = eq
            break
    if editable is not None:
        col1, col2 = st.columns(2)
        with col1:
            nx = st.number_input("X (mm)", min_value=0.0, value=float(editable["x"]))
            ny = st.number_input("Y (mm)", min_value=0.0, value=float(editable["y"]))
        with col2:
            nw = st.number_input("가로 (mm)", min_value=1.0, value=float(editable["w"]))
            nh = st.number_input("세로 (mm)", min_value=1.0, value=float(editable["h"]))
        if st.button("위치/사이즈 저장"):
            # clamp
            nx = float(min(max(0, nx), max(0, AREA_W - nw)))
            ny = float(min(max(0, ny), max(0, AREA_H - nh)))
            editable["x"], editable["y"], editable["w"], editable["h"] = nx, ny, float(nw), float(nh)
            st.success("저장되었습니다")
            st.experimental_rerun()

# 하중 분포 계산 함수
def compute_load_map(equipments, area_w, area_h, gx, gy, smooth_sigma):
    xs = np.linspace(0, area_w, gx)
    ys = np.linspace(0, area_h, gy)
    xv, yv = np.meshgrid(xs, ys)
    load = np.zeros_like(xv)

    # distribute each equipment weight uniformly inside its rectangle
    for eq in equipments:
        x0 = eq["x"]
        y0 = eq["y"]
        x1 = x0 + eq["w"]
        y1 = y0 + eq["h"]
        inside = (xv >= x0) & (xv <= x1) & (yv >= y0) & (yv <= y1)
        n_inside = inside.sum()
        if n_inside > 0:
            load += inside * (eq["weight"] / n_inside)

    if smooth_sigma and smooth_sigma > 0:
        load = gaussian_filter(load, sigma=smooth_sigma)
    return xs, ys, load

# 시각화
st.header("하중 분포 시각화 (히트맵 + 등고선)")
if st.button("하중분포 계산 및 그리기"):
    xs, ys, load = compute_load_map(st.session_state.equipments, AREA_W, AREA_H, grid_x, grid_y, smooth_sigma)
    fig, ax = plt.subplots(figsize=(10,6))
    im = ax.imshow(load, origin='lower', extent=[0,AREA_W,0,AREA_H], aspect='auto')
    try:
        cs = ax.contour(xs, ys, load, levels=8, colors='black', linewidths=0.7)
        ax.clabel(cs, inline=True, fmt="%.1f")
    except Exception:
        pass

    # draw equipment outlines
    for eq in st.session_state.equipments:
        rect = plt.Rectangle((eq["x"], eq["y"]), eq["w"], eq["h"], fill=False, edgecolor='white', linewidth=1.2)
        ax.add_patch(rect)
        ax.text(eq["x"] + 5, eq["y"] + 5, f"{eq['label']} ({eq['weight']}kg)", color='white', fontsize=8)

    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_title("하중 분포 (kg — cell 단위)")
    fig.colorbar(im, ax=ax, label='kg per grid cell (smoothed)')
    st.pyplot(fig)

    # PNG 저장
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=200)
    st.download_button(label="하중분포 PNG 다운로드", data=buf.getvalue(), file_name="load_distribution.png", mime="image/png")

    # CSV 다운로드: 장비 테이블
    out_df = pd.DataFrame(st.session_state.equipments)
    out_df["area_mm2"] = out_df["w"] * out_df["h"]
    out_df["pressure_kg_per_mm2"] = out_df["weight"] / out_df["area_mm2"]
    csv = out_df.to_csv(index=False).encode('utf-8')
    st.download_button(label="장비 테이블 CSV 다운로드", data=csv, file_name="equipments.csv", mime="text/csv")
else:
    st.info("장비를 추가하고 '하중분포 계산 및 그리기' 버튼을 눌러 결과를 확인하세요.")
