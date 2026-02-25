# Copyright (C) 2026 R6Assist Developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import requests
from bs4 import BeautifulSoup
import time
import re
import json
import sys
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

class R6StatsFetcher:
    def __init__(self, base_url="https://liquipedia.net/rainbowsix/Portal:Operators", output_file="data/op_stats.json"):
        self.base_url = base_url
        self.output_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), output_file)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        self.results = {}

    def clean_name(self, name):
        # 處理不間斷空白 ( \xa0 ) 並移除檔名不合法字元 (保持與 get_raw_icon.py 一致的命名邏輯)
        name = name.replace("\xa0", " ")
        name = re.sub(r'[\\/*?:"<>|]', "", name)
        return name.strip()

    def clean_text(self, text):
        if not text:
            return ""
        # 移除多餘空白與 \xa0
        return text.replace('\xa0', ' ').strip()

    def get_soup(self, url):
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"無法存取頁面 {url}: {e}")
            return None

    def get_operator_details(self, name, relative_url, category):
        full_url = f"https://liquipedia.net{relative_url}"
        soup = self.get_soup(full_url)
        
        op_data = {
            "name": name,
            "side": category, # atk, def, recruit
            "url": full_url,
            "role": "Unknown",
            "speed": "Unknown",
            "health": "Unknown",
            "details": {} # 儲存所有抓到的屬性以備不時之需
        }

        if not soup:
            return op_data

        # 尋找 Infobox
        # 通常是 div.fo-nttax-infobox
        infobox = soup.select_one('.fo-nttax-infobox')
        
        # 若找不到主要 class，嘗試找通用的 infobox
        if not infobox:
            infobox = soup.select_one('.infobox-vertical')

        if infobox:
            # 遍歷所有描述標籤 (.infobox-description)
            descriptions = infobox.select('.infobox-description')
            for desc in descriptions:
                key = self.clean_text(desc.get_text())
                # 值通常在下一個兄弟 div
                value_div = desc.find_next_sibling('div')
                if value_div:
                    # 有時候值裡面又有 HTML tags，使用 get_text 取得純文字
                    value = self.clean_text(value_div.get_text())
                    
                    # 存入 details
                    op_data["details"][key] = value

                    # 解析特定欄位
                    if "Operator Role" in key:
                        # 嘗試找出所有的連結作為標籤
                        links = value_div.select('a')
                        if links:
                            roles = [self.clean_text(link.get_text()) for link in links]
                            op_data["role"] = roles
                        else:
                            # 如果沒有連結，嘗試使用 separator 取出文字後分割 (預防黏在一起)
                            text_with_sep = value_div.get_text(separator="|")
                            roles = [self.clean_text(r) for r in text_with_sep.split("|") if self.clean_text(r)]
                            op_data["role"] = roles
                    elif "Speed" in key:
                        op_data["speed"] = value
                    elif "Health" in key or "Armor" in key:
                        # 新版 Wiki 顯示 Armor/Health，舊版可能顯示 Armor Rating
                        op_data["health"] = value

        return op_data

    def run(self):
        # 設定輸出編碼
        if sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

        print(f"正在存取 Portal 頁面: {self.base_url}")
        soup = self.get_soup(self.base_url)
        if not soup:
            print("無法取得 Portal 頁面，程式終止。")
            return

        headers = soup.select('span.gigas-text')
        tasks = []

        print("正在解析幹員列表...")
        for header in headers:
            header_text = header.get_text().strip().lower()
            if 'attacker' in header_text:
                category = "atk"
            elif 'defender' in header_text:
                category = "def"
            elif 'legacy' in header_text:
                category = "recruit"
            else:
                continue

            center_tag = header.find_parent('center')
            if not center_tag:
                continue
                
            next_b = center_tag.find_next_sibling('b')
            if not next_b:
                continue
            
            gallery = next_b.select_one('ul.gallery')
            if not gallery:
                continue
                
            boxes = gallery.select('li.gallerybox')
            for box in boxes:
                text_div = box.select_one('.gallerytext')
                if not text_div:
                    continue

                first_link = text_div.select_one('a')
                if not first_link:
                    continue

                raw_name = first_link.get_text().strip()
                href = first_link.get('href')

                # 清理名稱
                name = self.clean_name(raw_name)
                name = name.replace("(Operator)", "").strip()
                name = re.sub(r'\s[A-Z]{2}$', '', name).strip()

                if name and href:
                    tasks.append((name, href, category))

        print(f"找到 {len(tasks)} 位幹員，開始爬取詳細資料 (Max threads: 5)...")
        # 使用多線程爬取詳細資料
        max_workers = 5
        count = 0
        total = len(tasks)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_op = {executor.submit(self.get_operator_details, name, href, cat): name for name, href, cat in tasks}
            
            for future in as_completed(future_to_op):
                name = future_to_op[future]
                try:
                    data = future.result()
                    self.results[name] = data
                    count += 1
                    # 簡單的進度條
                    sys.stdout.write(f"\r[{count}/{total}] 已處理: {name}          ")
                    sys.stdout.flush()
                except Exception as e:
                    print(f"\n處理 {name} 時發生錯誤: {e}")

        print(f"\n爬取完成，正在寫入 {self.output_file}...")
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=4)
            print("檔案寫入成功!")
        except Exception as e:
            print(f"寫入檔案失敗: {e}")

if __name__ == "__main__":
    fetcher = R6StatsFetcher()
    fetcher.run()
