// Splits Server-Sent Events text (FastAPI's /v1/chat/stream, passed through /api/chat) into events.
// The network delivers the stream in arbitrary pieces, so whatever comes after the last blank line is an
// unfinished event: it is returned as `rest` and joined with the next piece.

export type SseEvent = { event: string; data: string };

export function parseSse(buffer: string): { events: SseEvent[]; rest: string } {
  const blocks = buffer.replace(/\r\n/g, "\n").split("\n\n");
  const rest = blocks.pop() ?? "";
  const events: SseEvent[] = [];

  for (const block of blocks) {
    let event = "message";
    const data: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
    }
    if (data.length > 0) events.push({ event, data: data.join("\n") });
  }
  return { events, rest };
}
