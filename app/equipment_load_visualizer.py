import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import io
import json

st.set_page_config(layout="wide", page_title="Equipment Load Visualizer")

st.title("장비 하중 배치 툴 (그리드 클릭 + 미리보기)")

# 세션 상태 초기화
if "items" not in st.session_state:
    st.session_state["items"] = []
if "selected_item" not in st.session_state:
    st.session_state["selected_item"] = None

# Sidebar: 장비 추가 폼
with st.sidebar.form("add_equipment"):
    label = st.text_input("장비 이름", "장비X")
    w = st.number_input("가로(mm)", min_value=10, max_value=500, value=80)
    h = st.number_input("세로(mm)", min_value=10, max_value=500, value=60)
    weight = st.number_input("무게(kg)", min_value=1, max_value=10000, value=100)
    submitted = st.form_submit_button("장비 추가")

    if submitted:
        new_id = f"equip{len(st.session_state['items'])+1}"
        st.session_state['items'].append({
            "id": new_id, "label": label, "x":0, "y":0, "w":w, "h":h, "weight":weight, "rot":0
        })
        st.session_state["selected_item"] = st.session_state['items'][-1]

# 현재 장비 선택
if st.session_state['items']:
    labels = [it["label"] for it in st.session_state['items']]
    selected_label = st.sidebar.selectbox("편집/미리보기 장비 선택", labels)
    st.session_state["selected_item"] = next(it for it in st.session_state['items'] if it["label"]==selected_label)

# 안전하게 selected_item_id 전달
selected_item_id = st.session_state["selected_item"]["id"] if st.session_state["selected_item"] else "null"

# Canvas + JS
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
  .preview-item {{
    position: absolute;
    background: rgba(0,150,255,0.1);
    border: 2px dashed #ff0000;
    pointer-events: none;
  }}
  .rotate-btn {{
    font-size:10px;
    margin-top:2px;
    cursor:pointer;
    background:white;
    color:black;
    border:none;
    padding:1px 2px;
    border-radius:2px;
  }}
</style>

<div id="canvas-area"></div>

<script>
const canvas = document.getElementById("canvas-area");
let items = {items_json};
let selectedItem = null;

if ("{selected_item_id}" !== "null") {{
    selectedItem = items.find(it => it.id == "{selected_item_id}");
}}

let previewDiv = null;

// 드래그 기능
function dragElement(elmnt) {{
  var pos1=0,pos2=0,pos3=0,pos4=0;
  elmnt.onmousedown = dragMouseDown;

  function dragMouseDown(e){{
    e.preventDefault();
    pos3=e.clientX; pos4=e.clientY;
    document.onmouseup=closeDragElement;
    document.onmousemove=elementDrag;
  }}

  function elementDrag(e){{
    e.preventDefault();
    pos1=pos3-e.clientX;
    pos2=pos4-e.clientY;
    pos3=e.clientX;
    pos4=e.clientY;
    elmnt.style.top=(elmnt.offsetTop-pos2)+"px";
    elmnt.style.left=(elmnt.offsetLeft-pos1)+"px";
  }}

  function closeDragElement(){{
    document.onmouseup=null;
    document.onmousemove=null;
  }}
}}

// 장비 생성
function createItem(it){{
  const div = document.createElement("div");
  div.className="item";
  div.id=it.id;
  div.style.left=it.x+"px";
  div.style.top=it.y+"px";
  div.style.width=it.w+"px";
  div.style.height=it.h+"px";
  div.innerHTML=it.label+"<br><button class='rotate-btn' onclick='rotateItem(\""+it.id+"\")'>회전</button>";
  canvas.appendChild(div);
  dragElement(div);
}}

// 회전
function rotateItem(id){{
  const el = document.getElementById(id);
  const temp = el.style.width;
  el.style.width = el.style.height;
  el.style.height = temp;
}}

// 초기 장비 생성
items.forEach(it=>createItem(it));

// 그리드 클릭 미리보기
canvas.addEventListener("mousemove", function(e){{
    if(!selectedItem) return;
    const gridSize = 20;
    const rect = canvas.getBoundingClientRect();
    const snapX = Math.floor((e.clientX-rect.left)/gridSize)*gridSize;
    const snapY = Math.floor((e.clientY-rect.top)/gridSize)*gridSize;
    if(previewDiv) previewDiv.remove();
    previewDiv = document.createElement("div");
    previewDiv.className="preview-item";
    previewDiv.style.left = snapX + "px";
    previewDiv.style.top = snapY + "px";
    previewDiv.style.width = selectedItem.w + "px";
    previewDiv.style.height = selectedItem.h + "px";
    canvas.appendChild(previewDiv);
}});

canvas.addEventListener("click", function(e){{
    if(!selectedItem) return;
    const gridSize = 20;
    const rect = canvas.getBoundingClientRect();
    const snapX = Math.floor((e.clientX-rect.left)/gridSize)*gridSize;
    const snapY = Math.floor((e.clientY-rect.top)/gridSize)*gridSize;
    selectedItem.x = snapX;
    selectedItem.y = snapY;
    createItem(selectedItem);
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
        h = int(max(1,float(it["h"]))))
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
