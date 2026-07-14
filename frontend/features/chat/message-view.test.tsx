import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  MessageView,
  PartRenderer,
  PartShell,
} from "@/features/chat/message-view";
import type { ConversationMessage, MessagePart } from "@/features/chat/types";

describe("MessageView", () => {
  it("renders message header with agent id", () => {
    const message: ConversationMessage = {
      id: "m1",
      role: "assistant",
      agentId: "research_understanding",
      parts: [{ type: "text", id: "p1", text: "hello" }],
      status: "completed",
    };
    render(<MessageView message={message} />);
    expect(screen.getByText("research_understanding")).toBeVisible();
    expect(screen.getByText("hello")).toBeVisible();
  });

  it("shows streaming indicator while message is streaming", () => {
    const message: ConversationMessage = {
      id: "m1",
      role: "assistant",
      parts: [{ type: "text", id: "p1", text: "partial" }],
      status: "streaming",
    };
    render(<MessageView message={message} />);
    expect(screen.getByText("working…")).toBeVisible();
  });

  it("uses 'You' as agent for user role", () => {
    const message: ConversationMessage = {
      id: "m1",
      role: "user",
      parts: [{ type: "text", id: "p1", text: "what is this?" }],
      status: "completed",
    };
    render(<MessageView message={message} />);
    expect(screen.getByText("You")).toBeVisible();
  });
});

describe("PartRenderer", () => {
  it("renders text parts as plain paragraphs", () => {
    const part: MessagePart = { type: "text", id: "p1", text: "hi" };
    render(<PartRenderer part={part} />);
    expect(screen.getByText("hi")).toBeVisible();
  });

  it("renders error parts with title and detail", () => {
    const part: MessagePart = {
      type: "error",
      id: "p1",
      title: "Bad input",
      detail: "patch invalid",
    };
    render(<PartRenderer part={part} />);
    expect(screen.getByText("Bad input")).toBeVisible();
    expect(screen.getByText("patch invalid")).toBeVisible();
  });

  it("renders artifact parts with name", () => {
    const part: MessagePart = {
      type: "artifact",
      id: "p1",
      artifactId: "a1",
      name: "plan.md",
    };
    render(<PartRenderer part={part} />);
    expect(screen.getByText("plan.md")).toBeVisible();
  });
});

describe("PartShell", () => {
  it("renders with tone class", () => {
    render(
      <PartShell icon={() => null} label="Tool call" tone="neutral">
        body
      </PartShell>,
    );
    expect(screen.getByText("Tool call")).toBeVisible();
    expect(screen.getByText("body")).toBeVisible();
  });
});
