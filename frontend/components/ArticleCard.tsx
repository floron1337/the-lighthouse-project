import { Article, ArticleBiasAnalysis } from "@/lib/streamClient";

interface ArticleCardProps {
  article: Article;
  analysis?: ArticleBiasAnalysis;
}

const BIAS_BADGE: Record<string, string> = {
  "pro-Western": "bg-blue-100 text-blue-800",
  "pro-BRICS": "bg-red-100 text-red-800",
  neutral: "bg-green-100 text-green-800",
  "pro-government": "bg-purple-100 text-purple-800",
  mixed: "bg-amber-100 text-amber-800",
};

export default function ArticleCard({ article, analysis }: ArticleCardProps) {
  const badgeClass =
    BIAS_BADGE[analysis?.overall_bias_direction ?? ""] ??
    "bg-gray-100 text-gray-700";

  return (
    <article
      className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm
                 flex flex-col gap-3 hover:shadow-md transition-shadow"
    >
      <div className="flex items-center justify-between gap-2 text-sm text-gray-500">
        <span className="font-semibold text-gray-700">{article.source_name}</span>
        <span>{article.country}</span>
        <time dateTime={article.published_at}>
          {new Date(article.published_at).toLocaleDateString()}
        </time>
      </div>

      <a
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-lg font-semibold text-gray-900 hover:text-blue-600 leading-snug"
      >
        {article.title}
      </a>

      {article.full_text && (
        <p className="text-gray-600 text-sm line-clamp-3">{article.full_text}</p>
      )}

      {analysis && (
        <div className="border-t pt-3 flex flex-col gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`text-xs font-semibold px-2 py-1 rounded-full ${badgeClass}`}
            >
              {analysis.overall_bias_direction}
            </span>
            <span className="text-xs text-gray-400">
              confidence {Math.round(analysis.confidence * 100)}%
            </span>
            <span className="text-xs text-gray-400">
              sentiment {analysis.sentiment_score > 0 ? "+" : ""}
              {analysis.sentiment_score.toFixed(2)}
            </span>
          </div>

          <details className="text-sm">
            <summary className="cursor-pointer text-blue-600 hover:underline text-xs select-none">
              Why flagged?
            </summary>
            <div className="mt-2 flex flex-col gap-1 text-gray-700">
              <p>{analysis.framing_analysis}</p>
              {analysis.loaded_terms.length > 0 && (
                <p>
                  <span className="font-medium">Loaded terms: </span>
                  {analysis.loaded_terms.join(", ")}
                </p>
              )}
              {analysis.omissions.length > 0 && (
                <p>
                  <span className="font-medium">Possible omissions: </span>
                  {analysis.omissions.join("; ")}
                </p>
              )}
            </div>
          </details>
        </div>
      )}
    </article>
  );
}
