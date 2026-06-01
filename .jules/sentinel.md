## 2024-05-19 - [HIGH] Restrict local API network binding and CORS policy
**Vulnerability:** The local Flask-SocketIO backend was binding to `0.0.0.0` and using wildcard CORS `*`, exposing the API and screen capture capabilities to the entire local network.
**Learning:** For a local desktop application with a decoupled web UI, backend APIs (Flask/SocketIO) must explicitly bind to `127.0.0.1` and use strict CORS policies limited to the local frontend port, rather than `0.0.0.0` or wildcard origins.
**Prevention:** Always verify network binding in local applications and explicitly load configuration ports to build strict `allowed_origins` for CORS and WebSocket connections.

## 2024-05-20 - [MEDIUM] Securely expose local API for cross-device access
**Vulnerability:** Hardcoded `localhost` bindings restrict cross-device functionality (e.g. tablet usage) on the same LAN.
**Learning:** To maintain security while supporting local network cross-device access, backend APIs (Flask/SocketIO) must bind to `0.0.0.0` and use regex-based CORS policies strictly matching local IP ranges (localhost, 192.168.x.x, 10.x.x.x, etc.) rather than using wildcard `*`.
**Prevention:** Use dynamic frontend URLs (`window.location.hostname`) and regex-based backend CORS validation when exposing services to the local area network.

## 2026-06-01 - [HIGH] Enforce strict CORS on WebSocket connections
**Vulnerability:** The Flask-SocketIO initialization used a wildcard (`*`) for `cors_allowed_origins` while regular Flask routes used a regex for strict cross-device local access, exposing the WebSocket screen capture stream to any origin.
**Learning:** While Flask-CORS natively supports passing a compiled regex object directly to `origins`, Flask-SocketIO (engineio) requires a callable function for regex evaluation (e.g., `lambda origin: bool(regex.match(origin))`). Passing a regex object directly to Flask-SocketIO results in a TypeError during connection.
**Prevention:** Always ensure both standard HTTP routes (via Flask-CORS) and WebSocket endpoints (via Flask-SocketIO) share the same strict, regex-based CORS validation when exposing services, ensuring the correct data type is used for each library.
