import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const ALPHA_TO_FLAG: Record<string, string> = {
  US: "🇺🇸", GB: "🇬🇧", FR: "🇫🇷", DE: "🇩🇪", CN: "🇨🇳", RU: "🇷🇺",
  IN: "🇮🇳", JP: "🇯🇵", KR: "🇰🇷", BR: "🇧🇷", QA: "🇶🇦", IL: "🇮🇱",
  TR: "🇹🇷", AU: "🇦🇺", CA: "🇨🇦", SG: "🇸🇬", ZA: "🇿🇦", IR: "🇮🇷",
  MX: "🇲🇽", NG: "🇳🇬", KE: "🇰🇪", AR: "🇦🇷", ES: "🇪🇸", IT: "🇮🇹",
  NL: "🇳🇱", SE: "🇸🇪", NO: "🇳🇴", PL: "🇵🇱", UA: "🇺🇦", AE: "🇦🇪",
  SA: "🇸🇦", EG: "🇪🇬", TH: "🇹🇭", ID: "🇮🇩", PH: "🇵🇭", VN: "🇻🇳",
};

export function countryFlag(code?: string | null): string {
  if (!code) return "🌐";
  const upper = code.toUpperCase();
  if (ALPHA_TO_FLAG[upper]) return ALPHA_TO_FLAG[upper];
  if (upper.length !== 2) return "🌐";
  const base = 127397;
  return String.fromCodePoint(
    upper.charCodeAt(0) + base,
    upper.charCodeAt(1) + base
  );
}
