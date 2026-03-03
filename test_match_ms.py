import cv2
import numpy as np
import os
import glob

base_dir = r"c:\Users\eddie\Desktop\Utility\R6Assist"
img_dir = os.path.join(base_dir, "screenshot")
atk_template = os.path.join(img_dir, "temp_atk.png")
def_template = os.path.join(img_dir, "temp_def.png")

tmpl_atk = cv2.imdecode(np.fromfile(atk_template, dtype=np.uint8), cv2.IMREAD_COLOR)
tmpl_def = cv2.imdecode(np.fromfile(def_template, dtype=np.uint8), cv2.IMREAD_COLOR)

def multi_scale_match(img, template):
    best_max_val = -1
    best_loc = None
    best_scale = 1.0
    # Test scales from 0.5 to 1.5
    for scale in np.linspace(0.5, 2.0, 16):
        resized_template = cv2.resize(template, (0,0), fx=scale, fy=scale)
        if resized_template.shape[0] > img.shape[0] or resized_template.shape[1] > img.shape[1]:
            break
        res = cv2.matchTemplate(img, resized_template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val > best_max_val:
            best_max_val = max_val
            best_loc = max_loc
            best_scale = scale
    return best_max_val, best_loc, best_scale

images = glob.glob(os.path.join(img_dir, "*.jpg"))
for img_path in images:
    img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None: continue
    
    # Crop top half of the screen as the icon is usually at the top, to speed up and reduce false positives
    # Or just use the whole screen
    search_region = img[0:img.shape[0]//2, 0:img.shape[1]]
        
    print(f"\nImage: {os.path.basename(img_path)}")
    atk_val, atk_loc, atk_scale = multi_scale_match(search_region, tmpl_atk)
    def_val, def_loc, def_scale = multi_scale_match(search_region, tmpl_def)
    
    print(f"  ATK => Conf: {atk_val:.4f}, Loc: {atk_loc}, Scale: {atk_scale:.2f}")
    print(f"  DEF => Conf: {def_val:.4f}, Loc: {def_loc}, Scale: {def_scale:.2f}")
    if atk_val > def_val and atk_val > 0.7:
        print("  => Detected: ATK")
    elif def_val > atk_val and def_val > 0.7:
        print("  => Detected: DEF")
    else:
        print("  => Detected: None")
