import time
import os
import cv2
import numpy as np

def run_bench():
    print("Testing original implementation vs optimized...")
    img = np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)
    last_frame = np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)

    # Original
    start_time = time.perf_counter()
    for _ in range(100):
        small_curr = cv2.resize(img, (64, 64))
        small_last = cv2.resize(last_frame, (64, 64))
        diff = cv2.absdiff(small_curr, small_last)
        ans = np.count_nonzero(diff)
    orig_time = time.perf_counter() - start_time

    # Optimized
    start_time = time.perf_counter()
    small_last = cv2.resize(last_frame, (64, 64))
    for _ in range(100):
        small_curr = cv2.resize(img, (64, 64))
        diff = cv2.absdiff(small_curr, small_last)
        ans = np.count_nonzero(diff)
    opt_time = time.perf_counter() - start_time

    print(f"Original: {orig_time:.4f}s")
    print(f"Optimized: {opt_time:.4f}s")
    print(f"Improvement: {(orig_time - opt_time) / orig_time * 100:.2f}%")

if __name__ == '__main__':
    run_bench()
