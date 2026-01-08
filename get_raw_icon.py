import os
import requests
from bs4 import BeautifulSoup
import time
import re

class R6IconDownloader:
    def __init__(self, base_url="https://liquipedia.net/rainbowsix/Portal:Operators", output_dir="raw_icons"):
        self.base_url = base_url
        self.output_dir = output_dir
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"建立目錄: {self.output_dir}")

    def clean_name(self, name):
        # 處理不間斷空白 ( \xa0 ) 並移除檔名不合法字元
        name = name.replace("\xa0", " ")
        name = re.sub(r'[\\/*?:"<>|]', "", name)
        return name.strip()

    def get_original_url(self, thumb_url):
        # Liquipedia 的原始圖片 URL 邏輯：
        # Thumbnail: .../images/thumb/x/xx/Filename.png/100px-Filename.png
        # Original: .../images/x/xx/Filename.png
        if "/thumb/" in thumb_url:
            # 處理路徑：移除 /thumb/ 並移除最後一個縮圖檔名部分
            # 使用更穩健的方法取代字串
            original_url = thumb_url.replace("/thumb/", "/")
            # 移除最後一項 (例如 /100px-Filename.png)
            parts = original_url.split("/")
            return "/".join(parts[:-1])
        return thumb_url

    def run(self):
        # 設定輸出編碼以避免 Windows CP950 錯誤
        import sys
        import io
        from concurrent.futures import ThreadPoolExecutor, as_completed

        if sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

        print(f"正在存取: {self.base_url}")
        try:
            response = requests.get(self.base_url, headers=self.headers)
            response.raise_for_status()
        except Exception as e:
            print(f"無法存取頁面: {e}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尋找所有分類標題 (span.gigas-text)
        headers = soup.select('span.gigas-text')
        download_tasks = []

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

            # 建立子目錄
            cat_dir = os.path.join(self.output_dir, category)
            if not os.path.exists(cat_dir):
                os.makedirs(cat_dir)

            # 根據瀏覽器探查結果：header 所在的 center 標籤的下一個兄弟標籤是 b，裡面有 ul.gallery
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
                img_tag = box.select_one('.thumb img')
                
                if not img_tag:
                    continue
                    
                name = ""
                if text_div:
                    first_link = text_div.select_one('a')
                    if first_link:
                        name = first_link.get_text().strip()
                    else:
                        name = text_div.get_text().strip()
                
                if not name:
                    raw_title = img_tag.get('alt', '') or img_tag.get('title', '')
                    name = re.sub(r'\s[A-Z]{2}$', '', raw_title).strip()
                
                if not name:
                    continue
                
                name = self.clean_name(name)
                name = name.replace("(Operator)", "").strip()
                name = re.sub(r'\s[A-Z]{2}$', '', name).strip()
                
                thumb_url = img_tag.get('src', '')
                if not thumb_url:
                    continue

                if thumb_url.startswith('//'):
                    thumb_url = "https:" + thumb_url
                elif thumb_url.startswith('/'):
                    thumb_url = "https://liquipedia.net" + thumb_url
                    
                original_url = self.get_original_url(thumb_url)
                download_tasks.append((name, original_url, category))

        print(f"找到 {len(download_tasks)} 個分類項目，準備開始多線程下載...")
        
        count = 0
        total = len(download_tasks)
        max_workers = 10 
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_info = {executor.submit(self.download_image, name, url, cat): (name, cat) for name, url, cat in download_tasks}
            
            for future in as_completed(future_to_info):
                name, cat = future_to_info[future]
                try:
                    result = future.result()
                    if result:
                        count += 1
                    sys.stdout.write(f"\r進度: {count}/{total} - [{cat}] {name}          ")
                    sys.stdout.flush()
                except Exception as e:
                    print(f"\n任務失敗 {name}: {repr(e)}")

        print(f"\n完成! 共處理 {total} 個項目。")

    def download_image(self, name, url, category):
        file_path = os.path.join(self.output_dir, category, f"{name}.png")
        
        # 檢查是否已存在且檔案大小正常
        if os.path.exists(file_path) and os.path.getsize(file_path) > 1000:
            return False

        try:
            img_response = requests.get(url, headers=self.headers, timeout=10)
            img_response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                f.write(img_response.content)
            return True
        except Exception as e:
            return False

if __name__ == "__main__":
    downloader = R6IconDownloader()
    downloader.run()
