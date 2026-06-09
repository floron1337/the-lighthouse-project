import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TooltipProvider } from "@/components/ui/tooltip";
import { LegendDialog } from "@/components/LegendDialog";

function renderLegend() {
  return render(
    <TooltipProvider>
      <LegendDialog />
    </TooltipProvider>
  );
}

describe("LegendDialog", () => {
  it("renders a trigger button labelled 'Legend'", () => {
    renderLegend();
    expect(
      screen.getByRole("button", { name: /legend/i })
    ).toBeInTheDocument();
  });

  it("opens a dialog with the indicator sections when the trigger is clicked", async () => {
    const user = userEvent.setup();
    renderLegend();

    // Dialog content not in the DOM until opened.
    expect(
      screen.queryByRole("dialog")
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /legend/i }));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(
      screen.getByText(/what the indicators mean/i)
    ).toBeInTheDocument();
    // Section headers
    expect(screen.getByText(/bias direction/i)).toBeInTheDocument();
    expect(screen.getByText(/^confidence$/i)).toBeInTheDocument();
    expect(screen.getByText(/^sentiment$/i)).toBeInTheDocument();
    expect(screen.getByText(/loaded terms/i)).toBeInTheDocument();
    expect(screen.getByText(/possible omissions/i)).toBeInTheDocument();
    expect(screen.getByText(/region perspective/i)).toBeInTheDocument();
  });

  it("lists every bias-direction badge by name", async () => {
    const user = userEvent.setup();
    renderLegend();
    await user.click(screen.getByRole("button", { name: /legend/i }));

    for (const label of [
      "pro-Western",
      "pro-BRICS",
      "pro-government",
      "neutral",
      "mixed",
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("closes when the close button is clicked", async () => {
    const user = userEvent.setup();
    renderLegend();
    await user.click(screen.getByRole("button", { name: /legend/i }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /close/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
