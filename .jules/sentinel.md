## 2024-05-19 - [HIGH] Restrict local API network binding and CORS policy
**Vulnerability:** The local Flask-SocketIO backend was binding to `0.0.0.0` and using wildcard CORS `*`, exposing the API and screen capture capabilities to the entire local network.
**Learning:** For a local desktop application with a decoupled web UI, backend APIs (Flask/SocketIO) must explicitly bind to `127.0.0.1` and use strict CORS policies limited to the local frontend port, rather than `0.0.0.0` or wildcard origins.
**Prevention:** Always verify network binding in local applications and explicitly load configuration ports to build strict `allowed_origins` for CORS and WebSocket connections.
