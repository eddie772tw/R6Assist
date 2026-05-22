import cv2
import numpy as np
import os

class PhaseDetector:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        img_dir = os.path.join(base_dir, "screenshot")
        self.atk_template = os.path.join(img_dir, "temp_atk.png")
        self.def_template = os.path.join(img_dir, "temp_def.png")
        
        # Load templates
        self.tmpl_atk = self._load_template(self.atk_template)
        self.tmpl_def = self._load_template(self.def_template)
        
        # Cache for successful match to speed up subsequent frames
        self.cached_scale = None
        self.cached_team = None
        self.cached_x = None
        self.cached_y = None
        self.cache_miss_count = 0

    def _load_template(self, path):
        if os.path.exists(path):
            img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            return img
        return None

    def _multi_scale_match(self, img, template):
        if template is None:
            return -1, None, 1.0
            
        best_max_val = -1
        best_loc = None
        best_scale = 1.0
        # scales from 0.5 to 2.0
        for scale in np.linspace(0.5, 2.0, 16):
            resized = cv2.resize(template, (0,0), fx=scale, fy=scale)
            if resized.shape[0] > img.shape[0] or resized.shape[1] > img.shape[1]:
                break
            res = cv2.matchTemplate(img, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val > best_max_val:
                best_max_val = max_val
                best_loc = max_loc
                best_scale = scale
        return best_max_val, best_loc, best_scale

    def detect_phase(self, img):
        if img is None or (self.tmpl_atk is None and self.tmpl_def is None):
            return True # Fallback if templates missing

        # 1. 將搜尋區域高度限縮至最頂部的 15% (帶狀區域)，這能免去大部分無謂的大圖計算開銷
        search_h = int(img.shape[0] * 0.15)
        search_region = img[0:search_h, 0:img.shape[1]]
        search_region = cv2.cvtColor(search_region, cv2.COLOR_BGR2GRAY)
        
        # 2. 智慧局部快取 (Temporal Cache Local Tracking)
        if self.cached_scale and self.cached_team in ['atk', 'def'] and self.cached_x is not None:
            template = self.tmpl_atk if self.cached_team == 'atk' else self.tmpl_def
            if template is not None:
                resized = cv2.resize(template, (0,0), fx=self.cached_scale, fy=self.cached_scale)
                th, tw = resized.shape[:2]
                
                # 僅在上一影格檢測到的 (cached_x, cached_y) 周圍 +-15 像素區域進行單次單尺度匹配
                margin = 15
                x_start = max(0, self.cached_x - margin)
                y_start = max(0, self.cached_y - margin)
                x_end = min(search_region.shape[1], self.cached_x + tw + margin)
                y_end = min(search_region.shape[0], self.cached_y + th + margin)
                
                # 確保局部區域大於樣板，才能呼叫 matchTemplate
                if (y_end - y_start) >= th and (x_end - x_start) >= tw:
                    local_region = search_region[y_start:y_end, x_start:x_end]
                    res = cv2.matchTemplate(local_region, resized, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, max_loc = cv2.minMaxLoc(res)
                    
                    if max_val > 0.8:
                        # 局部快取命中！更新快取座標 (加回裁切偏移量)
                        self.cached_x = x_start + max_loc[0]
                        self.cached_y = y_start + max_loc[1]
                        self.cache_miss_count = 0
                        return True
                    
            # 局部快取匹配失敗，累計次數
            self.cache_miss_count += 1
            if self.cache_miss_count >= 3:
                # 連續 3 影格局部快取失效，重置快取並強制退回全域多尺度搜尋
                self.cached_scale = None
                self.cached_team = None
                self.cached_x = None
                self.cached_y = None

        # 3. 快取未命中或已失效時，退回全域多尺度樣板匹配
        atk_val, atk_loc, atk_scale = self._multi_scale_match(search_region, self.tmpl_atk)
        def_val, def_loc, def_scale = self._multi_scale_match(search_region, self.tmpl_def)
        
        if atk_val > def_val and atk_val > 0.8:
            self.cached_scale = atk_scale
            self.cached_team = 'atk'
            self.cached_x = atk_loc[0]
            self.cached_y = atk_loc[1]
            self.cache_miss_count = 0
            return True
        elif def_val > atk_val and def_val > 0.8:
            self.cached_scale = def_scale
            self.cached_team = 'def'
            self.cached_x = def_loc[0]
            self.cached_y = def_loc[1]
            self.cache_miss_count = 0
            return True
            
        # 全域匹配也失敗，重置快取，判定不屬於此戰術階段
        self.cached_scale = None
        self.cached_team = None
        self.cached_x = None
        self.cached_y = None
        self.cache_miss_count = 0
        return False
