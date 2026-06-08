import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { PoliticalCompass } from "@/components/PoliticalCompass";
import { MiniCompass } from "@/components/MiniCompass";
import type {
  Article,
  ArticleBiasAnalysis,
  PoliticalCompassPoint,
} from "@/lib/streamClient";

const compass: PoliticalCompassPoint = {
  economic_axis: 0.4,
  social_axis: -0.6,
  regional_context: "Tends fiscally liberal, socially conservative in EU context.",
  label: "Auth · Right",
  confidence: 0.78,
};

const reuters: Article = {
  title: "Reuters headline",
  full_text: "body",
  url: "https://reuters.com/a",
  source_id: "reuters",
  source_name: "Reuters",
  country: "GB",
  published_at: "2026-04-12T10:00:00Z",
  author: null,
  language: "en",
  translated_text: null,
};

const analyses: ArticleBiasAnalysis[] = [
  {
    article_url: reuters.url,
    source_id: "reuters",
    overall_bias_direction: "pro-Western",
    confidence: 0.82,
    framing_analysis: "Balanced.",
    loaded_terms: [],
    omissions: [],
    sentiment_score: 0.0,
    attribution_balance: "balanced",
    political_compass: compass,
  },
];

function renderWith(ui: React.ReactNode) {
  return render(<TooltipProvider>{ui}</TooltipProvider>);
}

describe("PoliticalCompass", () => {
  it("renders a dot for each source with compass data", () => {
    renderWith(
      <PoliticalCompass
        analyses={analyses}
        articleBySource={new Map([[reuters.url, reuters]])}
      />
    );

    const dot = screen.getByRole("button", { name: /reuters/i });
    expect(dot).toBeInTheDocument();
  });

  it("renders an empty state when no analyses include compass data", () => {
    renderWith(
      <PoliticalCompass
        analyses={[{ ...analyses[0], political_compass: null }]}
        articleBySource={new Map([[reuters.url, reuters]])}
      />
    );

    expect(
      screen.getByText(/no political-compass data/i)
    ).toBeInTheDocument();
  });

  it("places the dot at the expected percentage on both axes", () => {
    renderWith(
      <PoliticalCompass
        analyses={analyses}
        articleBySource={new Map([[reuters.url, reuters]])}
      />
    );

    const dot = screen.getByRole("button", { name: /reuters/i });
    // economic +0.4 -> 70%, social -0.6 -> 80% (because auth=top)
    expect(dot.getAttribute("style")).toContain("left: 70%");
    expect(dot.getAttribute("style")).toContain("top: 80%");
  });

  it("lists the source in the side legend", () => {
    renderWith(
      <PoliticalCompass
        analyses={analyses}
        articleBySource={new Map([[reuters.url, reuters]])}
      />
    );
    expect(screen.getAllByText(/reuters/i).length).toBeGreaterThan(0);
    expect(screen.getByText("+0.4, -0.6")).toBeInTheDocument();
  });
});

describe("MiniCompass", () => {
  it("renders an accessible label derived from the compass label", () => {
    renderWith(<MiniCompass compass={compass} />);
    expect(
      screen.getByLabelText(/political compass.*auth.*right/i)
    ).toBeInTheDocument();
  });

  it("clamps and positions the dot inside the grid", () => {
    renderWith(
      <MiniCompass
        compass={{ ...compass, economic_axis: 2, social_axis: -2 }}
      />
    );
    const grid = screen.getByLabelText(/political compass/i);
    const dot = grid.querySelector("span:last-child") as HTMLElement;
    // economic clamped to +1 → 100%, social clamped to -1 → 100% (top)
    expect(dot.style.left).toBe("100%");
    expect(dot.style.top).toBe("100%");
  });
});
