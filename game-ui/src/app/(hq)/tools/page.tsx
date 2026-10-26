import type { Metadata } from "next";

import { testersGoToChat } from "@/lib/session/testers-go-to-chat";

import RoomPlaceholder from "../room-placeholder";

export const metadata: Metadata = { title: "Tools & MCP" };

// The Tools & MCP room: a placeholder until its data is wired in (G3 onward).
export default async function ToolsRoom() {
  await testersGoToChat();
  return <RoomPlaceholder />;
}
