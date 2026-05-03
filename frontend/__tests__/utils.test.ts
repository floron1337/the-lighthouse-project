import { describe, expect, it } from "vitest";
import { cn, countryFlag } from "@/lib/utils";
import { iso2ToNumeric } from "@/lib/iso";

describe("cn", () => {
  it("merges conditional class names", () => {
    expect(cn("p-2", false && "hidden", "text-sm")).toBe("p-2 text-sm");
  });

  it("dedupes conflicting tailwind classes (last wins)", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
  });
});

describe("countryFlag", () => {
  it("returns a known flag for an ISO-2 code", () => {
    expect(countryFlag("US")).toBe("🇺🇸");
    expect(countryFlag("gb")).toBe("🇬🇧");
  });

  it("falls back to the globe glyph for invalid input", () => {
    expect(countryFlag(undefined)).toBe("🌐");
    expect(countryFlag(null)).toBe("🌐");
    expect(countryFlag("xxx")).toBe("🌐");
  });
});

describe("iso2ToNumeric", () => {
  it("maps common ISO-2 codes to their padded numeric ISO-3166-1 id", () => {
    expect(iso2ToNumeric("US")).toBe("840");
    expect(iso2ToNumeric("GB")).toBe("826");
    expect(iso2ToNumeric("CN")).toBe("156");
    expect(iso2ToNumeric("at")).toBe("040");
  });

  it("returns undefined for unknown / empty input", () => {
    expect(iso2ToNumeric(undefined)).toBeUndefined();
    expect(iso2ToNumeric("")).toBeUndefined();
    expect(iso2ToNumeric("ZZ")).toBeUndefined();
  });
});
