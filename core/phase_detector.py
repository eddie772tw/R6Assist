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

    def _load_template(self, path):
        if os.path.exists(path):
            img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
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

        # Crop top half to speed up
        search_region = img[0:img.shape[0]//2, 0:img.shape[1]]
        
        # Check cache first
        if self.cached_scale and self.cached_team in ['atk', 'def']:
            template = self.tmpl_atk if self.cached_team == 'atk' else self.tmpl_def
            if template is not None:
                resized = cv2.resize(template, (0,0), fx=self.cached_scale, fy=self.cached_scale)
                if resized.shape[0] <= search_region.shape[0] and resized.shape[1] <= search_region.shape[1]:
                    res = cv2.matchTemplate(search_region, resized, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(res)
                    if max_val > 0.8:
                        return True

        atk_val, _, atk_scale = self._multi_scale_match(search_region, self.tmpl_atk)
        def_val, _, def_scale = self._multi_scale_match(search_region, self.tmpl_def)
        
        if atk_val > def_val and atk_val > 0.8:
            self.cached_scale = atk_scale
            self.cached_team = 'atk'
            return True
        elif def_val > atk_val and def_val > 0.8:
            self.cached_scale = def_scale
            self.cached_team = 'def'
            return True
            
        self.cached_scale = None
        self.cached_team = None
        return False
