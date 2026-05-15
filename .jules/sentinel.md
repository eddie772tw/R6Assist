## 2026-05-15 - [CORS Overly Permissive Configuration]
**Vulnerability:** The Flask and SocketIO CORS configuration in `api.py` used a wildcard (`*`), allowing any origin to access the API.
**Learning:** Cross-Origin Resource Sharing (CORS) defaults to restrictive, but when manually configured, developers sometimes use wildcards for convenience during development, exposing local APIs to external malicious websites.
**Prevention:** Always restrict CORS explicitly to known and trusted origins (e.g., localhost and specific ports used by the web frontend).
