import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});

// jsdom doesn't implement matchMedia, ResizeObserver, or IntersectionObserver;
// Radix and Recharts both touch them, so stub minimal versions for tests.
if (typeof window !== "undefined") {
  if (!window.matchMedia) {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));
  }

  class MockObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
    takeRecords = vi.fn().mockReturnValue([]);
  }

  const w = window as unknown as Record<string, unknown>;
  w.ResizeObserver ||= MockObserver;
  w.IntersectionObserver ||= MockObserver;
}
