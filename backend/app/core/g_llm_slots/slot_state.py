"""SlotState: how many answers may be generated at once, how many are running, how many wait.

Why our own queue when Ollama also queues: we can (1) measure the wait and show it on the
monitoring page, (2) refuse with 503 llm_busy after a timeout instead of letting requests pile up,
(3) report "2 running, 3 waiting" on the health page."""

import threading


class SlotState:
    def __init__(self, limit: int):
        self.limit = limit
        self.semaphore = threading.BoundedSemaphore(limit)
        self.lock = threading.Lock()
        self.running = 0
        self.waiting = 0