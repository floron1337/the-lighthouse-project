"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Article, ArticleBiasAnalysis } from "@/lib/streamClient";

interface SentimentChartProps {
  analyses: ArticleBiasAnalysis[];
  articleBySource: Map<string, Article>;
}

function colorFor(direction: string): string {
  const d = direction.toLowerCase();
  if (d.includes("west")) return "hsl(var(--bias-west))";
  if (d.includes("brics") || d.includes("east")) return "hsl(var(--bias-brics))";
  if (d.includes("government") || d.includes("state"))
    return "hsl(var(--bias-government))";
  if (d.includes("neutral")) return "hsl(var(--bias-neutral))";
  return "hsl(var(--bias-mixed))";
}

export function SentimentChart({
  analyses,
  articleBySource,
}: SentimentChartProps) {
  const data = analyses.map((a) => {
    const article = articleBySource.get(a.article_url);
    return {
      source: article?.source_name ?? a.source_id,
      country: article?.country ?? "",
      sentiment: Number(a.sentiment_score.toFixed(2)),
      fill: colorFor(a.overall_bias_direction),
      direction: a.overall_bias_direction,
    };
  });

  const height = Math.max(140, data.length * 38);

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
          barCategoryGap={8}
        >
          <CartesianGrid
            horizontal={false}
            stroke="hsl(var(--border))"
            strokeDasharray="2 4"
          />
          <XAxis
            type="number"
            domain={[-1, 1]}
            ticks={[-1, -0.5, 0, 0.5, 1]}
            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
            stroke="hsl(var(--border))"
          />
          <YAxis
            type="category"
            dataKey="source"
            width={120}
            tick={{ fill: "hsl(var(--foreground))", fontSize: 12 }}
            stroke="hsl(var(--border))"
          />
          <Tooltip
            cursor={{ fill: "hsl(var(--muted))", opacity: 0.4 }}
            contentStyle={{
              background: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: 8,
              fontSize: 12,
              color: "hsl(var(--foreground))",
            }}
            formatter={(value: number, _name, item) => [
              `${value > 0 ? "+" : ""}${value}`,
              item?.payload?.direction ?? "Sentiment",
            ]}
          />
          <ReferenceLine x={0} stroke="hsl(var(--foreground))" strokeOpacity={0.4} />
          <Bar dataKey="sentiment" radius={[4, 4, 4, 4]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
