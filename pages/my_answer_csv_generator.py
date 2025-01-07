import streamlit as st
import pandas as pd
import io
import os
import zipfile

def calculate_weights(n):
    """根据行数计算权重列表"""
    if n == 1:
        return [100]
    elif n == 2:
        return [60, 40]
    elif n == 3:
        return [30, 30, 40]
    elif n == 4:
        return [30, 30, 30, 10]
    elif n == 5:
        return [30, 30, 20, 10, 10]
    elif n == 6:
        return [30, 30, 10, 10, 10, 10]
    elif n == 7:
        return [30, 20, 10, 10, 10, 10, 10]
    elif n == 8:
        return [30, 20, 10, 10, 10, 10, 5, 5]
    elif n == 9:
        return [30, 20, 10, 10, 10, 5, 5, 5, 5]
    elif n == 10:
        return [30, 20, 10, 10, 5, 5, 5, 5, 5, 5]
    elif n == 11:
        return [30, 20, 10, 5, 5, 5, 5, 5, 5, 5, 5]
    elif n == 12:
        return [30, 20, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
    elif n == 13:
        return [30, 10, 10, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
    elif n == 14:
        return [20, 10, 10, 10, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
    elif n == 15:
        return [20, 10, 10, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
    elif n > 15:
        raise ValueError("上传文件行数过多（>15），请手动赋值")
    elif n < 1:
        raise ValueError("请检查上传文件内容是否正确")
    else:
        return []

def process_csv(uploaded_file):
    """处理上传的CSV文件，并返回处理后的DataFrame"""
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"读取文件失败, 请确保上传csv文件. 错误信息: {e}")
        return None

    if 'id' not in df.columns or 'answer' not in df.columns:
        st.error("CSV 文件必须包含 'id' 和 'answer' 列")
        return None

    if df[['id','answer']].isnull().values.any():
        st.error("id 或 answer 列存在缺失值，请检查")
        return None
    
    df = df.rename(columns={'answer': 'my_answer'})
    
    n = len(df)
    
    try:
        weights = calculate_weights(n)
        df['weight'] = weights + [0]*(n-len(weights))
    except ValueError as e:
        st.error(e)
        return None
    
    return df


st.title("批量生成 my_answer CSV 答案文件")

# 分数设置规则展示
with st.expander("点击查看分数设置规则"):
    st.markdown("""
| 题目数 | 每题分数                                         |
| ------ | ------------------------------------------------ |
| 1      | 100                                              |
| 2      | [60, 40]                                         |
| 3      | [30, 30, 40]                                     |
| 4      | [30, 30, 30, 10]                                 |
| 5      | [30, 30, 20, 10, 10]                             |
| 6      | [30, 30, 10, 10, 10, 10]                         |
| 7      | [30, 20, 10, 10, 10, 10, 10]                     |
| 8      | [30, 20, 10, 10, 10, 10, 5, 5]                   |
| 9      | [30, 20, 10, 10, 10, 5, 5, 5, 5]                 |
| 10     | [30, 20, 10, 10, 5, 5, 5, 5, 5, 5]               |
| 11     | [30, 20, 10, 5, 5, 5, 5, 5, 5, 5, 5]             |
| 12     | [30, 20, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]           |
| 13     | [30, 10, 10, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]       |
| 14     | [20, 10, 10, 10, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]   |
| 15     | [20, 10, 10, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5] |
""")

uploaded_files = st.file_uploader("上传一个或多个 CSV 文件 (包含 id 和 answer 列)", type=["csv"], accept_multiple_files=True)

if uploaded_files:
    processed_dfs = []
    for uploaded_file in uploaded_files:
        processed_df = process_csv(uploaded_file)
        if processed_df is not None:
            processed_dfs.append( (uploaded_file.name, processed_df) ) # 保存文件名和DataFrame

    if processed_dfs:
       
        st.write("处理后的数据:")
        for filename, df in processed_dfs:
           new_filename = f"my_{filename}"
           csv_buffer = io.StringIO()
           df.to_csv(csv_buffer, index=False)

           st.download_button(
                label=f"下载 {new_filename}",
                data=csv_buffer.getvalue(),
                file_name=new_filename,
                mime="text/csv"
            )
           st.write(f"**{filename}**:")
           st.dataframe(df)
        
        # 创建 ZIP 下载按钮
        if len(processed_dfs) > 1: # 只有上传多个文件时才显示 zip 下载
           zip_buffer = io.BytesIO()
           with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
              for filename, df in processed_dfs:
                new_filename = f"my_{filename}"
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                zf.writestr(new_filename, csv_buffer.getvalue())

           zip_buffer.seek(0)
           st.download_button(
             label="下载所有处理后的 CSV 文件 (ZIP)",
             data=zip_buffer,
             file_name="processed_csv_files.zip",
             mime="application/zip"
            )