import * as React from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RegionMap from "@/components/RegionMap";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Article } from "@/lib/streamClient";

vi.mock("react-simple-maps", () => ({
  ComposableMap: ({ children }: { children: React.ReactNode }) => (
    <svg>{children}</svg>
  ),
  Geographies: ({
    children,
  }: {
    children: (args: {
      geographies: Array<Record<string, unknown>>;
    }) => React.ReactNode;
  }) => (
    <g>
      {children({
        geographies: [
          {
            id: "840",
            rsmKey: "usa",
            properties: { name: "United States" },
          },
          {
            id: "250",
            rsmKey: "france",
            properties: { name: "France" },
          },
        ],
      })}
    </g>
  ),
  Geography: React.forwardRef<
    SVGPathElement,
    {
      geography: { id: string };
      onClick?: React.MouseEventHandler<SVGPathElement>;
      style?: { hover?: { cursor?: string } };
    } & React.SVGProps<SVGPathElement>
  >(({ geography, onClick, style, ...props }, ref) => (
    <path
      ref={ref}
      data-testid={`country-${geography.id}`}
      onClick={onClick}
      style={{ cursor: style?.hover?.cursor }}
      {...props}
    />
  )),
}));

const articles: Article[] = [
  {
    title: "Story",
    full_text: "Full text",
    url: "https://example.com/story",
    source_id: "reuters",
    source_name: "Reuters",
    country: "US",
    published_at: "2026-01-01T00:00:00Z",
    author: null,
    language: "en",
    translated_text: null,
  },
];

function renderMap(onCountryClick = vi.fn()) {
  render(
    <TooltipProvider delayDuration={0}>
      <RegionMap
        articles={articles}
        selectedCountry={null}
        onCountryClick={onCountryClick}
      />
    </TooltipProvider>
  );
  return { onCountryClick };
}

describe("RegionMap", () => {
  it("keeps countries with sources clickable", async () => {
    const user = userEvent.setup();
    const { onCountryClick } = renderMap();

    const usa = screen.getByTestId("country-840");
    await user.click(usa);

    expect(usa).toHaveAttribute("data-has-news-sources", "true");
    expect(onCountryClick).toHaveBeenCalledWith("US");
  });

  it("keeps hover details for countries without sources but disables click", async () => {
    const user = userEvent.setup();
    const { onCountryClick } = renderMap();

    const france = screen.getByTestId("country-250");
    await user.hover(france);
    expect(
      await screen.findAllByText("No news sources for this query")
    ).not.toHaveLength(0);
    await user.click(france);

    expect(france).toHaveAttribute("data-has-news-sources", "false");
    expect(france).toHaveAttribute("aria-disabled", "true");
    expect(onCountryClick).not.toHaveBeenCalled();
  });
});
