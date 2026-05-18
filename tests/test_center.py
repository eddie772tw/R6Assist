import cv2
import numpy as np
import os
import glob

base_dir = r"c:\Users\eddie\Desktop\Utility\R6Assist"
img_dir = os.path.join(base_dir, "screenshot")
center_template = os.path.join(img_dir, "temp_center.png")
tmpl_center = cv2.imdecode(np.fromfile(center_template, dtype=np.uint8), cv2.IMREAD_COLOR)
print(f"Center Template Shape: {tmpl_center.shape if tmpl_center is not None else 'None'}")

def multi_scale_match(img, template):
    best_max_val = -1
    best_loc = None
    best_scale = 1.0
    for scale in np.linspace(0.5, 2.0, 16):
        resized = cv2.resize(template, (0,0), fx=scale, fy=scale)
        if resized.shape[0] > img.shape[0] or resized.shape[1] > img.shape[1]:
            break
        res = cv2.matchTemplate(img, resized, cv2.TM_CCOEFF_NORMED)
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
    
    val, loc, scale = multi_scale_match(img, tmpl_center)
    print(f"Image: {os.path.basename(img_path)} -> Center Conf: {val:.4f}, Loc: {loc}, Scale: {scale:.2f}")
