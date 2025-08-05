# 公司破產判決摘要查詢系統

本專案自動爬取台灣司法院裁判書查詢系統之「公司破產」相關判決，並以 Gemini AI 進行摘要，最終以網頁互動查詢與下載。

## 主要功能
- 自動爬取 2015 年以來所有公司破產判決（破字案由）
- 自動判斷申請人是否為公司
- 以 Gemini AI 產生三句話重點摘要
- 支援斷點續跑與 quota 失敗重試
- 以 Streamlit 製作互動式查詢網頁，可依關鍵字篩選、下載結果
- 判決連結皆為可點擊超連結

## 專案結構
- `scraper2.py`：爬取破字判決連結
- `batch_summary.py`：批次下載判決、抽取欄位、AI 摘要、產生 CSV
- `app.py`：Streamlit 查詢網頁
- `公司破產判決摘要.csv`：最終查詢資料
- `破字_判決連結.csv`：所有破字判決連結

## 使用方式
1. 安裝 Python 3.8+，建議使用虛擬環境
2. 安裝必要套件：
   ```sh
   pip install -r requirements.txt
   ```
3. 先執行 `scraper2.py` 產生判決連結
4. 執行 `batch_summary.py` 產生摘要與 CSV
5. 執行 `streamlit run app.py` 啟動查詢網頁

## 注意事項
- 本專案僅供學術與資訊參考，勿用於商業用途
- 原始資料來源：[司法院裁判書查詢系統](https://judgment.judicial.gov.tw/FJUD/default.aspx)
- Gemini API 需自備金鑰，請於程式內填寫

## 製作人
張景翰
