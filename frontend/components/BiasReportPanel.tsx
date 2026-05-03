import { BiasReport } from "@/lib/streamClient";

interface BiasReportPanelProps {
  report: BiasReport;
}

export default function BiasReportPanel({ report }: BiasReportPanelProps) {
  return (
    <section
      aria-label="Bias Analysis Report"
      className="rounded-2xl border border-amber-200 bg-amber-50 p-6 flex flex-col gap-5"
    >
      <h2 className="text-xl font-bold text-gray-900">
        Bias Analysis:{" "}
        <span className="text-amber-700">{report.topic}</span>
      </h2>

      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-2">Balanced Summary</h3>
        <p className="text-gray-800 leading-relaxed">{report.balanced_summary}</p>
      </div>

      {report.consensus_facts.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-2">Consensus Facts</h3>
          <ul className="list-disc list-inside space-y-1 text-gray-700 text-sm">
            {report.consensus_facts.map((fact, i) => (
              <li key={i}>{fact}</li>
            ))}
          </ul>
        </div>
      )}

      {report.disputed_framings.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-2">Disputed Framings</h3>
          <div className="flex flex-col gap-3">
            {report.disputed_framings.map((item, i) => (
              <div
                key={i}
                className="rounded-xl bg-white border border-amber-100 p-4"
              >
                <p className="font-medium text-gray-800">{item.framing}</p>
                <p className="text-xs text-gray-500 mt-1">
                  Pattern: {item.geopolitical_pattern}
                  {item.sources_using_it.length > 0 &&
                    ` · Sources: ${item.sources_using_it.join(", ")}`}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {report.geopolitical_patterns.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-2">Geopolitical Patterns</h3>
          <ul className="list-disc list-inside space-y-1 text-gray-700 text-sm">
            {report.geopolitical_patterns.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-xs text-gray-400 border-t border-amber-200 pt-3">
        {report.methodology_note}
      </p>
    </section>
  );
}
