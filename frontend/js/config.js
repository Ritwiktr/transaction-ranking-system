// Uses same origin when served by FastAPI; falls back to localhost for separate static hosting.
window.API_BASE_URL = window.API_BASE_URL || window.location.origin;
