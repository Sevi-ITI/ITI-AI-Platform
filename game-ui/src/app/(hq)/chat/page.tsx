import type { Metadata } from "next";

import RoomPlaceholder from "../room-placeholder";

export const metadata: Metadata = { title: "Chat" };

// The Chat room: a placeholder until its data is wired in (G3 onward).
export default function ChatRoom() {
  return <RoomPlaceholder />;
}
