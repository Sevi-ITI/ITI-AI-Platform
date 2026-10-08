"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

// Asks the server to re-render the page every few seconds (scroll and focus stay), skipped while the
// tab is hidden. FastAPI doesn't log GET /v1/admin/* calls, so this doesn't fill the request log.
export default function AutoRefresh({ seconds }: { seconds: number }) {
  const router = useRouter();

  useEffect(() => {
    const timer = setInterval(() => {
      if (!document.hidden) {
        router.refresh();
      }
    }, seconds * 1000);
    return () => clearInterval(timer);
  }, [router, seconds]);

  return null;
}
