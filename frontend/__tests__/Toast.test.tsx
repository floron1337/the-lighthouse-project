import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { Toast } from "@/components/Toast";

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("Toast", () => {
  it("renders the title and description when open", () => {
    render(
      <Toast
        open
        title="No relevant news found"
        description="No articles came back for “climate”."
        onDismiss={vi.fn()}
      />
    );
    expect(screen.getByText("No relevant news found")).toBeInTheDocument();
    expect(
      screen.getByText(/no articles came back for/i)
    ).toBeInTheDocument();
  });

  it("auto-dismisses after the configured duration", () => {
    const onDismiss = vi.fn();
    render(
      <Toast
        open
        title="Hi"
        durationMs={2000}
        onDismiss={onDismiss}
      />
    );

    act(() => {
      vi.advanceTimersByTime(1900);
    });
    expect(onDismiss).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("does not auto-dismiss when durationMs is 0", () => {
    const onDismiss = vi.fn();
    render(<Toast open title="Hi" durationMs={0} onDismiss={onDismiss} />);

    act(() => {
      vi.advanceTimersByTime(10_000);
    });
    expect(onDismiss).not.toHaveBeenCalled();
  });

  it("calls onDismiss when the close button is clicked", () => {
    const onDismiss = vi.fn();
    render(<Toast open title="Hi" durationMs={0} onDismiss={onDismiss} />);

    fireEvent.click(
      screen.getByRole("button", { name: /dismiss notification/i })
    );
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("unmounts after the fade-out transition when closed", () => {
    const { rerender } = render(
      <Toast open title="Hi" durationMs={0} onDismiss={vi.fn()} />
    );
    expect(screen.getByRole("status")).toBeInTheDocument();

    rerender(<Toast open={false} title="Hi" durationMs={0} onDismiss={vi.fn()} />);
    // Still mounted during the fade-out window
    expect(screen.getByRole("status")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(400);
    });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
