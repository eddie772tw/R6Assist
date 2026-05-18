import cv2
import numpy as np
import time

def benchmark(iterations=1000):
    img = np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)
    last_frame = np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)

    # Method 1: Resize last_frame in loop
    start = time.time()
    for _ in range(iterations):
        small_curr = cv2.resize(img, (64, 64))
        small_last = cv2.resize(last_frame, (64, 64))
        diff = cv2.absdiff(small_curr, small_last)
        non_zero_count = np.count_nonzero(diff)
    end = time.time()
    print(f"Method 1 (current) time: {end - start:.4f}s")

    # Method 2: Cache small_last
    start = time.time()
    last_small_frame = cv2.resize(last_frame, (64, 64))
    for _ in range(iterations):
        small_curr = cv2.resize(img, (64, 64))
        small_last = last_small_frame
        diff = cv2.absdiff(small_curr, small_last)
        non_zero_count = np.count_nonzero(diff)
    end = time.time()
    print(f"Method 2 (proposed) time: {end - start:.4f}s")

benchmark()
