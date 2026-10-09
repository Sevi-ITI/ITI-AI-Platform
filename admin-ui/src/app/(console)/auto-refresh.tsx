"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

// Asks the server to re-render the page every few seconds (scroll and focus stay), skipped while the
// tab is hidden, and once right away when the tab comes back. "Hidden" is the browser's word: another tab in
// front, or the window minimized (a window merely covered by another one still counts as visible).
// FastAPI doesn't log GET /v1/admin/* calls, so this doesn't fill the request log.
export default function AutoRefresh({ seconds }: { seconds: number }) {
  const router = useRouter();

  useEffect(() => {
    const timer = setInterval(() => {
      if (!document.hidden) {
        router.refresh();
      }
    }, seconds * 1000);
    const onVisible = () => {
      if (!document.hidden) router.refresh();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [router, seconds]);

  return null;
}
