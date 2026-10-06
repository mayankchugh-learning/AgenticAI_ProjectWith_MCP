// Characterization tests: capture the CURRENT behaviour of RagQATab. The API client is mocked, so
// there is no network, no backend and no API key.
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

vi.mock("@/lib/api", () => ({ askQuestion: vi.fn() }));

import { askQuestion } from "@/lib/api";
import RagQATab from "@/components/RagQATab";

const ask = vi.mocked(askQuestion);
const textbox = () => screen.getByPlaceholderText(/EU import duty rate/) as HTMLTextAreaElement;
const askButton = () => screen.getByRole("button", { name: "Ask" }) as HTMLButtonElement;

beforeEach(() => {
  ask.mockReset();
});

describe("RagQATab (current behaviour)", () => {
  it("starts with an empty history and a disabled Ask button", () => {
    render(<RagQATab />);
    expect(screen.queryByText("No queries yet")).not.toBeNull();
    expect(screen.queryByText("0 queries in this session")).not.toBeNull();
    expect(askButton().disabled).toBe(true);
  });

  it("sends the trimmed text with the default 'similarity' retriever and shows the answer under the 'AI-generated answer' label", async () => {
    ask.mockResolvedValue({ answer: "EUR 2.84 billion" });
    render(<RagQATab />);
    fireEvent.change(textbox(), { target: { value: "  total revenue?  " } });
    fireEvent.click(askButton());

    expect(await screen.findByText("EUR 2.84 billion")).not.toBeNull();
    expect(ask).toHaveBeenCalledTimes(1);
    expect(ask).toHaveBeenCalledWith("total revenue?", "similarity");
    // Q5: the label used to be "Verified Answer", which overstated how trustworthy a model answer is.
    expect(screen.queryByText("AI-generated answer")).not.toBeNull();
    expect(screen.queryByText("Verified Answer")).toBeNull();
    expect(screen.queryByText("1 queries in this session")).not.toBeNull();
    expect(textbox().value).toBe("");
  });

  it("passes the selected retrieval strategy to the API", async () => {
    ask.mockResolvedValue({ answer: "ok" });
    render(<RagQATab />);
    fireEvent.click(screen.getByRole("button", { name: "Multi-Query" }));
    fireEvent.change(textbox(), { target: { value: "q" } });
    fireEvent.click(askButton());
    await screen.findByText("ok");
    expect(ask).toHaveBeenCalledWith("q", "multiquery");
  });

  it("sends an example query immediately when it is clicked", async () => {
    ask.mockResolvedValue({ answer: "Net-45" });
    render(<RagQATab />);
    const example = "What are the standard payment terms for servo motor suppliers?";
    fireEvent.click(screen.getByText(example));
    await screen.findByText("Net-45");
    expect(ask).toHaveBeenCalledWith(example, "similarity");
  });

  it("shows the error message and no answer label when the request fails", async () => {
    ask.mockRejectedValue(new Error("backend exploded"));
    render(<RagQATab />);
    fireEvent.change(textbox(), { target: { value: "q" } });
    fireEvent.click(askButton());

    expect(await screen.findByText("backend exploded")).not.toBeNull();
    expect(screen.queryByText("Error Encountered")).not.toBeNull();
    expect(screen.queryByText("AI-generated answer")).toBeNull();
  });

  it("does not send whitespace-only input", () => {
    render(<RagQATab />);
    fireEvent.change(textbox(), { target: { value: "   " } });
    expect(askButton().disabled).toBe(true);
    fireEvent.keyDown(textbox(), { key: "Enter" });
    expect(ask).not.toHaveBeenCalled();
  });

  it("Enter sends and Shift+Enter does not", async () => {
    ask.mockResolvedValue({ answer: "done" });
    render(<RagQATab />);
    fireEvent.change(textbox(), { target: { value: "hello" } });
    fireEvent.keyDown(textbox(), { key: "Enter", shiftKey: true });
    expect(ask).not.toHaveBeenCalled();
    fireEvent.keyDown(textbox(), { key: "Enter" });
    await screen.findByText("done");
    expect(ask).toHaveBeenCalledTimes(1);
  });

  it("shows a waiting state while the request is pending and blocks a second send", () => {
    ask.mockReturnValue(new Promise(() => {}));
    render(<RagQATab />);
    fireEvent.change(textbox(), { target: { value: "slow" } });
    fireEvent.click(askButton());
    expect(screen.queryByText("Thinking…")).not.toBeNull();
    expect(screen.queryByText(/synthesising context/)).not.toBeNull();
    fireEvent.change(textbox(), { target: { value: "again" } });
    fireEvent.keyDown(textbox(), { key: "Enter" });
    expect(ask).toHaveBeenCalledTimes(1);
  });

  it("Clear History empties the list", async () => {
    ask.mockResolvedValue({ answer: "a1" });
    render(<RagQATab />);
    fireEvent.change(textbox(), { target: { value: "q" } });
    fireEvent.click(askButton());
    await screen.findByText("a1");
    fireEvent.click(screen.getByRole("button", { name: /Clear History/ }));
    await waitFor(() => expect(screen.queryByText("No queries yet")).not.toBeNull());
    expect(screen.queryByText("a1")).toBeNull();
  });
});
