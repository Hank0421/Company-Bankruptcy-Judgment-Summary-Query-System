# === 讀取已產生的公司破產判決摘要（如有） ===
import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import google.generativeai as genai
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

gemini_summary_map = {}
if os.path.exists("公司破產判決摘要.csv"):
    old_df = pd.read_csv("公司破產判決摘要.csv")
    # 以 url 為 key，存下已成功的 Gemini 摘要
    for _, row in old_df.iterrows():
        url = row.get("url")
        gemini = row.get("Gemini摘要", "")
        # 只保留非 429 quota 失敗的 Gemini 摘要
        if isinstance(gemini, str) and not gemini.startswith("摘要失敗：429") and not gemini.startswith("摘要失敗：429\n") and gemini.strip() != "":
            gemini_summary_map[url] = gemini

# === Gemini API 設定 ===
genai.configure(api_key="AIzaSyAWCFqEi2s977vs-dCHZATNT608sKXb7bk")
model = genai.GenerativeModel("gemini-2.5-flash-lite")

# === 讀取破字_判決連結.csv ===
links_df = pd.read_csv("破字_判決連結.csv")

# === 公司判斷關鍵字 ===
company_keywords = ["有限公司", "股份有限公司", "公司", "股份公司"]

def is_company(applicant):
    if any(kw in applicant for kw in company_keywords):
        return True
    return False

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
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"連結失敗: {url}，錯誤: {e}")
        return None

def extract_fields_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    raw_text = soup.get_text(separator="\n", strip=True)

    # 裁判字號
    case_number = "無法擷取"
    h2 = soup.find("h2")
    if h2 and h2.text.strip():
        case_number = h2.text.strip()
    else:
        m = re.search(r"[\u4e00-\u9fa5]{2,}\s*\d+\s*年度.*?字第.*?號.*?(裁定|判決)", raw_text)
        if m:
            case_number = m.group(0)

    # 裁判日期
    judgment_date = "無法擷取"
    m = re.search(r"中華民國\s*\d+\s*年\s*\d+\s*月\s*\d+\s*日", raw_text)
    if m:
        judgment_date = m.group(0)
    else:
        m = re.search(r"\d+\s*年\s*\d+\s*月\s*\d+\s*日", raw_text)
        if m:
            judgment_date = m.group(0)

    # 只抓每一行開頭的聲請人/申請人（允許多個空格/全形空格），去除多餘空白
    applicant_name = "無法判斷"
    # 將兩個正規表示式合併為一個，並預先編譯以提升效率
    # (?:...) 是非捕獲分組，用 | 來表示 "或"
    applicant_pattern = re.compile(r'^[\s　]*(?:[申聲][\s　]*請|[抗][\s　]*告)[\s　]*人[\s　]*(.+)$')
    for line in raw_text.splitlines():
        m = applicant_pattern.match(line)
        if m:
            applicant_name = m.group(1).strip()
            break

    # 是否核准
    approved_status = "補正中"
    if "駁回" in raw_text:
        approved_status = "駁回"
    elif "准予" in raw_text or "裁定破產" in raw_text:
        approved_status = "核准"

    # 理由摘要
    reason_match = re.search(r"(本院認為|理由如下)[\s\S]{0,1000}", raw_text)
    reason_summary = reason_match.group(0) if reason_match else "無法擷取理由"

    # ================== 修改後的抗告判斷邏輯 ==================
    appeal_status = "抗告案" if re.search(r"抗[\s　]*告[\s　]*人", raw_text) else "非抗告案"
    # =======================================================
    
    # Gemini 摘要
    summary_prompt = f"請幫我將以下台灣法院破產裁定判決文字摘要成三句話的簡要內容：\n\n{raw_text[:3500]}"
    try:
        response = model.generate_content(summary_prompt)
        gemini_summary = response.text.strip()
    except Exception as e:
        gemini_summary = f"摘要失敗：{e}"

    return {
        "裁判字號": case_number,
        "裁判日期": judgment_date,
        "申請人": applicant_name,
        "是否核准": approved_status,
        "理由摘要": reason_summary,
        "是否為抗告案": appeal_status,
        "Gemini摘要": gemini_summary
    }

def minguo_to_ad(date_str):
    m = re.search(r'(\d+)[^\d]+(\d+)[^\d]+(\d+)', str(date_str))
    if m:
        year, month, day = m.groups()
        try:
            ad_year = int(year) + 1911 if int(year) < 3000 else int(year)
            return f"{ad_year:04d}-{int(month):02d}-{int(day):02d}"
        except:
            return "0000-00-00"
    return "0000-00-00"

# === 批次處理 ===
results = []
for idx, row in links_df.iterrows():
    print(f"[{idx+1}/{len(links_df)}] 處理: {row['title']}")
    url = row['url']
    html = get_judgment_html(url)
    if not html:
        continue
    fields = extract_fields_from_html(html)
    # 決定 Gemini 摘要是否要續跑
    if url in gemini_summary_map:
        fields["Gemini摘要"] = gemini_summary_map[url]
    # 其餘欄位（如申請人）都重新產生
    keep = is_company(fields["申請人"])
    if not keep:
        # 若申請人擷取失敗，直接在全文搜尋公司關鍵字
        soup = BeautifulSoup(html, "html.parser")
        raw_text = soup.get_text(separator="\n", strip=True)
        if any(kw in raw_text for kw in company_keywords):
            keep = True
    if keep:
        result = {"url": url}
        result.update(fields)
        results.append(result)
    time.sleep(2)  # 禮貌延遲，避免被封鎖

# === 輸出公司破產判決摘要 ===
if results:
    df = pd.DataFrame(results)
    def minguo_to_ad(date_str):
        m = re.search(r'(\d+)[^\d]+(\d+)[^\d]+(\d+)', str(date_str))
        if m:
            year, month, day = m.groups()
            try:
                ad_year = int(year) + 1911 if int(year) < 3000 else int(year)
                return f"{ad_year:04d}-{int(month):02d}-{int(day):02d}"
            except:
                return "0000-00-00"
        return "0000-00-00"
    df["裁判日期排序"] = df["裁判日期"].apply(minguo_to_ad)
    df = df[df["裁判日期排序"] >= "2015-01-01"]
    df = df.sort_values("裁判日期排序", ascending=False)
    df = df.drop(columns=["裁判日期排序"])
    columns = ["裁判字號", "裁判日期", "申請人", "是否核准", "理由摘要", "是否為抗告案", "Gemini摘要", "url"]
    df = df[[col for col in columns if col in df.columns]]
    df.to_csv("公司破產判決摘要.csv", index=False, encoding="utf-8-sig")
    print(f"已產生 {len(df)} 筆公司破產判決摘要，存為 公司破產判決摘要.csv")
else:
    print("未找到公司破產案件。")