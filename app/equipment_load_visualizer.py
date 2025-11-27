import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import io
import json

st.set_page_config(layout="wide", page_title="Equipment Load Visualizer")

st.title("장비 하중 배치 툴 (Drag & Drop + 클릭 추가)")

# 기본 장비
default_items = [
    {"id": "equip1", "label": "장비1", "x": 10, "y": 10, "w": 80, "h": 60, "weight": 100, "rot": 0},
    {"id": "equip2", "label": "장비2", "x": 120, "y": 10, "w": 80, "h": 60, "weight": 150, "rot": 0},
    {"id": "equip3", "label": "장비3", "x": 230, "y": 10, "w": 80, "h": 60, "weight": 120, "rot": 0},
]

if "items" not in st.session_state:
    st.session_state["items"] = default_items

# 좌표 / 크기 / 무게 데이터 에디터
df = pd.DataFrame(st.session_state["items"])
df_display = df[["id", "label", "x", "y", "w", "h", "weight"]]
edited = st.experimental_data_editor(df_display, num_rows="never", use_container_width=True)
st.session_state["items"] = edited.to_dict(orient="records")

# HTML + JS: 드래그 + 그리드 클릭 추가
items_json = json.dumps(st.session_state["items"])
component_html = f"""
<style>
  #canvas-area {{
    width: 930px;
    height: 615px;
    border: 2px solid #aaa;
    position: relative;
    background: #f4f4f4;
    background-image: linear-gradient(0deg, transparent 19px, #ccc 20px),
                      linear-gradient(90deg, transparent 19px, #ccc 20px);
    background-size: 20px 20px;
    overflow: hidden;
  }}
  .item {{
    position: absolute;
    background: rgba(0,150,255,0.3);
    color: white;
    padding: 4px;
    text-align: center;
    font-size: 13px;
    border-radius:6px;
    cursor: grab;
    user-select: none;
    border: 3px solid #ff0000;
  }}
</style>

<div id="canvas-area"></div>

<script>
const canvas = document.getElementById("canvas-area");
let items = {items_json};

// 드래그 기능
function dragElement(elmnt) {{
  var pos1=0, pos2=0, pos3=0, pos4=0;
  elmnt.onmousedown = dragMouseDown;

  function dragMouseDown(e) {{
    e.preventDefault();
    pos3 = e.clientX;
    pos4 = e.clientY;
    document.onmouseup = closeDragElement;
    document.onmousemove = elementDrag;
  }}

  function elementDrag(e) {{
    e.preventDefault();
    pos1 = pos3 - e.clientX;
    pos2 = pos4 - e.clientY;
    pos3 = e.clientX;
    pos4 = e.clientY;
    elmnt.style.top = (elmnt.offsetTop - pos2) + "px";
    elmnt.style.left = (elmnt.offsetLeft - pos1) + "px";
  }}

  function closeDragElement() {{
    document.onmouseup = null;
    document.onmousemove = null;
  }}
}}

// 장비 생성 함수
function createItem(it) {{
  const div = document.createElement("div");
  div.className = "item";
  div.id = it.id;
  div.style.left = it.x + "px";
  div.style.top = it.y + "px";
  div.style.width = it.w + "px";
  div.style.height = it.h + "px";
  div.innerHTML = it.label + "<br><button onclick='rotateItem(\""+it.id+"\")'>회전</button>";
  canvas.appendChild(div);
  dragElement(div);
}}

// 회전
function rotateItem(id) {{
  const el = document.getElementById(id);
  const temp = el.style.width;
  el.style.width = el.style.height;
  el.style.height = temp;
}}

// 초기 장비 생성
items.forEach(it => createItem(it));

// 그리드 클릭 추가
canvas.addEventListener("click", function(e){{
    if(e.target.id === "canvas-area"){{
        const gridSize = 20;
        const rect = canvas.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const clickY = e.clientY - rect.top;
        const snapX = Math.floor(clickX/gridSize)*gridSize;
        const snapY = Math.floor(clickY/gridSize)*gridSize;
        const newId = "equip"+(items.length+1);
        const newItem = {{id:newId, label:"장비"+(items.length+1), x:snapX, y:snapY, w:80, h:60, weight:100, rot:0}};
        items.push(newItem);
        createItem(newItem);
    }}
}});
</script>
"""

st.components.v1.html(component_html, height=650)

# 하중 분포 생성
if st.button("하중분포 생성"):
    canvas_w = 930
    canvas_h = 615
    grid = np.zeros((canvas_h, canvas_w))
    for it in st.session_state["items"]:
        x = int(max(0,min(canvas_w-1,float(it["x"]))))
        y = int(max(0,min(canvas_h-1,float(it["y"]))))
        w = int(max(1,float(it["w"])))
        h = int(max(1,float(it["h"])))
        weight = float(it["weight"])
        x2 = min(canvas_w, x+w)
        y2 = min(canvas_h, y+h)
        grid[y:y2, x:x2] += weight

    fig, ax = plt.subplots(figsize=(9,6))
    im = ax.imshow(grid, cmap="jet", origin="lower")
    ax.set_title("하중 분포 Heatmap")
    plt.colorbar(im, ax=ax)
    st.pyplot(fig)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200)
    st.download_button("PNG 다운로드", data=buf.getvalue(), file_name="loadmap.png", mime="image/png")
