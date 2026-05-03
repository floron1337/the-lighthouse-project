import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";

function renderToggle() {
  return render(
    <ThemeProvider
      attribute="class"
      defaultTheme="light"
      enableSystem={false}
      storageKey="lighthouse-theme-test"
    >
      <ThemeToggle />
    </ThemeProvider>
  );
}

describe("ThemeToggle", () => {
  it("renders a button with an accessible label", async () => {
    renderToggle();
    expect(
      await screen.findByRole("button", { name: /switch to dark mode/i })
    ).toBeInTheDocument();
  });

  it("toggles the theme when clicked and persists to localStorage", async () => {
    const user = userEvent.setup();
    renderToggle();

    const button = await screen.findByRole("button", { name: /switch to dark mode/i });
    await user.click(button);

    expect(
      await screen.findByRole("button", { name: /switch to light mode/i })
    ).toBeInTheDocument();
    expect(window.localStorage.getItem("lighthouse-theme-test")).toBe("dark");
  });
});
