// Characterization tests: capture the CURRENT behaviour of AuditTab. The API client is mocked, so
// there is no network, no backend and no API key.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";

vi.mock("@/lib/api", () => ({ runAudit: vi.fn() }));

import { runAudit } from "@/lib/api";
import AuditTab from "@/components/AuditTab";

const audit = vi.mocked(runAudit);
const textbox = () => screen.getByPlaceholderText("Describe the procurement request…") as HTMLTextAreaElement;
const executeButton = () => screen.getByRole("button", { name: /Execute Audit/ }) as HTMLButtonElement;

const RESULT = {
  risk_result: "RISK-REPORT",
  tax_result: "TAX-REPORT",
  control_result: "CONTROL-REPORT",
  cfo_memo: "MEMO: FINAL DECISION: REJECTED",
};

beforeEach(() => {
  audit.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("AuditTab (current behaviour)", () => {
  it("is pre-filled with the sample request and sends exactly the textarea text", () => {
    audit.mockReturnValue(new Promise(() => {}));
    render(<AuditTab />);
    expect(textbox().value).toContain("Takumi Controls Europe B.V.");
    fireEvent.click(executeButton());
    expect(audit).toHaveBeenCalledTimes(1);
    expect(audit).toHaveBeenCalledWith(textbox().value);
  });

  it("does not run with an empty request", () => {
    render(<AuditTab />);
    fireEvent.change(textbox(), { target: { value: "   " } });
    expect(executeButton().disabled).toBe(true);
    fireEvent.click(executeButton());
    expect(audit).not.toHaveBeenCalled();
  });

  it("on success shows all four phases done and the memo, without an 'All Passed' claim", async () => {
    audit.mockResolvedValue(RESULT);
    render(<AuditTab />);
    fireEvent.click(executeButton());

    expect((await screen.findAllByText(RESULT.cfo_memo)).length).toBeGreaterThan(0);
    expect(screen.queryByText("4/4")).not.toBeNull();
    // Q5: the footer used to say "All Passed" even when the memo's decision was REJECTED (as in RESULT).
    expect(screen.queryByText("All Passed")).toBeNull();
    expect(screen.getAllByText("Complete").length).toBeGreaterThan(0);
  });

  it("on failure shows the error and no memo or footer", async () => {
    audit.mockRejectedValue(new Error("Audit exploded"));
    render(<AuditTab />);
    fireEvent.click(executeButton());

    expect(await screen.findByText("Audit exploded")).not.toBeNull();
    expect(screen.queryByText("Audit Failed")).not.toBeNull();
    expect(screen.queryByText("All Passed")).toBeNull();
    expect(screen.queryByText("4/4")).toBeNull();
  });

  it("Reset restores the sample request and clears the pipeline", async () => {
    audit.mockResolvedValue(RESULT);
    render(<AuditTab />);
    fireEvent.change(textbox(), { target: { value: "custom" } });
    fireEvent.click(executeButton());
    await screen.findByText("4/4");
    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    expect(textbox().value).toContain("Takumi Controls Europe B.V.");
    expect(screen.queryByText("4/4")).toBeNull();
  });

  it("does not show invented progress while the request is pending, and completes all phases only when the response arrives", async () => {
    vi.useFakeTimers();
    let resolve!: (value: typeof RESULT) => void;
    audit.mockReturnValue(new Promise<typeof RESULT>((r) => { resolve = r; }));
    render(<AuditTab />);
    fireEvent.click(executeButton());

    // Q5: phases used to flip to running/done on client timers at 3s, 6s and 9s. They now stay pending.
    expect(screen.queryByText("0/4")).not.toBeNull();
    expect(screen.queryAllByText("Processing…").length).toBe(0);
    for (const _ of [1, 2, 3]) {
      act(() => { vi.advanceTimersByTime(3000); });
      expect(screen.queryByText("0/4")).not.toBeNull();
      expect(screen.queryAllByText("Processing…").length).toBe(0);
    }

    await act(async () => { resolve(RESULT); });
    expect(screen.queryByText("4/4")).not.toBeNull();
  });
});
