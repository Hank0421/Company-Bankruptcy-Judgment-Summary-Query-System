from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import time
import csv


# 初始化瀏覽器
options = Options()
options.add_argument('--headless')  # 可拿掉這行來顯示瀏覽器畫面
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)
import re
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

# 年度範圍（114~104，含2015年）
start_year = 114
end_year = 104

all_links = []

for year in range(start_year, end_year - 1, -1):
    keyword = f"{year}年度破字"
    print(f"\n=== 查詢：{keyword} ===")
    # 打開查詢頁
    driver.get("https://judgment.judicial.gov.tw/FJUD/default.aspx")
    try:
        search_input = wait.until(EC.presence_of_element_located((By.ID, "txtKW")))
        search_input.clear()
        search_input.send_keys(keyword)
        search_input.send_keys(Keys.ENTER)
    except Exception as e:
        print(f"找不到搜尋欄 (id=txtKW)，錯誤：{e}")
        continue

    page = 0
    stop = False
    while not stop:
        page += 1
        print(f"處理第 {page} 頁...")
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "iframe-data")))
            table = wait.until(EC.presence_of_element_located((By.ID, "jud")))
            links = table.find_elements(By.CSS_SELECTOR, "a[href*='id=']")
            for link in links:
                href = link.get_attribute("href")
                title = link.text.strip()
                # 從標題擷取日期
                m = re.search(r'(\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日', title)
                if m:
                    date_str = f"{m.group(1)}年{m.group(2)}月{m.group(3)}日"
                    ad_date = minguo_to_ad(date_str)
                    if ad_date < "2015-01-01":
                        stop = True
                        break
                if href and title:
                    all_links.append({"title": title, "url": href})
        except Exception as e:
            print(f"擷取資料時發生錯誤：{e}")
            try:
                print("iframe 內容前 500 字：", driver.page_source[:500])
            except:
                pass
            break

        # 切回主頁面
        driver.switch_to.default_content()

        if stop:
            print("已遇到2015年以前的判決，停止本年度爬取。")
            break

        # 點下一頁
        try:
            time.sleep(1)
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "iframe-data")))
            next_button = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "下一頁")))
            next_button.click()
            print("已點擊下一頁")
            time.sleep(2)
            driver.switch_to.default_content()
        except Exception as e:
            print(f"無法前往下一頁：{e}")
            try:
                driver.switch_to.default_content()
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "iframe-data")))
                print("iframe 內容前 500 字：", driver.page_source[:500])
            except Exception as e2:
                print("無法取得 iframe 內容：", e2)
            break
            print("已點擊下一頁")
            time.sleep(2)
            driver.switch_to.default_content()
        except Exception as e:
            print(f"無法前往下一頁：{e}")
            try:
                driver.switch_to.default_content()
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "iframe-data")))
                print("iframe 內容前 500 字：", driver.page_source[:500])
            except Exception as e2:
                print("無法取得 iframe 內容：", e2)
            break

# 關閉瀏覽器
driver.quit()

# 儲存為 CSV
csv_file = "破字_判決連結.csv"
with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["title", "url"])
    writer.writeheader()
    writer.writerows(all_links)

print(f"\n共擷取 {len(all_links)} 筆連結，已儲存為 {csv_file}")
