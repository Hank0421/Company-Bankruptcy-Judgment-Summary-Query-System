import streamlit as st
import pandas as pd

st.set_page_config(page_title="公司破產判決摘要查詢", layout="wide")
st.title("公司破產判決摘要查詢（2015年起）")

@st.cache_data
def load_data():
    return pd.read_csv("公司破產判決摘要.csv")

df = load_data()

# 移除理由摘要欄位（如果存在）
if "理由摘要" in df.columns:
    df = df.drop(columns=["理由摘要"])

# 新增判決連結欄位，轉為超連結
if "url" in df.columns:
    df["判決連結"] = df["url"].apply(lambda x: f'<a href="{x}" target="_blank">點我看判決</a>')

# 搜尋功能
search = st.text_input("請輸入關鍵字（公司名、裁判字號、理由等）進行篩選：")
if search:
    mask = df.apply(lambda row: search in str(row.values), axis=1)
    filtered = df[mask]
else:
    filtered = df

# 只顯示想要的欄位（排除url，理由摘要已移除）
show_cols = [col for col in ["裁判字號", "裁判日期", "申請人", "是否核准", "是否有抗告", "Gemini摘要", "判決連結"] if col in filtered.columns]

st.write(f"共 {len(filtered)} 筆公司破產判決摘要")
st.write(filtered[show_cols].to_html(escape=False, index=False), unsafe_allow_html=True)

# 下載功能：CSV 內的判決連結也要是超連結
csv_df = filtered.copy()
if "url" in csv_df.columns:
    csv_df["判決連結"] = csv_df["url"].apply(lambda x: f'=HYPERLINK("{x}", "點我看判決")')
show_csv_cols = [col for col in ["裁判字號", "裁判日期", "申請人", "是否核准", "是否有抗告", "Gemini摘要", "判決連結"] if col in csv_df.columns]
csv = csv_df[show_csv_cols].to_csv(index=False, encoding="utf-8-sig")
st.download_button(
    label="下載目前篩選結果 (CSV)",
    data=csv,
    file_name="公司破產判決摘要_查詢結果.csv",
    mime="text/csv"
)

st.markdown("""
- 本頁面由自動爬蟲與 Gemini AI 摘要產生，僅供學術與資訊參考。
- 原始資料來源：[司法院裁判書查詢系統](https://judgment.judicial.gov.tw/FJUD/default.aspx)
- 製作人：張景翰
""")
