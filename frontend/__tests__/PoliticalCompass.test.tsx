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
    // economic +0.4 -> 70%, social -0.6 -> 20% (auth is at the TOP of the chart)
    expect(dot.getAttribute("style")).toContain("left: 70%");
    expect(dot.getAttribute("style")).toContain("top: 20%");
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

  it("re-positions dots relative to the provided viewAnchor", () => {
    const usAnchor = {
      id: "us",
      name: "United States median",
      short_name: "US",
      flag: "🇺🇸",
      economic_axis: 0.25,
      social_axis: -0.1,
      description: "Market-leaning",
    };
    renderWith(
      <PoliticalCompass
        analyses={analyses}
        articleBySource={new Map([[reuters.url, reuters]])}
        viewAnchor={usAnchor}
      />
    );

    // econ +0.4 − 0.25 = +0.15 → 57.5%
    // social -0.6 − (-0.1) = -0.5 → 25% (auth-side, top of chart)
    const dot = screen.getByRole("button", { name: /reuters/i });
    expect(dot.getAttribute("style")).toContain("left: 57.49999999999999%");
    expect(dot.getAttribute("style")).toContain("top: 25%");
    // anchor marker is rendered too
    expect(
      screen.getByLabelText(/anchor: united states median/i)
    ).toBeInTheDocument();
  });

  it("does not transform when the anchor is the global baseline", () => {
    const globalAnchor = {
      id: "global",
      name: "Global median",
      short_name: "Global",
      flag: "🌐",
      economic_axis: 0,
      social_axis: 0,
      description: "Baseline",
    };
    renderWith(
      <PoliticalCompass
        analyses={analyses}
        articleBySource={new Map([[reuters.url, reuters]])}
        viewAnchor={globalAnchor}
      />
    );
    const dot = screen.getByRole("button", { name: /reuters/i });
    expect(dot.getAttribute("style")).toContain("left: 70%");
    expect(dot.getAttribute("style")).toContain("top: 20%");
    // no anchor marker when global
    expect(screen.queryByLabelText(/anchor: /i)).not.toBeInTheDocument();
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
    // economic clamped to +1 → 100%, social clamped to -1 → 0% (top = auth)
    expect(dot.style.left).toBe("100%");
    expect(dot.style.top).toBe("0%");
  });
});
