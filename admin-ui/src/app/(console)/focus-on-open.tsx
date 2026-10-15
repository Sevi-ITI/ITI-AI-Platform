"use client";

import { useEffect } from "react";

// Moves keyboard focus to an element when it appears (a details panel's heading), so keyboard and screen reader users
// land in it. preventScroll: a sticky panel's own place is the top of the page, and plain autoFocus scrolled there.
export default function FocusOnOpen({ targetId }: { targetId: string }) {
  useEffect(() => {
    document.getElementById(targetId)?.focus({ preventScroll: true });
  }, [targetId]);
  return null;
}
