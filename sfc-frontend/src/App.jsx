import React, { useEffect, useState } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
  Title,
} from "chart.js";
import { Bar } from "react-chartjs-2";

// Register chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend, Title);

// --- CONFIG ---
const API_BASE =
  "https://sfc-api.braveglacier-e2f83e8d.australiaeast.azurecontainerapps.io";

// --- SHARED STYLES ---
const pageStyle = {
  backgroundColor: "#0b0b0f",
  minHeight: "100vh",
  color: "#f5f5f5",
  padding: "2rem 0",
  fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
};

const containerStyle = {
  maxWidth: "1280px",
  margin: "0 auto",
  padding: "0 2rem 3rem",
};

const headerStyle = {
  borderBottom: "1px solid #262626",
  paddingBottom: "1rem",
  marginBottom: "2rem",
};

const appTitleStyle = {
  fontSize: "2.4rem",
  fontWeight: 800,
  letterSpacing: "0.03em",
  margin: 0,
};

const sectionStyle = {
  marginBottom: "2.5rem",
};

const sectionHeadingStyle = {
  fontSize: "1.4rem",
  margin: "0 0 0.75rem",
};

const cardStyle = {
  borderRadius: "10px",
  border: "1px solid #262626",
  background:
    "radial-gradient(circle at top left, #1c1c26 0%, #111118 45%, #0d0d12 100%)",
  padding: "1rem 1.25rem",
};

const buttonStyle = {
  padding: "0.4rem 0.9rem",
  background: "#000",
  color: "#fff",
  borderRadius: "999px",
  border: "1px solid #3b3b3b",
  cursor: "pointer",
  fontSize: "0.9rem",
  fontWeight: 500,
};

const subtleTextStyle = {
  fontSize: "0.9rem",
  color: "#bbbbbb",
};

