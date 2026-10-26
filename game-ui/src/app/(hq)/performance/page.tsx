import type { Metadata } from "next";

import { testersGoToChat } from "@/lib/session/testers-go-to-chat";

import RoomPlaceholder from "../room-placeholder";

export const metadata: Metadata = { title: "Performance" };

// The Performance room: a placeholder until its data is wired in (G3 onward).
export default async function PerformanceRoom() {
  await testersGoToChat();
  return <RoomPlaceholder />;
}
