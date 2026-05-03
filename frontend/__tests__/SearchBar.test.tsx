import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SearchBar from "@/components/SearchBar";

describe("SearchBar", () => {
  it("renders the input and submit button", () => {
    render(<SearchBar onSearch={vi.fn()} />);
    expect(screen.getByRole("textbox", { name: /news topic/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /analyze/i })).toBeInTheDocument();
  });

  it("calls onSearch with the trimmed query on submit", async () => {
    const onSearch = vi.fn();
    const user = userEvent.setup();
    render(<SearchBar onSearch={onSearch} />);

    await user.type(
      screen.getByRole("textbox", { name: /news topic/i }),
      "  EU AI Act  "
    );
    await user.click(screen.getByRole("button", { name: /analyze/i }));

    expect(onSearch).toHaveBeenCalledTimes(1);
    expect(onSearch).toHaveBeenCalledWith("EU AI Act");
  });

  it("does not submit empty queries", async () => {
    const onSearch = vi.fn();
    const user = userEvent.setup();
    render(<SearchBar onSearch={onSearch} />);

    await user.click(screen.getByRole("button", { name: /analyze/i }));
    expect(onSearch).not.toHaveBeenCalled();
  });

  it("disables the input and button while a search is running", () => {
    render(<SearchBar onSearch={vi.fn()} disabled />);
    expect(screen.getByRole("textbox", { name: /news topic/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /crawling/i })).toBeDisabled();
  });

  it("submits when a suggestion chip is clicked", async () => {
    const onSearch = vi.fn();
    const user = userEvent.setup();
    render(<SearchBar onSearch={onSearch} />);

    await user.click(screen.getByRole("button", { name: "EU AI Act" }));
    expect(onSearch).toHaveBeenCalledWith("EU AI Act");
  });
});