function App() {
  // ---- HEALTH ----
  const [status, setStatus] = useState("checking...");
  const [healthError, setHealthError] = useState("");

  // ---- MONTHLY SUMMARY ----
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [summary, setSummary] = useState(null);
  const [summaryError, setSummaryError] = useState("");
  const [summaryLoading, setSummaryLoading] = useState(false);

  // ---- BUDGET INSIGHTS ----
  const [budgetInsights, setBudgetInsights] = useState([]);
  const [budgetLoading, setBudgetLoading] = useState(false);
  const [budgetError, setBudgetError] = useState("");

  // ---- TRAJECTORY (trend) ----
  const [trajectory, setTrajectory] = useState([]);
  const [trajectoryLoading, setTrajectoryLoading] = useState(false);
  const [trajectoryError, setTrajectoryError] = useState("");

  // ---------- HEALTH CHECK ----------
  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch(`${API_BASE}/health`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        setStatus(data.status ?? "unknown");
      } catch (err) {
        console.error("Health check failed:", err);
        setHealthError("Failed to reach API (see console).");
        setStatus("down");
      }
    }

    checkHealth();
  }, []);

  // ---------- LOAD SUMMARY ----------
  async function loadSummary() {
    setSummaryLoading(true);
    setSummaryError("");
    setSummary(null);

    try {
      const url = `${API_BASE}/summary/monthly?year=${year}&month=${month}`;
      console.log("Fetching summary:", url);
      const res = await fetch(url);

      if (!res.ok) {
        let errBody = "";
        try {
          errBody = await res.text();
        } catch {
          /* ignore */
        }
        console.error("Summary error response:", res.status, errBody);
        throw new Error(`Summary load failed with HTTP ${res.status}`);
      }

      const data = await res.json();
      console.log("Summary response:", data);
      setSummary(data);
    } catch (err) {
      console.error("loadSummary failed:", err);
      setSummaryError("Failed to load monthly summary. See console for details.");
    } finally {
      setSummaryLoading(false);
    }
  }

  // ---------- LOAD BUDGET INSIGHTS ----------
  async function loadBudgetInsights() {
    console.log("clicked budget button");
    setBudgetLoading(true);
    setBudgetError("");
    setBudgetInsights([]);

    try {
      const url = `${API_BASE}/insights/budget?year=${year}&month=${month}`;
      console.log("Fetching budget insights:", url);
      const res = await fetch(url);

      if (!res.ok) {
        let errBody = "";
        try {
          errBody = await res.text();
        } catch {
          /* ignore */
        }
        console.error("Budget insights error response:", res.status, errBody);
        throw new Error(`Budget insights failed with HTTP ${res.status}`);
      }

      const data = await res.json();
      console.log("Budget insights response:", data);
      setBudgetInsights(data);
    } catch (err) {
      console.error("loadBudgetInsights failed:", err);
      setBudgetError(
        "Failed to load budget insights. See browser console for details."
      );
    } finally {
      setBudgetLoading(false);
    }
  }

  // ---------- LOAD SPENDING TRAJECTORY ----------
  async function loadTrajectory() {
    setTrajectoryLoading(true);
    setTrajectoryError("");
    setTrajectory([]);

    try {
      const url = `${API_BASE}/summary/trajectory`;
      console.log("Fetching trajectory:", url);

      const res = await fetch(url);

      if (!res.ok) {
        let errBody = "";
        try {
          errBody = await res.text();
        } catch {
          /* ignore */
        }
        console.error("Trajectory error response:", res.status, errBody);
        throw new Error("Failed to load trajectory");
      }

      const data = await res.json();
      console.log("Trajectory response:", data);

      // Your API returns { months: [...], biggest_jump: {...} }
      const monthsArr = Array.isArray(data.months) ? data.months : [];
      setTrajectory(monthsArr);
    } catch (err) {
      console.error("loadTrajectory failed:", err);
      setTrajectoryError("Could not load monthly trend data.");
    } finally {
      setTrajectoryLoading(false);
    }
  }

  // ---------- DERIVED VALUES ----------
  const totalSpent =
    summary && typeof summary.total_spent !== "undefined"
      ? Number(summary.total_spent)
      : null;
  const totalIncome =
    summary && typeof summary.total_income !== "undefined"
      ? Number(summary.total_income)
      : null;

  const categoryTotals = Array.isArray(summary?.by_category)
    ? summary.by_category
    : [];

  const topCategories = categoryTotals
    .slice()
    .sort((a, b) => Number(b.total_spent) - Number(a.total_spent))
    .slice(0, 3);

  const categoryLabels = categoryTotals.map((c) => c.category_name);
  const categoryValues = categoryTotals.map((c) => Number(c.total_spent));

  // coloured bars
  const colors = [
    "#4CAF50",
    "#FF9800",
    "#2196F3",
    "#E91E63",
    "#9C27B0",
    "#FFC107",
    "#00BCD4",
    "#8BC34A",
    "#F44336",
    "#3F51B5",
  ];

  const categoryBarData = {
    labels: categoryLabels,
    datasets: [
      {
        label: `Spending by category (${month}/${year})`,
        data: categoryValues,
        backgroundColor: categoryTotals.map(
          (_, i) => colors[i % colors.length]
        ),
        borderColor: "#ffffff22",
        borderWidth: 1,
      },
    ],
  };

  const categoryBarOptions = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: { display: false },
    },
    scales: {
      x: { ticks: { color: "#eee" } },
      y: { ticks: { color: "#eee" } },
    },
  };

  // ---------- UI ----------
  return (
    <div style={pageStyle}>
      <div style={containerStyle}>
        {/* HEADER */}
        <header style={headerStyle}>
          <h1 style={appTitleStyle}>Smart Financial Coach</h1>
          <p style={{ marginTop: "0.5rem", fontSize: "0.95rem" }}>
            API base URL: <code>{API_BASE}</code>
          </p>
        </header>

        {/* ---- API HEALTH ---- */}
        <section style={sectionStyle}>
          <h2 style={sectionHeadingStyle}>API Health</h2>
          <div style={cardStyle}>
            <p style={{ margin: 0 }}>
              Status:{" "}
              <strong
                style={{ color: status === "ok" ? "lightgreen" : "#ff6b6b" }}
              >
                {status}
              </strong>
            </p>
            {healthError && (
              <p style={{ color: "#ff6b6b", marginTop: "0.5rem" }}>
                {healthError}
              </p>
            )}
          </div>
        </section>

        {/* ---- MONTHLY SUMMARY ---- */}
        <section style={sectionStyle}>
          <h2 style={sectionHeadingStyle}>Monthly Summary</h2>

          {/* Controls */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: "0.75rem",
              marginBottom: "0.75rem",
            }}
          >
            <label>
              <span style={{ marginRight: "0.25rem" }}>Year:</span>
              <input
                type="number"
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
                style={{
                  width: "6rem",
                  padding: "0.25rem 0.4rem",
                  borderRadius: "6px",
                  border: "1px solid #333",
                  background: "#050509",
                  color: "#f5f5f5",
                }}
              />
            </label>

            <label>
              <span style={{ marginRight: "0.25rem" }}>Month:</span>
              <input
                type="number"
                min="1"
                max="12"
                value={month}
                onChange={(e) => setMonth(Number(e.target.value))}
                style={{
                  width: "3.5rem",
                  padding: "0.25rem 0.4rem",
                  borderRadius: "6px",
                  border: "1px solid #333",
                  background: "#050509",
                  color: "#f5f5f5",
                }}
              />
            </label>

            <button onClick={loadSummary} style={buttonStyle}>
              Load Summary
            </button>
          </div>

          {/* Loading / error */}
          {summaryLoading && <p>Loading summary...</p>}
          {summaryError && (
            <p style={{ color: "#ff6b6b" }}>{summaryError}</p>
          )}

          {/* Card + breakdown */}
          {summary && !summaryLoading && (
            <div style={{ display: "grid", gap: "1.25rem" }}>
              {/* summary card */}
              <div style={cardStyle}>
                {totalSpent !== null ? (
                  <p style={{ margin: 0 }}>
                    <strong>Total spent:</strong>{" "}
                    $
                    {Number.isFinite(totalSpent)
                      ? totalSpent.toFixed(2)
                      : totalSpent}
                  </p>
                ) : (
                  <p style={{ margin: 0 }}>No total_spent in response.</p>
                )}

                {totalIncome !== null ? (
                  <p style={{ margin: "0.4rem 0 0" }}>
                    <strong>Total income:</strong>{" "}
                    $
                    {Number.isFinite(totalIncome)
                      ? totalIncome.toFixed(2)
                      : totalIncome}
                  </p>
                ) : (
                  <p style={{ margin: "0.4rem 0 0" }}>
                    No total_income in response.
                  </p>
                )}

                {topCategories.length > 0 && (
                  <p style={{ marginTop: "0.6rem", ...subtleTextStyle }}>
                    Top {topCategories.length} categories:{" "}
                    {topCategories.map((cat, idx) => (
                      <span key={cat.category_name}>
                        {cat.category_name}
                        {idx < topCategories.length - 1 ? ", " : ""}
                      </span>
                    ))}
                  </p>
                )}
              </div>

              {/* Category breakdown + chart */}
              {categoryTotals.length > 0 && (
                <div
                  style={{
                    display: "grid",
                    gap: "1.25rem",
                    gridTemplateColumns: "minmax(0, 1.1fr)",
                  }}
                >
                  {/* Table */}
                  <div style={cardStyle}>
                    <h4 style={{ margin: "0 0 0.5rem" }}>
                      Category Breakdown
                    </h4>
                    <table
                      style={{
                        width: "100%",
                        borderCollapse: "collapse",
                        fontSize: "0.9rem",
                      }}
                    >
                      <thead>
                        <tr>
                          <th
                            style={{
                              textAlign: "left",
                              borderBottom: "1px solid #444",
                              paddingBottom: "4px",
                            }}
                          >
                            Category
                          </th>
                          <th
                            style={{
                              textAlign: "right",
                              borderBottom: "1px solid #444",
                              paddingBottom: "4px",
                            }}
                          >
                            Spent
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {categoryTotals
                          .slice()
                          .sort(
                            (a, b) =>
                              Number(b.total_spent) -
                              Number(a.total_spent)
                          )
                          .map((cat) => (
                            <tr key={cat.category_name}>
                              <td style={{ padding: "6px 0" }}>
                                {cat.category_name}
                              </td>
                              <td
                                style={{
                                  padding: "6px 0",
                                  textAlign: "right",
                                }}
                              >
                                ${Number(cat.total_spent).toFixed(2)}
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Chart */}
                  <div style={cardStyle}>
                    <h4 style={{ margin: "0 0 0.75rem" }}>
                      Spending by category
                    </h4>
                    <Bar
                      data={categoryBarData}
                      options={categoryBarOptions}
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        {/* ---- BUDGET INSIGHTS ---- */}
        <section style={sectionStyle}>
          <h2 style={sectionHeadingStyle}>Budget Insights</h2>

          <p style={subtleTextStyle}>
            Uses the same year/month as above. 
          </p>

          <button onClick={loadBudgetInsights} style={buttonStyle}>
            Load Budget Insights
          </button>

          {budgetLoading && <p>Loading budget insights...</p>}
          {budgetError && (
            <p style={{ color: "#ff6b6b" }}>{budgetError}</p>
          )}

          {!budgetLoading &&
            !budgetError &&
            budgetInsights.length === 0 && (
              <p style={{ marginTop: "0.75rem" }}>
                No budget insights for this month.
              </p>
            )}

          {budgetInsights.length > 0 && (
            <div style={{ marginTop: "0.85rem" }}>
              {budgetInsights.map((b) => (
                <div
                  key={b.category_name}
                  style={{ marginBottom: "0.7rem" }}
                >
                  <strong>{b.category_name}</strong> – spent $
                  {Number(b.spent).toFixed(2)} / budget $
                  {Number(b.amount_limit).toFixed(2)} →{" "}
                  <em>{b.status}</em>
                  <br />
                  <span style={subtleTextStyle}>{b.message}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ---- SPENDING TREND ---- */}
        <section style={sectionStyle}>
          <h2 style={sectionHeadingStyle}>Spending Trend</h2>

          <button onClick={loadTrajectory} style={buttonStyle}>
            Load Trend
          </button>

          {trajectoryLoading && <p>Loading trend...</p>}
          {trajectoryError && (
            <p style={{ color: "#ff6b6b" }}>{trajectoryError}</p>
          )}

          {trajectory.length > 0 && (
            <div style={{ marginTop: "0.85rem" }}>
              <div style={cardStyle}>
                <h4 style={{ margin: "0 0 0.5rem" }}>
                  Monthly total spending
                </h4>
                <ul
                  style={{
                    listStyle: "none",
                    paddingLeft: 0,
                    margin: 0,
                    fontSize: "0.9rem",
                  }}
                >
                  {trajectory.map((t) => (
                    <li
                      key={`${t.year}-${t.month}`}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        padding: "4px 0",
                        borderBottom: "1px solid #252525",
                      }}
                    >
                      <span>
                        {t.month}/{t.year}
                      </span>
                      <span>
                        ${Number(t.total_spent).toFixed(2)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default App;
