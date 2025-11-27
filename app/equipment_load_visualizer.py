import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import io
import json

st.set_page_config(layout="wide", page_title="Equipment Load Visualizer")
st.title("장비 하중 배치 툴 (클릭 배치 + 관리 + 회전/삭제)")

# 세션 상태 초기화
if "items" not in st.session_state:
    st.session_state["items"] = []
if "placed_items" not in st.session_state:
    st.session_state["placed_items"] = []
if "selected_item_index" not in st.session_state:
    st.session_state["selected_item_index"] = None

# Sidebar: 캔버스 설정
st.sidebar.subheader("캔버스 설정")
canvas_w = st.sidebar.number_input("캔버스 가로(mm)", min_value=200, max_value=5000, value=930)
canvas_h = st.sidebar.number_input("캔버스 세로(mm)", min_value=200, max_value=5000, value=615)
grid_size = st.sidebar.number_input("그리드 크기(px)", min_value=5, max_value=200, value=20)

# Sidebar: 장비 추가
with st.sidebar.form("add_equipment"):
    label = st.text_input("장비 이름", f"장비{len(st.session_state['items'])+1}")
    w = st.number_input("가로(mm)", min_value=10, max_value=2500, value=80)
    h = st.number_input("세로(mm)", min_value=10, max_value=2500, value=60)
    weight = st.number_input("무게(kg)", min_value=1, max_value=10000, value=100)
    submitted = st.form_submit_button("장비 추가")
    if submitted:
        st.session_state["items"].append({
            "label": label, "w": w, "h": h, "weight": weight
        })
        st.session_state["selected_item_index"] = len(st.session_state["items"]) - 1

# 장비 관리 / 삭제
st.sidebar.subheader("장비 목록 관리")
to_remove = None
for i, it in enumerate(st.session_state["items"]):
    col1, col2 = st.sidebar.columns([3,1])
    col1.write(f"{it['label']} ({it['w']}x{it['h']} mm, {it['weight']} kg)")
    if col2.button("삭제", key=f"del_{i}"):
        to_remove = i
if to_remove is not None:
    st.session_state["items"].pop(to_remove)
    st.experimental_rerun()

# 선택 장비
st.sidebar.subheader("배치할 장비 선택")
if st.session_state["items"]:
    st.session_state["selected_item_index"] = st.sidebar.radio(
        "장비 선택",
        options=range(len(st.session_state["items"])),
        index=st.session_state["selected_item_index"] or 0,
        format_func=lambda x: st.session_state["items"][x]["label"]
    )
    selected_item = st.session_state["items"][st.session_state["selected_item_index"]]
else:
    selected_item = None

# 배치 초기화
def reset_placement():
    st.session_state["placed_items"] = []

st.sidebar.button("배치 초기화", on_click=reset_placement)

# 캔버스 HTML + JS
st.subheader("장비 배치 캔버스 (클릭 배치 + 회전/삭제 + 확대/축소)")

items_json = json.dumps(st.session_state["items"])
placed_json = json.dumps(st.session_state["placed_items"])
selected_id = str(st.session_state["selected_item_index"]) if selected_item else "null"

