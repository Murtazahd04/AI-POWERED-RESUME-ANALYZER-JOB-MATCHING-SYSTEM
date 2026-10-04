import { useEffect, useState } from "react";
import { adminApi } from "../api/endpoints";
import { apiErrorMessage } from "../api/client";

const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const number = new Intl.NumberFormat("en-US");
const displayNumber = (value) => value == null ? "—" : number.format(value);
const displayCost = (value) => value == null ? "—" : currency.format(value);

function AnalyticsTable({ headers, children }) {
  return <div className="analytics-table-wrap"><table className="analytics-table"><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>{children}</tbody></table></div>;
}

export default function AdminAccessPage() {
  const [data, setData] = useState(null);
  const [filters, setFilters] = useState({ start_date: "", end_date: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value));
      setData(await adminApi.analytics(params));
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load admin analytics."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const maxSectionTokens = Math.max(...(data?.sections || []).map((row) => (row.input_tokens || 0) + (row.output_tokens || 0)), 1);

  return <main className="admin-page">
    <div className="admin-heading">
      <div><h1 className="page-title">AI insights</h1><p className="page-subtitle">Provider-reported token usage and estimated costs for AI analysis requests.</p></div>
      <form className="date-filter" onSubmit={(event) => { event.preventDefault(); load(); }}>
        <label>From<input type="date" value={filters.start_date} onChange={(e) => setFilters({ ...filters, start_date: e.target.value })} /></label>
        <label>To<input type="date" value={filters.end_date} onChange={(e) => setFilters({ ...filters, end_date: e.target.value })} /></label>
        <button className="btn-small btn-filled" type="submit">Apply</button>
      </form>
    </div>
    {error && <div className="auth-error">{error}</div>}
    {loading ? <p className="muted">Loading analytics…</p> : data && <>
      <section className="metric-grid">
        <article><span>Analyzed resumes</span><strong>{displayNumber(data.summary.analyzed_resume_count)}</strong></article>
        <article><span>Analysis requests</span><strong>{displayNumber(data.summary.successful_analysis_request_count)}</strong></article>
        <article><span>Input tokens</span><strong>{displayNumber(data.summary.input_tokens)}</strong></article>
        <article><span>Output tokens</span><strong>{displayNumber(data.summary.output_tokens)}</strong></article>
        <article><span>Estimated cost</span><strong>{displayCost(data.summary.estimated_total_cost_usd)}</strong></article>
      </section>
      <section className="admin-panel"><h2>Model usage</h2><AnalyticsTable headers={["Model", "Requests", "Input", "Output", "Estimated cost"]}>{data.models.map((row) => <tr key={row.model}><td>{row.model}</td><td>{row.request_count}</td><td>{displayNumber(row.input_tokens)}</td><td>{displayNumber(row.output_tokens)}</td><td>{displayCost(row.estimated_total_cost_usd)}</td></tr>)}</AnalyticsTable></section>
      <section className="admin-panel"><h2>Section usage</h2><AnalyticsTable headers={["Section", "Requests", "Input", "Output", "Estimated cost", "Attribution"]}>{data.sections.map((row) => <tr key={row.section}><td>{row.section}</td><td>{row.request_count}</td><td>{displayNumber(row.input_tokens)}</td><td>{displayNumber(row.output_tokens)}</td><td>{displayCost(row.estimated_total_cost_usd)}</td><td className="attribution">{row.usage_attribution}</td></tr>)}</AnalyticsTable><div className="usage-bars" aria-label="Section token usage chart">{data.sections.map((row) => <div className="usage-bar" key={row.section}><span>{row.section}</span><div><i style={{ width: `${(((row.input_tokens || 0) + (row.output_tokens || 0)) / maxSectionTokens) * 100}%` }} /></div><b>{displayNumber((row.input_tokens || 0) + (row.output_tokens || 0))}</b></div>)}</div></section>
      <section className="admin-panel"><h2>Recommendation cost by user</h2><p className="muted">Per-recommendation values are allocated from the generating request’s estimated cost.</p><AnalyticsTable headers={["User ID", "Recommendations", "Estimated total", "Cost per recommendation", "Attribution"]}>{data.recommendation_costs.map((row) => <tr key={row.user_id}><td className="user-id">{row.user_id}</td><td>{row.recommendation_count}</td><td>{displayCost(row.estimated_total_cost_usd)}</td><td>{displayCost(row.estimated_cost_per_recommendation_usd)}</td><td className="attribution">{row.cost_attribution}</td></tr>)}</AnalyticsTable></section>
    </>}
  </main>;
}
