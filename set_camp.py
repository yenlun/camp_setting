import streamlit as st
import json

# Define the pages as a dictionary
pages = {
    "生成 my_answer csv": "pages/my_answer_csv_generator.py",
    "批量生成阶段与任务": "pages/batch_stage_and_task_creator.py",
    "批量生成阶段": "pages/stage_generator.py",
    "学习任务加链接 🚩": "pages/markdown_url_link_app.py",
}

# Create the navigation menu using st.navigation
selected_page = st.select_slider("Select a page", options=list(pages.keys()))

# Get the module path using the selected page and import it
module_path = pages[selected_page]
if module_path:
    with open(module_path, "r", encoding="utf-8") as f:
        module_code = f.read()
    exec(module_code)