canvas_html = f"""
<style>
#canvas-wrapper {{
  width:100%;
  overflow:auto;
}}
#canvas-controls {{
  margin-bottom:5px;
}}
#canvas-area {{
  border: 2px solid #aaa;
  position: relative;
  background: #f4f4f4;
  background-image: linear-gradient(0deg, transparent {grid_size-1}px, #ccc {grid_size}px),
                    linear-gradient(90deg, transparent {grid_size-1}px, #ccc {grid_size}px);
  background-size: {grid_size}px {grid_size}px;
  overflow: hidden;
  height:{canvas_h}px;
  width:{canvas_w}px;
}}
.item {{
  position: absolute;
  background: rgba(0,150,255,0.3);
  border: 2px solid red;
  text-align: center;
  font-size: 12px;
  pointer-events:none;
}}
.rotate-btn, .del-btn {{
  position:absolute;
  font-size:10px;
  background:white;
  border:1px solid #aaa;
  border-radius:2px;
  cursor:pointer;
}}
</style>

<div id="canvas-controls">
  <button onclick="zoom(1.2)">확대</button>
  <button onclick="zoom(0.8)">축소</button>
  <button onclick="resetCanvas()">초기화</button>
</div>

<div id="canvas-wrapper">
  <div id="canvas-area"></div>
</div>

<script>
let items = {items_json};
let placedItems = {placed_json};
let selectedItemIndex = {selected_id};
let scale = 1;
const canvas = document.getElementById("canvas-area");

function drawItems(){{
    canvas.innerHTML = '';
    placedItems.forEach((it, idx) => {{
        const div = document.createElement('div');
        div.className='item';
        div.style.left = it.x+'px';
        div.style.top = it.y+'px';
        div.style.width = it.w+'px';
        div.style.height = it.h+'px';
        div.innerHTML = it.label;

        // 회전 버튼
        const rotBtn = document.createElement('button');
        rotBtn.className='rotate-btn';
        rotBtn.innerHTML='↻';
        rotBtn.style.top='0px';
        rotBtn.style.right='0px';
        rotBtn.onclick = function(e){{
            e.stopPropagation();
            let temp = it.w;
            it.w = it.h;
            it.h = temp;
            div.style.width = it.w + 'px';
            div.style.height = it.h + 'px';
            fetch("/_stcore/set_session_state", {{
                method:"POST",
                body:JSON.stringify({{key:"placed_items", value:placedItems}})
            }});
        }};
        div.appendChild(rotBtn);

        // 삭제 버튼
        const delBtn = document.createElement('button');
        delBtn.className='del-btn';
        delBtn.style.top='0px';
        delBtn.style.right='20px';
        delBtn.innerHTML='✕';
        delBtn.onclick = function(e){{
            e.stopPropagation();
            placedItems.splice(idx,1);
            drawItems();
            fetch("/_stcore/set_session_state", {{
                method:"POST",
                body:JSON.stringify({{key:"placed_items", value:placedItems}})
            }});
        }};
        div.appendChild(delBtn);

        canvas.appendChild(div);
    }});
}}
drawItems();

// 캔버스 클릭으로 배치
canvas.addEventListener('click', function(e){{
    if(selectedItemIndex === null) return;
    const rect = canvas.getBoundingClientRect();
    const clickX = Math.floor((e.clientX-rect.left)/{grid_size})*{grid_size};
    const clickY = Math.floor((e.clientY-rect.top)/{grid_size})*{grid_size};
    const item = items[selectedItemIndex];
    const placed = {{
        label:item.label,
        w:item.w,
        h:item.h,
        weight:item.weight,
        x:clickX,
        y:clickY
    }};
    placedItems.push(placed);
    drawItems();
    fetch("/_stcore/set_session_state", {{
        method:"POST",
        body:JSON.stringify({{key:"placed_items", value:placedItems}})
    }});
}});

// 캔버스 초기화 (JS)
function resetCanvas(){{
    placedItems = [];
    drawItems();
    fetch("/_stcore/set_session_state", {{
        method:"POST",
        body:JSON.stringify({{key:"placed_items", value:placedItems}})
    }});
}}

function zoom(factor){{
    scale *= factor;
    canvas.style.transform = "scale("+scale+")";
    canvas.style.transformOrigin = "top left";
}}
</script>
"""

st.components.v1.html(canvas_html, height=canvas_h+50)

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

    fig, ax = plt.subplots(figsize=(canvas_w/100, canvas_h/100))
    im = ax.imshow(grid_array, cmap="jet", origin="lower")
    ax.set_title("하중 분포 Heatmap")
    plt.colorbar(im, ax=ax)
    st.pyplot(fig)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200)
    st.download_button("PNG 다운로드", data=buf.getvalue(),
                       file_name="loadmap.png", mime="image/png")
