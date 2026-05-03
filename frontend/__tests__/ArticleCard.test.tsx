import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TooltipProvider } from "@/components/ui/tooltip";
import ArticleCard from "@/components/ArticleCard";
import type {
  Article,
  ArticleBiasAnalysis,
} from "@/lib/streamClient";

const article: Article = {
  title: "Philippines files new maritime protest amid South China Sea standoff",
  full_text: "Manila lodged a diplomatic protest with Beijing on Tuesday…",
  url: "https://reuters.com/test-article",
  source_id: "reuters",
  source_name: "Reuters",
  country: "GB",
  published_at: "2026-04-12T10:00:00Z",
  author: "Jane Doe",
  language: "en",
  translated_text: null,
};

const analysis: ArticleBiasAnalysis = {
  article_url: article.url,
  source_id: "reuters",
  overall_bias_direction: "neutral",
  confidence: 0.82,
  framing_analysis: "Uses 'disputed' consistently and presents both perspectives.",
  loaded_terms: ["standoff"],
  omissions: ["Civilian impact statistics"],
  sentiment_score: 0.05,
  attribution_balance: "Quotes Filipino and Chinese officials.",
};

function renderWith(ui: React.ReactNode) {
  return render(<TooltipProvider>{ui}</TooltipProvider>);
}

describe("ArticleCard", () => {
  it("renders headline as a link to the original article opening in a new tab", () => {
    renderWith(<ArticleCard article={article} />);
    const link = screen.getByRole("link", { name: /philippines files/i });
    expect(link).toHaveAttribute("href", article.url);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });

  it("shows source metadata", () => {
    renderWith(<ArticleCard article={article} />);
    expect(screen.getByText("Reuters")).toBeInTheDocument();
    expect(screen.getByText("GB")).toBeInTheDocument();
  });

  it("shows an awaiting state when no analysis is provided", () => {
    renderWith(<ArticleCard article={article} />);
    expect(screen.getByText(/awaiting bias analysis/i)).toBeInTheDocument();
  });

  it("renders bias direction, confidence and loaded terms when analysis is provided", async () => {
    const user = userEvent.setup();
    renderWith(<ArticleCard article={article} analysis={analysis} />);

    expect(screen.getByText("neutral")).toBeInTheDocument();
    expect(screen.getByText("82%")).toBeInTheDocument();

    await user.click(screen.getByText(/why was this flagged/i));
    expect(screen.getByText(/uses 'disputed' consistently/i)).toBeInTheDocument();
    expect(screen.getByText("standoff")).toBeInTheDocument();
    expect(screen.getByText(/civilian impact statistics/i)).toBeInTheDocument();
  });
});
