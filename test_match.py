import cv2
import numpy as np
import os
import glob
import sys

base_dir = r"c:\Users\eddie\Desktop\Utility\R6Assist"
img_dir = os.path.join(base_dir, "screenshot")
atk_template = os.path.join(img_dir, "temp_atk.png")
def_template = os.path.join(img_dir, "temp_def.png")

# Load templates
tmpl_atk = cv2.imdecode(np.fromfile(atk_template, dtype=np.uint8), cv2.IMREAD_COLOR)
tmpl_def = cv2.imdecode(np.fromfile(def_template, dtype=np.uint8), cv2.IMREAD_COLOR)

print(f"ATK Template Shape: {tmpl_atk.shape if tmpl_atk is not None else 'None'}")
print(f"DEF Template Shape: {tmpl_def.shape if tmpl_def is not None else 'None'}")

# Test on all images
images = glob.glob(os.path.join(img_dir, "*.jpg"))
for img_path in images:
    img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None: continue
        
    print(f"\nImage: {os.path.basename(img_path)} ({img.shape})")
    
    # Matching ATK
    res_atk = cv2.matchTemplate(img, tmpl_atk, cv2.TM_CCOEFF_NORMED)
    min_val_atk, max_val_atk, min_loc_atk, max_loc_atk = cv2.minMaxLoc(res_atk)
    
    # Matching DEF
    res_def = cv2.matchTemplate(img, tmpl_def, cv2.TM_CCOEFF_NORMED)
    min_val_def, max_val_def, min_loc_def, max_loc_def = cv2.minMaxLoc(res_def)
    
    print(f"  ATK Match: Conf={max_val_atk:.4f}, Loc={max_loc_atk}")
    print(f"  DEF Match: Conf={max_val_def:.4f}, Loc={max_loc_def}")
