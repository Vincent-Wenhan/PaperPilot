import { describe, expect, it } from "vitest";

import {
  type ConversationMessage,
  type MessagePart,
} from "@/features/chat/types";

function makeMessage(parts: MessagePart[]): ConversationMessage {
  return {
    id: "m1",
    role: "assistant",
    agentId: "research_understanding",
    parts,
    status: "completed",
  };
}

describe("MessagePart type system", () => {
  it("treats each part variant as a valid MessagePart", () => {
    const parts: MessagePart[] = [
      { type: "text", id: "p1", text: "hello" },
      { type: "reasoning-summary", id: "p2", text: "thinking" },
      { type: "tool", id: "p3", toolCallId: "tc1" },
      { type: "artifact", id: "p4", artifactId: "a1", name: "plan.md" },
      { type: "plan-review", id: "p5", interruptId: "i1" },
      { type: "status", id: "p6", label: "Running", status: "running" },
      { type: "error", id: "p7", title: "Bad input", detail: "patch invalid" },
    ];
    const message = makeMessage(parts);
    expect(message.parts).toHaveLength(7);
    expect(message.parts[0]).toMatchObject({ type: "text", text: "hello" });
    expect(message.parts[6]).toMatchObject({
      type: "error",
      title: "Bad input",
      detail: "patch invalid",
    });
  });

  it("keeps streaming state separate from part content", () => {
    const streaming = makeMessage([
      { type: "text", id: "p1", text: "partial" },
    ]);
    streaming.status = "streaming";
    expect(streaming.status).toBe("streaming");
    expect(streaming.parts[0]).toMatchObject({ type: "text", text: "partial" });
  });

  it("supports assistant, user and system roles", () => {
    const user = makeMessage([]);
    user.role = "user";
    const system = makeMessage([]);
    system.role = "system";
    expect(user.role).toBe("user");
    expect(system.role).toBe("system");
  });
});
