## 2024-03-24 - Frame caching optimization in image capture loops
**Learning:** In real-time screen capture loops (e.g. `monitor.py` and `api.py`), copying the entire full-resolution frame `img.copy()` into memory and then redundantly resizing that previous frame to 64x64 during *every* iteration to check for differences is a severe performance and memory bottleneck.
**Action:** When comparing current frames against previous frames for motion detection or screen updates, cache the heavily downscaled thumbnail representation (`small_curr`) instead of the full raw image. `cv2.resize` allocates a new numpy array, so passing the reference directly is safe and entirely removes the need for `.copy()`.

## 2025-02-23 - [O(1) Operator Lookup]
**Learning:** Found that `TacticalAdvisor` performs an O(N) iteration over database keys to do a case-insensitive match every time a mismatch happens. For an application matching 79 operators continuously, this is an unnecessary overhead.
**Action:** Pre-compute a case-insensitive map (`_name_map`) during database loading to turn case-insensitive lookups from O(N) into O(1).
