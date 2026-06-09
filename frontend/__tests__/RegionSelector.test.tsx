import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TooltipProvider } from "@/components/ui/tooltip";
import { RegionSelector } from "@/components/RegionSelector";
import type { RegionalAnchor } from "@/lib/streamClient";

const anchors: RegionalAnchor[] = [
  {
    id: "global",
    name: "Global median",
    short_name: "Global",
    flag: "🌐",
    economic_axis: 0,
    social_axis: 0,
    description: "Baseline",
  },
  {
    id: "us",
    name: "United States median",
    short_name: "US",
    flag: "🇺🇸",
    economic_axis: 0.25,
    social_axis: -0.1,
    description: "Market-leaning",
  },
];

function renderWith(ui: React.ReactNode) {
  return render(<TooltipProvider>{ui}</TooltipProvider>);
}

describe("RegionSelector", () => {
  it("renders one radio button per anchor with the selected one aria-checked", () => {
    renderWith(
      <RegionSelector
        anchors={anchors}
        selectedId="us"
        onChange={vi.fn()}
      />
    );
    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(2);
    expect(
      screen.getByRole("radio", { name: /us/i })
    ).toHaveAttribute("aria-checked", "true");
    expect(
      screen.getByRole("radio", { name: /global/i })
    ).toHaveAttribute("aria-checked", "false");
  });

  it("calls onChange with the clicked anchor id", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    renderWith(
      <RegionSelector
        anchors={anchors}
        selectedId="global"
        onChange={onChange}
      />
    );
    await user.click(screen.getByRole("radio", { name: /us/i }));
    expect(onChange).toHaveBeenCalledWith("us");
  });

  it("renders nothing when no anchors are provided", () => {
    const { container } = renderWith(
      <RegionSelector
        anchors={[]}
        selectedId="global"
        onChange={vi.fn()}
      />
    );
    expect(container).toBeEmptyDOMElement();
  });
});
