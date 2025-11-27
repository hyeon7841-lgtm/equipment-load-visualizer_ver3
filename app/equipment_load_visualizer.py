New-Item -ItemType Directory -Path equipment-load-visualizer\app -Force
New-Item -ItemType Directory -Path equipment-load-visualizer\.streamlit -Force

Set-Content -Path equipment-load-visualizer\app\app.py -Value @'
# (여기에 위의 app/app.py 전체 내용을 붙여넣으세요)
'@

Set-Content -Path equipment-load-visualizer\requirements.txt -Value @'
streamlit
numpy
matplotlib
pandas
'@

Set-Content -Path equipment-load-visualizer\README.md -Value @'
# Equipment Load Visualizer (Simple Drag HTML Version)

A minimal Streamlit app that embeds an HTML/JS canvas for drag-and-drop of equipment blocks.
After roughly moving blocks, edit precise x/y in the table and click '하중분포 생성' to create the heatmap.

Run locally:
pip install -r requirements.txt
streamlit run app/app.py
'@

Set-Content -Path equipment-load-visualizer\.streamlit\config.toml -Value @'
[theme]
primaryColor = "#4B9CD3"
backgroundColor = "#F7F7F7"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#000000"
'@

Compress-Archive -Path equipment-load-visualizer\* -DestinationPath equipment-load-visualizer.zip
Write-Output "ZIP created: $(Resolve-Path .\equipment-load-visualizer.zip)"
