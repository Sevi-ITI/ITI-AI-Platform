"""INGEST_LOCK: only one document is embedded at a time, so uploads never starve chat of the GPU."""

import threading

INGEST_LOCK = threading.Lock()
