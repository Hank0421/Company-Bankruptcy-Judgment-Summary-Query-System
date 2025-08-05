import requests
from bs4 import BeautifulSoup
import pandas as pd
import google.generativeai as genai
import re
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# === 設定 Gemini API ===
genai.configure(api_key="AIzaSyAWCFqEi2s977vs-dCHZATNT608sKXb7bk")
model = genai.GenerativeModel("gemini-2.5-flash")

# === 測試網址 ===
url = "https://judgment.judicial.gov.tw/FJUD/data.aspx?ty=JD&id=KLDV,114%2c%e7%a0%b4%2c1%2c20250729%2c1"

def get_judgment_html(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15",
        "Accept-Language": "zh-TW,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        "Referer": "https://judgment.judicial.gov.tw/"
    }

    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))

    response = session.get(url, headers=headers, timeout=10)
    response.raise_for_status()  # 如果失敗就會拋出錯誤
    return response.text


def extract_fields_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    
    # 判決主文與全文
    raw_text = soup.get_text(separator="\n", strip=True)
    
    # 擷取申請人（找「申請人」、「聲請人」）
    applicant = re.findall(r"申請人[:： ]?([^\n，。；；]*)", raw_text)
    if not applicant:
        applicant = re.findall(r"聲請人[:： ]?([^\n，。；；]*)", raw_text)
    applicant_name = applicant[0] if applicant else "無法判斷"
    
    # 是否核准破產
    approved_status = "補正中"
    if "駁回" in raw_text:
        approved_status = "駁回"
    elif "准予" in raw_text or "裁定破產" in raw_text:
        approved_status = "核准"
    
    # 理由摘要：找「理由如下」或「本院認為」段落
    reason_match = re.search(r"(本院認為|理由如下)[\s\S]{0,1000}", raw_text)
    reason_summary = reason_match.group(0) if reason_match else "無法擷取理由"
    
    # 是否有抗告
    appeal_status = "有抗告" if "抗告" in raw_text else "無抗告"
    
    # 判決全文摘要（用 Gemini）
    summary_prompt = f"請幫我將以下台灣法院破產裁定判決文字摘要成三句話的簡要內容：\n\n{raw_text[:3500]}"
    try:
        response = model.generate_content(summary_prompt)
        gemini_summary = response.text.strip()
    except Exception as e:
        gemini_summary = f"摘要失敗：{e}"

    return {
        "申請人": applicant_name,
        "是否核准": approved_status,
        "理由摘要": reason_summary,
        "是否有抗告": appeal_status,
        "Gemini摘要": gemini_summary
    }

# === 主程式 ===
html = get_judgment_html(url)
data = extract_fields_from_html(html)

# === 儲存為表格 ===
df = pd.DataFrame([data])
df.to_csv("破產判決摘要.csv", index=False, encoding="utf-8-sig")
print(df)
