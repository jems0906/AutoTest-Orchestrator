const { useEffect, useMemo, useState } = React;

const defaultApiHost =
  window.location.hostname === "localhost" || window.location.hostname === "::1"
    ? "127.0.0.1"
    : window.location.hostname;
const API_BASE = window.API_BASE || `http://${defaultApiHost}:8000/api`;

function StatCard({ label, value, hint }) {
  return React.createElement(
    "article",
    { className: "stat-card" },
    React.createElement("p", { className: "stat-label" }, label),
    React.createElement("h3", { className: "stat-value" }, value),
    React.createElement("p", { className: "stat-hint" }, hint || "")
  );
}

function Panel({ title, children }) {
  return React.createElement(
    "section",
    { className: "panel" },
    React.createElement("h2", null, title),
    children
  );
}

function BarList({ rows, valueKey, labelKey, colorClass }) {
  if (!rows || rows.length === 0) {
    return React.createElement("p", { className: "muted" }, "No data");
  }

  const max = Math.max(...rows.map((row) => Number(row[valueKey] || 0)), 1);

  return React.createElement(
    "div",
    { className: "bar-list" },
    rows.map((row, idx) => {
      const value = Number(row[valueKey] || 0);
      const width = Math.round((value / max) * 100);
      return React.createElement(
        "div",
        { className: "bar-row", key: `${row[labelKey]}-${idx}` },
        React.createElement("span", { className: "bar-label" }, row[labelKey]),
        React.createElement(
          "div",
          { className: "bar-track" },
          React.createElement("div", {
            className: `bar-fill ${colorClass || ""}`.trim(),
            style: { width: `${width}%` },
          })
        ),
        React.createElement("span", { className: "bar-value" }, String(value))
      );
    })
  );
}

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [traceability, setTraceability] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadData() {
    setError("");
    try {
      const [dRes, tRes] = await Promise.all([
        fetch(`${API_BASE}/dashboard`),
        fetch(`${API_BASE}/traceability`),
      ]);

      if (!dRes.ok || !tRes.ok) {
        throw new Error("API request failed");
      }

      const dData = await dRes.json();
      const tData = await tRes.json();
      setDashboard(dData);
      setTraceability(tData);
    } catch (err) {
      setError(err.message || "Failed to load dashboard");
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function runRegression(onlyRisky) {
    setMessage("Starting regression run...");
    try {
      const response = await fetch(`${API_BASE}/runs/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_type: onlyRisky ? "risky-retest" : "manual",
          triggered_by: "dashboard",
          only_risky: Boolean(onlyRisky),
        }),
      });

      if (!response.ok) {
        throw new Error("Run trigger failed");
      }

      const payload = await response.json();
      setMessage(
        `Run ${payload.run_id} complete: ${payload.passed}/${payload.total} passed (${payload.pass_rate}%)`
      );
      await loadData();
    } catch (err) {
      setMessage(err.message || "Run failed");
    }
  }

  const statCards = useMemo(() => {
    if (!dashboard) {
      return [];
    }

    return [
      {
        label: "Requirement Mapping",
        value: `${dashboard.requirement_coverage.mapped_coverage_pct}%`,
        hint: `${dashboard.requirement_coverage.mapped_requirements}/${dashboard.requirement_coverage.total_requirements} requirements linked`,
      },
      {
        label: "Passed Coverage",
        value: `${dashboard.requirement_coverage.passed_coverage_pct}%`,
        hint: `${dashboard.requirement_coverage.passed_requirements} requirements with passing evidence`,
      },
      {
        label: "Execution Completeness",
        value: `${dashboard.test_completeness.completeness_pct}%`,
        hint: `${dashboard.test_completeness.executed_last_7_days}/${dashboard.test_completeness.active_tests} tests this week`,
      },
      {
        label: "Open Risk Flags",
        value: String(dashboard.risk_flags.length),
        hint: "Queued for risk retesting",
      },
    ];
  }, [dashboard]);

  if (error) {
    return React.createElement("div", { className: "center error" }, error);
  }

  if (!dashboard) {
    return React.createElement("div", { className: "center" }, "Loading dashboard...");
  }

  return React.createElement(
    "main",
    null,
    React.createElement(
      "section",
      { className: "hero" },
      React.createElement("p", { className: "eyebrow" }, "Autonomous Verification Intelligence"),
      React.createElement("h1", null, "AutoTest Orchestrator"),
      React.createElement(
        "p",
        null,
        "Plan, schedule, and track simulation and HIL-style verification runs with requirement traceability."
      ),
      React.createElement(
        "div",
        { className: "hero-actions" },
        React.createElement(
          "button",
          { onClick: () => runRegression(false) },
          "Run Full Regression"
        ),
        React.createElement(
          "button",
          { className: "ghost", onClick: () => runRegression(true) },
          "Retest Risky"
        )
      ),
      message ? React.createElement("p", { className: "run-message" }, message) : null
    ),
    React.createElement(
      "section",
      { className: "stats-grid" },
      statCards.map((card) => React.createElement(StatCard, { key: card.label, ...card }))
    ),
    React.createElement(
      "section",
      { className: "dashboard-grid" },
      React.createElement(
        Panel,
        { title: "Regression Trend (Pass Rate %)" },
        React.createElement(BarList, {
          rows: dashboard.regression_trends.slice(-10),
          valueKey: "pass_rate",
          labelKey: "day",
          colorClass: "accent",
        })
      ),
      React.createElement(
        Panel,
        { title: "Failure Categories" },
        React.createElement(BarList, {
          rows: dashboard.failure_categories,
          valueKey: "count",
          labelKey: "category",
          colorClass: "danger",
        })
      ),
      React.createElement(
        Panel,
        { title: "Scenario Diversity" },
        React.createElement(BarList, {
          rows: dashboard.scenario_diversity,
          valueKey: "count",
          labelKey: "scenario_type",
          colorClass: "ok",
        })
      ),
      React.createElement(
        Panel,
        { title: "Coverage Gaps" },
        dashboard.coverage_gaps.length === 0
          ? React.createElement("p", { className: "muted" }, "No uncovered requirements")
          : React.createElement(
              "ul",
              { className: "simple-list" },
              dashboard.coverage_gaps.map((gap, idx) =>
                React.createElement(
                  "li",
                  { key: `${gap.requirement_key}-${idx}` },
                  `${gap.requirement_key}: ${gap.requirement_title}`
                )
              )
            )
      )
    ),
    React.createElement(
      Panel,
      { title: "Requirement Traceability Matrix" },
      React.createElement(
        "div",
        { className: "table-wrap" },
        React.createElement(
          "table",
          null,
          React.createElement(
            "thead",
            null,
            React.createElement(
              "tr",
              null,
              React.createElement("th", null, "Requirement"),
              React.createElement("th", null, "Severity"),
              React.createElement("th", null, "Mapped Tests"),
              React.createElement("th", null, "Latest Status")
            )
          ),
          React.createElement(
            "tbody",
            null,
            traceability.map((row) => {
              const failCount = row.tests.filter((t) => t.last_outcome === "fail").length;
              const status = failCount > 0 ? `${failCount} failures` : "healthy";
              return React.createElement(
                "tr",
                { key: row.requirement_key },
                React.createElement(
                  "td",
                  null,
                  React.createElement("strong", null, row.requirement_key),
                  React.createElement("p", null, row.requirement_title)
                ),
                React.createElement("td", null, row.severity),
                React.createElement("td", null, String(row.test_count)),
                React.createElement("td", { className: failCount ? "danger-text" : "ok-text" }, status)
              );
            })
          )
        )
      )
    )
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(React.createElement(App));
