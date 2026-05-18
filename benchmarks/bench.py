import cv2
import numpy as np
import time

def bench_original(img, last_frame, iters=1000):
    start = time.time()
    for _ in range(iters):
        small_curr = cv2.resize(img, (64, 64))
        small_last = cv2.resize(last_frame, (64, 64))
        diff = cv2.absdiff(small_curr, small_last)
        ans = np.count_nonzero(diff)
    return time.time() - start

def bench_optimized(img, small_last, iters=1000):
    start = time.time()
    for _ in range(iters):
        small_curr = cv2.resize(img, (64, 64))
        diff = cv2.absdiff(small_curr, small_last)
        ans = np.count_nonzero(diff)
    return time.time() - start

img = np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)
last_frame = np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)
small_last = cv2.resize(last_frame, (64, 64))

orig = bench_original(img, last_frame, 1000)
opt = bench_optimized(img, small_last, 1000)

print(f"Original: {orig:.4f}s")
print(f"Optimized: {opt:.4f}s")
print(f"Improvement: {(orig - opt) / orig * 100:.2f}%")
