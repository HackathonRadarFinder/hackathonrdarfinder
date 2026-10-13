import React, { useState } from "react";
import { NavLink, Route, Routes, Link } from "react-router-dom";
import {
  LayoutDashboard, ClipboardList, DatabaseZap, BrainCircuit,
  Activity, FileText, Users, Settings2, ShieldCheck, AlertTriangle,
  CheckCircle2, XCircle, Clock, RefreshCw, Play, Pause, Trash2,
  ChevronRight, Copy, Merge, Flag, TrendingUp, Server,
  Cpu, HardDrive, Wifi, MemoryStick, Eye, UserX, UserCheck,
  ToggleLeft, ToggleRight, ArrowLeft, Plus,
  Search, Filter, Bell, Zap, Globe2
} from "lucide-react";
import {
  adminStats, reviewQueue, sources, duplicates, dataFlags,
  users, auditLogs, modelMetrics, systemHealth, featureFlags
} from "./adminData";

// ─── Admin Shell ──────────────────────────────────────────────────────────────
const adminNav = [
  { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/admin/review", label: "Review Queue", icon: ClipboardList, badge: 23 },
  { to: "/admin/sources", label: "Source Management", icon: DatabaseZap },
  { to: "/admin/duplicates", label: "Duplicates", icon: Copy, badge: 4 },
  { to: "/admin/flags", label: "Data Flags", icon: Flag, badge: 6 },
  { to: "/admin/model", label: "Model Dashboard", icon: BrainCircuit },
  { to: "/admin/health", label: "System Health", icon: Activity },
  { to: "/admin/users", label: "User Management", icon: Users },
  { to: "/admin/audit", label: "Audit Log", icon: FileText },
  { to: "/admin/config", label: "Config & Features", icon: Settings2 },
];

function AdminShell({ children }) {
  const [sideOpen, setSideOpen] = useState(true);
  return (
    <div className="admin-shell">
      <aside className={`admin-sidebar ${sideOpen ? "" : "collapsed"}`}>
        <div className="admin-brand">
          <div className="admin-brand-icon"><ShieldCheck size={18} /></div>
          {sideOpen && <span>Admin Panel</span>}
        </div>
        <nav className="admin-nav">
          {adminNav.map(({ to, label, icon: Icon, badge, end }) => (
            <NavLink key={to} to={to} end={end}
              className={({ isActive }) => `admin-nav-item ${isActive ? "active" : ""}`}>
              <Icon size={17} />
              {sideOpen && <span>{label}</span>}
              {sideOpen && badge && <em className="admin-badge">{badge}</em>}
            </NavLink>
          ))}
        </nav>
        <button aria-label="Toggle demo admin sidebar" className="sidebar-toggle" onClick={() => setSideOpen(!sideOpen)}>
          <ChevronRight size={16} style={{ transform: sideOpen ? "rotate(180deg)" : "none", transition: ".2s" }} />
        </button>
      </aside>
      <div className="admin-main">
        <header className="admin-topbar">
          <Link to="/" className="back-to-site"><ArrowLeft size={15} /> Back to site</Link>
          <div className="admin-topbar-right">
            <span className="live-badge"><span className="pulse-green" />Demo</span>
            <button className="icon-btn" title="Notifications"><Bell size={17} /></button>
            <div className="admin-avatar">NK</div>
          </div>
        </header>
        <div className="admin-content">{children}</div>
      </div>
    </div>
  );
}

// ─── Shared UI Atoms ──────────────────────────────────────────────────────────
function StatCard({ label, value, icon: Icon, color = "purple", sub }) {
  return (
    <div className={`admin-stat-card accent-${color}`}>
      <div className="stat-icon"><Icon size={20} /></div>
      <div>
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
        {sub && <div className="stat-sub">{sub}</div>}
      </div>
    </div>
  );
}

function AdminPageHeader({ title, sub, action }) {
  return (
    <div className="admin-page-header">
      <div>
        <h1 className="admin-page-title">{title}</h1>
        {sub && <p className="admin-page-sub">{sub}</p>}
      </div>
      {action}
    </div>
  );
}

function QueueStatusBadge({ status }) {
  const map = {
    pending: { cls: "badge-pending", label: "Pending" },
    approved: { cls: "badge-approved", label: "Approved" },
    rejected: { cls: "badge-rejected", label: "Rejected" },
    flagged: { cls: "badge-flagged", label: "Flagged" },
  };
  const { cls, label } = map[status] || map.pending;
  return <span className={`queue-badge ${cls}`}>{label}</span>;
}

function ProgressBar({ value, color = "purple", height = 6 }) {
  return (
    <div className="progress-track" style={{ height }}>
      <div className="progress-fill" style={{ width: `${value}%`, background: `var(--${color}-grad)`, height }} />
    </div>
  );
}

// ─── Admin Dashboard ──────────────────────────────────────────────────────────
function AdminDashboard() {
  const { pendingReview, totalEvents, activeSources, duplicatesDetected,
    usersTotal, activeUsers, modelAccuracy, systemUptime,
    eventsThisWeek, scrapersRunning, avgResponseMs } = adminStats;

  return (
    <div>
      <AdminPageHeader title="Admin Dashboard" sub="Platform overview and key operational metrics" />

      <div className="admin-stat-grid">
        <StatCard label="Total Events" value={totalEvents.toLocaleString()} icon={Globe2} color="cyan" sub={`+${eventsThisWeek} this week`} />
        <StatCard label="Pending Review" value={pendingReview} icon={ClipboardList} color="orange" sub="Awaiting moderation" />
        <StatCard label="Active Sources" value={activeSources} icon={DatabaseZap} color="purple" sub={`${scrapersRunning} scrapers running`} />
        <StatCard label="Duplicates" value={duplicatesDetected} icon={Copy} color="red" sub="Detected this week" />
        <StatCard label="Total Users" value={usersTotal.toLocaleString()} icon={Users} color="green" sub={`${activeUsers} active now`} />
        <StatCard label="Model Accuracy" value={`${modelAccuracy}%`} icon={BrainCircuit} color="purple" sub="occurrence-1.1.0" />
        <StatCard label="System Uptime" value={`${systemUptime}%`} icon={Activity} color="green" sub="Last 30 days" />
        <StatCard label="Avg Response" value={`${avgResponseMs}ms`} icon={Zap} color="cyan" sub="API latency" />
      </div>

      <div className="admin-two-col">
        <div>
          <div className="admin-card">
            <div className="admin-card-header">
              <h3>Recent Review Queue</h3>
              <Link to="/admin/review" className="card-link">View all <ChevronRight size={14} /></Link>
            </div>
            {reviewQueue.slice(0, 4).map(item => (
              <div className="queue-row" key={item.id}>
                <div className="queue-row-main">
                  <div className="queue-title">{item.title}</div>
                  <div className="queue-sub">{item.source} · {item.submittedAt}</div>
                </div>
                <QueueStatusBadge status={item.status} />
              </div>
            ))}
          </div>

          <div className="admin-card" style={{ marginTop: 16 }}>
            <div className="admin-card-header">
              <h3>Data Flags</h3>
              <Link to="/admin/flags" className="card-link">View all <ChevronRight size={14} /></Link>
            </div>
            {dataFlags.slice(0, 4).map(f => (
              <div className="flag-row" key={f.id}>
                <span className={`severity-dot sev-${f.severity}`} />
                <div>
                  <div className="flag-title">{f.field} · {f.event}</div>
                  <div className="flag-sub">{f.issue}</div>
                </div>
                <span className={`sev-badge sev-${f.severity}`}>{f.severity}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="admin-card">
            <div className="admin-card-header">
              <h3>Source Health</h3>
              <Link to="/admin/sources" className="card-link">Manage <ChevronRight size={14} /></Link>
            </div>
            {sources.slice(0, 5).map(src => (
              <div className="source-mini-row" key={src.id}>
                <span className={`src-status-dot src-${src.status}`} />
                <div className="source-mini-info">
                  <div className="source-mini-name">{src.name}</div>
                  <ProgressBar value={src.successRate} color={src.status === "error" ? "red" : src.status === "paused" ? "orange" : "green"} height={4} />
                </div>
                <span className="source-mini-rate">{src.successRate}%</span>
              </div>
            ))}
          </div>

          <div className="admin-card" style={{ marginTop: 16 }}>
            <div className="admin-card-header">
              <h3>Model Performance</h3>
              <Link to="/admin/model" className="card-link">Details <ChevronRight size={14} /></Link>
            </div>
            <div className="model-mini-stats">
              {[
                { label: "Accuracy", value: modelMetrics.accuracy },
                { label: "Precision", value: modelMetrics.precision },
                { label: "Recall", value: modelMetrics.recall },
                { label: "F1 Score", value: modelMetrics.f1 },
              ].map(m => (
                <div key={m.label} className="model-mini-stat">
                  <div className="model-mini-label">{m.label}</div>
                  <div className="model-mini-value">{m.value}%</div>
                  <ProgressBar value={m.value} height={5} />
                </div>
              ))}
            </div>
          </div>

          <div className="admin-card" style={{ marginTop: 16 }}>
            <div className="admin-card-header">
              <h3>System Services</h3>
              <Link to="/admin/health" className="card-link">Details <ChevronRight size={14} /></Link>
            </div>
            {systemHealth.services.slice(0, 5).map(svc => (
              <div className="svc-row" key={svc.name}>
                <span className={`svc-dot svc-${svc.status}`} />
                <span className="svc-name">{svc.name}</span>
                <span className="svc-latency">{svc.latency}ms</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="admin-card" style={{ marginTop: 16 }}>
        <div className="admin-card-header">
          <h3>Recent Audit Activity</h3>
          <Link to="/admin/audit" className="card-link">Full log <ChevronRight size={14} /></Link>
        </div>
        <div className="audit-list-mini">
          {auditLogs.slice(0, 5).map(log => (
            <div className="audit-row" key={log.id}>
              <span className={`audit-type-dot audit-${log.type}`} />
              <div className="audit-row-main">
                <span className="audit-action">{log.action}</span>
                <span className="audit-target">· {log.target}</span>
              </div>
              <span className="audit-actor">{log.actor}</span>
              <span className="audit-time">{log.timestamp}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Review Queue ─────────────────────────────────────────────────────────────
function ReviewQueuePage() {
  const [filter, setFilter] = useState("All");
  const [search, setSearch] = useState("");
  const [queue, setQueue] = useState(reviewQueue);

  const statuses = ["All", "pending", "flagged", "approved", "rejected"];
  const filtered = queue.filter(q =>
    (filter === "All" || q.status === filter) &&
    (q.title.toLowerCase().includes(search.toLowerCase()) || q.organizer.toLowerCase().includes(search.toLowerCase()))
  );

  const updateStatus = (id, newStatus) => {
    setQueue(q => q.map(item => item.id === id ? { ...item, status: newStatus } : item));
  };

  return (
    <div>
      <AdminPageHeader
        title="Review Queue"
        sub="Moderate scraped events before they go public"
        action={
          <div className="rq-counts">
            <span className="rq-count-chip orange">{queue.filter(q => q.status === "pending").length} pending</span>
            <span className="rq-count-chip red">{queue.filter(q => q.status === "flagged").length} flagged</span>
          </div>
        }
      />

      <div className="admin-filter-bar">
        <div className="admin-search-box">
          <Search size={16} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search events..." />
        </div>
        <div className="admin-tab-pills">
          {statuses.map(s => (
            <button key={s} onClick={() => setFilter(s)}
              className={`tab-pill ${filter === s ? "active" : ""}`}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="review-queue-list">
        {filtered.map(item => (
          <div key={item.id} className={`review-card rq-${item.status}`}>
            <div className="review-card-top">
              <div className="review-card-info">
                <div className="review-title">{item.title}</div>
                <div className="review-meta">
                  <span>{item.organizer}</span>
                  <span>·</span>
                  <span className="review-source">{item.source}</span>
                  <span>·</span>
                  <span>{item.date}</span>
                  <span>·</span>
                  <span>{item.location}</span>
                  <span>·</span>
                  <span className="review-time">{item.submittedAt}</span>
                </div>
              </div>
              <div className="review-card-right">
                <QueueStatusBadge status={item.status} />
                <div className="confidence-chip">
                  <TrendingUp size={13} />
                  {item.confidence}%
                </div>
              </div>
            </div>
            {item.flags.length > 0 && (
              <div className="review-flags">
                <AlertTriangle size={13} />
                {item.flags.map((f, i) => <span key={i} className="review-flag-tag">{f}</span>)}
              </div>
            )}
            <div className="review-actions">
              <button className="rq-btn approve" onClick={() => updateStatus(item.id, "approved")}>
                <CheckCircle2 size={15} /> Approve
              </button>
              <button className="rq-btn flag-btn" onClick={() => updateStatus(item.id, "flagged")}>
                <Flag size={15} /> Flag
              </button>
              <button className="rq-btn reject" onClick={() => updateStatus(item.id, "rejected")}>
                <XCircle size={15} /> Reject
              </button>
              <button className="rq-btn view">
                <Eye size={15} /> View event
              </button>
            </div>
          </div>
        ))}
        {!filtered.length && (
          <div className="admin-empty">
            <ClipboardList size={38} />
            <h3>No items found</h3>
            <p>Try changing your filter or search term.</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Source Management ────────────────────────────────────────────────────────
function SourceManagement() {
  const [sourceList, setSourceList] = useState(sources);
  const [search, setSearch] = useState("");

  const toggleSource = (id) => {
    setSourceList(s => s.map(src => {
      if (src.id !== id) return src;
      return { ...src, status: src.status === "active" ? "paused" : "active" };
    }));
  };

  const filtered = sourceList.filter(s =>
    s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.url.toLowerCase().includes(search.toLowerCase())
  );

  const typeColors = { Scraper: "cyan", API: "purple", RSS: "orange" };

  return (
    <div>
      <AdminPageHeader
        title="Source Management"
        sub="Manage and monitor all hackathon data ingestion sources"
        action={
          <button className="admin-primary-btn"><Plus size={16} /> Add Source</button>
        }
      />

      <div className="admin-stat-grid four-col">
        <StatCard label="Active Sources" value={sourceList.filter(s => s.status === "active").length} icon={CheckCircle2} color="green" />
        <StatCard label="Paused" value={sourceList.filter(s => s.status === "paused").length} icon={Pause} color="orange" />
        <StatCard label="Errors" value={sourceList.filter(s => s.status === "error").length} icon={AlertTriangle} color="red" />
        <StatCard label="Total Events" value={sourceList.reduce((a, s) => a + s.eventsFound, 0).toLocaleString()} icon={Globe2} color="cyan" />
      </div>

      <div className="admin-filter-bar">
        <div className="admin-search-box">
          <Search size={16} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search sources..." />
        </div>
      </div>

      <div className="sources-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Type</th>
              <th>Status</th>
              <th>Last Run</th>
              <th>Events</th>
              <th>Success Rate</th>
              <th>Errors</th>
              <th>Interval</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(src => (
              <tr key={src.id}>
                <td>
                  <div className="src-name-cell">
                    <div className="src-name">{src.name}</div>
                    <div className="src-url">{src.url}</div>
                  </div>
                </td>
                <td><span className={`type-badge type-${typeColors[src.type]}`}>{src.type}</span></td>
                <td>
                  <span className={`src-status-badge src-status-${src.status}`}>
                    <span className={`src-status-dot src-${src.status}`} />
                    {src.status.charAt(0).toUpperCase() + src.status.slice(1)}
                  </span>
                </td>
                <td className="cell-muted">{src.lastRun}</td>
                <td className="cell-number">{src.eventsFound.toLocaleString()}</td>
                <td>
                  <div className="success-rate-cell">
                    <span className={src.successRate >= 90 ? "rate-good" : src.successRate >= 70 ? "rate-warn" : "rate-bad"}>
                      {src.successRate}%
                    </span>
                    <ProgressBar value={src.successRate} color={src.successRate >= 90 ? "green" : src.successRate >= 70 ? "orange" : "red"} height={4} />
                  </div>
                </td>
                <td className={`cell-number ${src.errorCount > 5 ? "cell-red" : ""}`}>{src.errorCount}</td>
                <td className="cell-muted">{src.avgInterval}</td>
                <td>
                  <div className="src-actions">
                    <button className="src-action-btn" title="Run now"><Play size={14} /></button>
                    <button className="src-action-btn" title={src.status === "active" ? "Pause" : "Resume"}
                      onClick={() => toggleSource(src.id)}>
                      {src.status === "active" ? <Pause size={14} /> : <Play size={14} />}
                    </button>
                    <button className="src-action-btn danger" title="Delete"><Trash2 size={14} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Duplicates ───────────────────────────────────────────────────────────────
function DuplicatesPage() {
  const [dupList, setDupList] = useState(duplicates);

  const resolve = (id, action) => {
    setDupList(d => d.map(dup => dup.id === id ? { ...dup, status: action } : dup));
  };

  const pending = dupList.filter(d => d.status === "pending");
  const resolved = dupList.filter(d => d.status !== "pending");

  return (
    <div>
      <AdminPageHeader title="Duplicate Detection" sub="Review and merge or dismiss detected duplicate events" />

      <div className="admin-stat-grid four-col">
        <StatCard label="Pending Review" value={pending.length} icon={Copy} color="orange" />
        <StatCard label="Resolved" value={resolved.length} icon={CheckCircle2} color="green" />
        <StatCard label="Avg Similarity" value={`${Math.round(dupList.reduce((a, d) => a + d.similarity, 0) / dupList.length)}%`} icon={TrendingUp} color="purple" />
        <StatCard label="Auto-detected" value={dupList.length} icon={BrainCircuit} color="cyan" />
      </div>

      {pending.length > 0 && (
        <>
          <h3 className="admin-section-title">Pending Review</h3>
          {pending.map(dup => (
            <div key={dup.id} className="dup-card">
              <div className="dup-header">
                <span className="dup-similarity" style={{ "--sim": dup.similarity / 100 }}>
                  {dup.similarity}% similar
                </span>
                <span className="dup-time">{dup.detectedAt}</span>
              </div>
              <div className="dup-compare">
                <div className="dup-event-box">
                  <div className="dup-event-label">Source A</div>
                  <div className="dup-event-title">{dup.a.title}</div>
                  <div className="dup-event-meta">{dup.a.source} · {dup.a.date}</div>
                </div>
                <div className="dup-vs"><Merge size={20} /></div>
                <div className="dup-event-box">
                  <div className="dup-event-label">Source B</div>
                  <div className="dup-event-title">{dup.b.title}</div>
                  <div className="dup-event-meta">{dup.b.source} · {dup.b.date}</div>
                </div>
              </div>
              <div className="dup-actions">
                <button className="rq-btn approve" onClick={() => resolve(dup.id, "merged")}>
                  <Merge size={15} /> Merge events
                </button>
                <button className="rq-btn reject" onClick={() => resolve(dup.id, "dismissed")}>
                  <XCircle size={15} /> Dismiss (not duplicate)
                </button>
              </div>
            </div>
          ))}
        </>
      )}

      {resolved.length > 0 && (
        <>
          <h3 className="admin-section-title" style={{ marginTop: 30 }}>Resolved</h3>
          {resolved.map(dup => (
            <div key={dup.id} className="dup-card dup-resolved">
              <div className="dup-header">
                <span className="dup-similarity resolved-similarity">{dup.similarity}% similar</span>
                <span className={`queue-badge ${dup.status === "merged" ? "badge-approved" : "badge-rejected"}`}>
                  {dup.status}
                </span>
                <span className="dup-time">{dup.detectedAt}</span>
              </div>
              <div className="dup-compare compact">
                <span className="dup-event-name">{dup.a.title}</span>
                <Merge size={14} style={{ color: "var(--muted)", flexShrink: 0 }} />
                <span className="dup-event-name">{dup.b.title}</span>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

// ─── Data Flags ───────────────────────────────────────────────────────────────
function DataFlagsPage() {
  const [flags, setFlags] = useState(dataFlags);
  const [sevFilter, setSevFilter] = useState("All");

  const dismiss = (id) => setFlags(f => f.filter(fl => fl.id !== id));

  const filtered = flags.filter(f => sevFilter === "All" || f.severity === sevFilter);

  return (
    <div>
      <AdminPageHeader title="Data Quality Flags" sub="Review and resolve data quality issues detected during ingestion" />

      <div className="admin-stat-grid four-col">
        <StatCard label="High Severity" value={flags.filter(f => f.severity === "high").length} icon={AlertTriangle} color="red" />
        <StatCard label="Medium Severity" value={flags.filter(f => f.severity === "medium").length} icon={Flag} color="orange" />
        <StatCard label="Low Severity" value={flags.filter(f => f.severity === "low").length} icon={CheckCircle2} color="cyan" />
        <StatCard label="Total Flags" value={flags.length} icon={Flag} color="purple" />
      </div>

      <div className="admin-filter-bar">
        <div className="admin-tab-pills">
          {["All", "high", "medium", "low"].map(s => (
            <button key={s} onClick={() => setSevFilter(s)}
              className={`tab-pill ${sevFilter === s ? "active" : ""}`}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="flags-list">
        {filtered.map(flag => (
          <div key={flag.id} className={`flag-card sev-card-${flag.severity}`}>
            <div className="flag-card-left">
              <span className={`sev-badge sev-${flag.severity}`}>{flag.severity}</span>
              <div>
                <div className="flag-event-title">{flag.event}</div>
                <div className="flag-issue">{flag.issue}</div>
                <div className="flag-meta">
                  <span className="flag-field-chip">{flag.field}</span>
                  <span>·</span>
                  <span>{flag.source}</span>
                  <span>·</span>
                  <span>{flag.detectedAt}</span>
                </div>
              </div>
            </div>
            <div className="flag-card-actions">
              <button className="rq-btn view"><Eye size={14} /> Review</button>
              <button className="rq-btn approve" onClick={() => dismiss(flag.id)}>
                <CheckCircle2 size={14} /> Dismiss
              </button>
            </div>
          </div>
        ))}
        {!filtered.length && (
          <div className="admin-empty">
            <CheckCircle2 size={38} />
            <h3>No flags</h3>
            <p>All data quality issues have been resolved.</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Model Dashboard ──────────────────────────────────────────────────────────
function ModelDashboard() {
  const m = modelMetrics;

  return (
    <div>
      <AdminPageHeader
        title="Model Dashboard"
        sub="Prediction engine performance, validation and feature importance"
        action={
          <div className="model-version-pill">
            <BrainCircuit size={15} />
            v{m.version} · trained {m.lastTrained}
          </div>
        }
      />

      <div className="admin-stat-grid">
        <StatCard label="Accuracy" value={`${m.accuracy}%`} icon={TrendingUp} color="purple" />
        <StatCard label="Precision" value={`${m.precision}%`} icon={CheckCircle2} color="green" />
        <StatCard label="Recall" value={`${m.recall}%`} icon={RefreshCw} color="cyan" />
        <StatCard label="F1 Score" value={`${m.f1}%`} icon={Activity} color="orange" />
        <StatCard label="Total Predictions" value={m.totalPredictions} icon={BrainCircuit} color="purple" />
        <StatCard label="Correct" value={m.correctPredictions} icon={CheckCircle2} color="green" />
        <StatCard label="Avg Confidence" value={`${m.avgConfidence}%`} icon={TrendingUp} color="cyan" />
        <StatCard label="Pending Validation" value={m.pendingValidation} icon={Clock} color="orange" />
      </div>

      <div className="admin-two-col">
        <div className="admin-card">
          <div className="admin-card-header"><h3>Version History</h3></div>
          <div className="model-version-table">
            {m.history.map((h, i) => (
              <div key={i} className={`model-ver-row ${i === m.history.length - 1 ? "current-ver" : ""}`}>
                <div>
                  <div className="ver-label">v{h.version} {i === m.history.length - 1 && <span className="current-tag">current</span>}</div>
                  <div className="ver-date">{h.date}</div>
                </div>
                <div className="ver-accuracy-bar">
                  <div className="ver-acc-val">{h.accuracy}%</div>
                  <ProgressBar value={h.accuracy} height={6} />
                </div>
              </div>
            ))}
          </div>
          <button className="admin-secondary-btn full-width" style={{ marginTop: 16 }}>
            <RefreshCw size={15} /> Trigger Retraining
          </button>
        </div>

        <div className="admin-card">
          <div className="admin-card-header"><h3>Feature Importance</h3></div>
          <div className="feature-importance-list">
            {m.features.map((f, i) => (
              <div key={i} className="feature-row">
                <div className="feature-name">{f.name}</div>
                <div className="feature-bar-wrap">
                  <div className="feature-bar" style={{ width: `${f.importance * 100}%` }} />
                </div>
                <div className="feature-val">{(f.importance * 100).toFixed(0)}%</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="admin-card" style={{ marginTop: 16 }}>
        <div className="admin-card-header">
          <h3>Pending Validation</h3>
          <span className="card-meta">{m.pendingValidation} predictions awaiting outcome confirmation</span>
        </div>
        <div className="validation-notice">
          <BrainCircuit size={20} />
          <div>
            <b>Prediction outcomes improve the model</b>
            <p>When predicted events are confirmed or denied, they feed back into the training pipeline. Review and confirm predictions that have passed their predicted window.</p>
          </div>
        </div>
        <div className="model-actions">
          <button className="admin-primary-btn"><Play size={15} /> Run Validation Check</button>
          <button className="admin-secondary-btn"><FileText size={15} /> Export Model Report</button>
        </div>
      </div>
    </div>
  );
}

// ─── System Health ─────────────────────────────────────────────────────────────
function SystemHealthPage() {
  const h = systemHealth;
  const [autoRefresh, setAutoRefresh] = useState(true);

  return (
    <div>
      <AdminPageHeader
        title="System Health"
        sub="Real-time infrastructure status, performance and error monitoring"
        action={
          <div className="health-controls">
            <button
              className={`admin-secondary-btn ${autoRefresh ? "active-btn" : ""}`}
              onClick={() => setAutoRefresh(!autoRefresh)}>
              <RefreshCw size={15} className={autoRefresh ? "spin" : ""} />
              {autoRefresh ? "Auto-refresh on" : "Auto-refresh off"}
            </button>
          </div>
        }
      />

      <div className="admin-stat-grid four-col">
        <StatCard label="Uptime" value={`${h.uptime}%`} icon={Activity} color="green" sub="Last 30 days" />
        <StatCard label="Avg Response" value={`${h.avgResponseMs}ms`} icon={Zap} color="cyan" />
        <StatCard label="Errors (24h)" value={h.errorsLast24h} icon={AlertTriangle} color="red" />
        <StatCard label="Requests (24h)" value={(h.requestsLast24h / 1000).toFixed(1) + "k"} icon={Globe2} color="purple" />
      </div>

      <div className="admin-two-col">
        <div>
          <div className="admin-card">
            <div className="admin-card-header"><h3>Resource Usage</h3></div>
            <div className="resource-list">
              {[
                { label: "CPU Usage", value: h.cpuUsage, icon: Cpu, color: h.cpuUsage > 80 ? "red" : "cyan" },
                { label: "Memory Usage", value: h.memoryUsage, icon: MemoryStick, color: h.memoryUsage > 80 ? "red" : "purple" },
                { label: "Storage", value: h.storageUsage, icon: HardDrive, color: h.storageUsage > 80 ? "red" : "green" },
              ].map(r => (
                <div key={r.label} className="resource-row">
                  <div className="resource-icon"><r.icon size={18} /></div>
                  <div className="resource-info">
                    <div className="resource-label">{r.label}</div>
                    <ProgressBar value={r.value} color={r.color} height={8} />
                  </div>
                  <div className="resource-val">{r.value}%</div>
                </div>
              ))}
              <div className="resource-extra-row">
                <div className="resource-extra"><Wifi size={16} /><span>Active Scrapers</span><b>{h.activeScrapers}</b></div>
                <div className="resource-extra"><Server size={16} /><span>Queue Depth</span><b>{h.queueDepth}</b></div>
              </div>
            </div>
          </div>

          <div className="admin-card" style={{ marginTop: 16 }}>
            <div className="admin-card-header"><h3>Recent Errors</h3></div>
            {h.recentErrors.map((err, i) => (
              <div key={i} className="error-row">
                <span className={`http-code http-${Math.floor(err.code / 100)}xx`}>{err.code}</span>
                <div className="error-path">{err.path}</div>
                <span className="error-count">{err.count}×</span>
                <span className="error-time">{err.lastSeen}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="admin-card">
          <div className="admin-card-header"><h3>Service Status</h3></div>
          <div className="services-list">
            {h.services.map(svc => (
              <div key={svc.name} className="service-row">
                <span className={`svc-dot svc-${svc.status}`} />
                <div className="service-info">
                  <div className="service-name">{svc.name}</div>
                  <div className="service-latency">{svc.latency}ms</div>
                </div>
                <span className={`svc-status-badge svc-badge-${svc.status}`}>
                  {svc.status.charAt(0).toUpperCase() + svc.status.slice(1)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── User Management ──────────────────────────────────────────────────────────
function UserManagement() {
  const [userList, setUserList] = useState(users);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("All");

  const filtered = userList.filter(u =>
    (roleFilter === "All" || u.role === roleFilter) &&
    (u.name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase()))
  );

  const toggleSuspend = (id) => {
    setUserList(ul => ul.map(u => u.id === id
      ? { ...u, status: u.status === "active" ? "suspended" : "active" }
      : u
    ));
  };

  const roleColors = { Admin: "purple", Moderator: "cyan", User: "green" };

  return (
    <div>
      <AdminPageHeader
        title="User Management"
        sub="Manage user accounts, roles and access control"
        action={
          <button className="admin-primary-btn"><Plus size={16} /> Add User</button>
        }
      />

      <div className="admin-stat-grid four-col">
        <StatCard label="Total Users" value={adminStats.usersTotal.toLocaleString()} icon={Users} color="purple" />
        <StatCard label="Active Now" value={adminStats.activeUsers} icon={Activity} color="green" />
        <StatCard label="Admins" value={userList.filter(u => u.role === "Admin").length} icon={ShieldCheck} color="cyan" />
        <StatCard label="Suspended" value={userList.filter(u => u.status === "suspended").length} icon={UserX} color="red" />
      </div>

      <div className="admin-filter-bar">
        <div className="admin-search-box">
          <Search size={16} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search users..." />
        </div>
        <div className="admin-tab-pills">
          {["All", "Admin", "Moderator", "User"].map(r => (
            <button key={r} onClick={() => setRoleFilter(r)}
              className={`tab-pill ${roleFilter === r ? "active" : ""}`}>{r}</button>
          ))}
        </div>
      </div>

      <div className="sources-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Role</th>
              <th>Status</th>
              <th>Joined</th>
              <th>Saved Events</th>
              <th>Last Login</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(user => (
              <tr key={user.id} className={user.status === "suspended" ? "row-suspended" : ""}>
                <td>
                  <div className="user-cell">
                    <div className={`user-avatar-mini avatar-${user.role.toLowerCase()}`}>{user.avatar}</div>
                    <div>
                      <div className="user-name">{user.name}</div>
                      <div className="user-email">{user.email}</div>
                    </div>
                  </div>
                </td>
                <td>
                  <span className={`role-badge role-${roleColors[user.role]}`}>{user.role}</span>
                </td>
                <td>
                  <span className={`status-badge-user ${user.status === "active" ? "user-active" : "user-suspended"}`}>
                    {user.status}
                  </span>
                </td>
                <td className="cell-muted">{user.joined}</td>
                <td className="cell-number">{user.events}</td>
                <td className="cell-muted">{user.lastLogin}</td>
                <td>
                  <div className="src-actions">
                    <button className="src-action-btn" title="View profile"><Eye size={14} /></button>
                    <button className={`src-action-btn ${user.status === "suspended" ? "active-action" : ""}`}
                      title={user.status === "active" ? "Suspend" : "Reactivate"}
                      onClick={() => toggleSuspend(user.id)}>
                      {user.status === "active" ? <UserX size={14} /> : <UserCheck size={14} />}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Audit Log ────────────────────────────────────────────────────────────────
function AuditLogPage() {
  const [typeFilter, setTypeFilter] = useState("All");
  const [search, setSearch] = useState("");

  const auditTypeColors = {
    approval: "green", rejection: "red", source: "cyan", duplicate: "purple",
    user: "orange", flag: "orange", model: "purple", config: "cyan"
  };

  const filtered = auditLogs.filter(log =>
    (typeFilter === "All" || log.type === typeFilter) &&
    (log.action.toLowerCase().includes(search.toLowerCase()) ||
      log.actor.toLowerCase().includes(search.toLowerCase()) ||
      log.target.toLowerCase().includes(search.toLowerCase()))
  );

  const types = ["All", "approval", "rejection", "source", "duplicate", "user", "model", "config"];

  return (
    <div>
      <AdminPageHeader
        title="Audit Log"
        sub="Complete history of all admin and system actions"
        action={
          <button className="admin-secondary-btn"><FileText size={15} /> Export CSV</button>
        }
      />

      <div className="admin-filter-bar">
        <div className="admin-search-box">
          <Search size={16} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search logs..." />
        </div>
        <div className="admin-tab-pills wrap-pills">
          {types.map(t => (
            <button key={t} onClick={() => setTypeFilter(t)}
              className={`tab-pill ${typeFilter === t ? "active" : ""}`}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="admin-card">
        <div className="audit-full-list">
          {filtered.map(log => (
            <div key={log.id} className="audit-full-row">
              <div className={`audit-type-icon audit-icon-${auditTypeColors[log.type]}`}>
                {log.type === "approval" && <CheckCircle2 size={16} />}
                {log.type === "rejection" && <XCircle size={16} />}
                {log.type === "source" && <DatabaseZap size={16} />}
                {log.type === "duplicate" && <Copy size={16} />}
                {log.type === "user" && <Users size={16} />}
                {log.type === "flag" && <Flag size={16} />}
                {log.type === "model" && <BrainCircuit size={16} />}
                {log.type === "config" && <Settings2 size={16} />}
              </div>
              <div className="audit-full-content">
                <div className="audit-full-action">{log.action}</div>
                <div className="audit-full-target">{log.target}</div>
              </div>
              <div className="audit-full-right">
                <div className="audit-actor-info">
                  <div className={`audit-actor-avatar role-${log.role.toLowerCase()}`}>
                    {log.actor.slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <div className="audit-actor-name">{log.actor}</div>
                    <div className="audit-actor-role">{log.role}</div>
                  </div>
                </div>
                <div className="audit-timestamp">{log.timestamp}</div>
              </div>
            </div>
          ))}
          {!filtered.length && (
            <div className="admin-empty">
              <FileText size={38} />
              <h3>No logs found</h3>
              <p>Try adjusting your search or filter.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Config & Feature Flags ───────────────────────────────────────────────────
function ConfigPage() {
  const [flags, setFlags] = useState(featureFlags);

  const toggle = (id) => {
    setFlags(f => f.map(flag => flag.id === id ? { ...flag, enabled: !flag.enabled } : flag));
  };

  const groups = [...new Set(flags.map(f => f.group))];

  return (
    <div>
      <AdminPageHeader
        title="Config & Feature Controls"
        sub="Manage system configuration, feature flags and platform behaviour"
      />

      <div className="admin-stat-grid four-col">
        <StatCard label="Feature Flags" value={flags.length} icon={Settings2} color="purple" />
        <StatCard label="Enabled" value={flags.filter(f => f.enabled).length} icon={ToggleRight} color="green" />
        <StatCard label="Disabled" value={flags.filter(f => !f.enabled).length} icon={ToggleLeft} color="red" />
        <StatCard label="Groups" value={groups.length} icon={Filter} color="cyan" />
      </div>

      {groups.map(group => (
        <div key={group} className="admin-card" style={{ marginBottom: 16 }}>
          <div className="admin-card-header">
            <h3>{group} Settings</h3>
            <span className="card-meta">{flags.filter(f => f.group === group).length} flags</span>
          </div>
          <div className="flags-list-card">
            {flags.filter(f => f.group === group).map(flag => (
              <div key={flag.id} className={`feature-flag-row ${flag.enabled ? "flag-enabled" : ""}`}>
                <div className="flag-info">
                  <div className="flag-name">{flag.label}</div>
                  <div className="flag-key-desc">
                    <span className="flag-key">{flag.name}</span>
                    <span>·</span>
                    <span className="flag-desc">{flag.description}</span>
                  </div>
                </div>
                <div className="flag-toggle-wrap">
                  <span className={`flag-status-text ${flag.enabled ? "enabled-text" : "disabled-text"}`}>
                    {flag.enabled ? "Enabled" : "Disabled"}
                  </span>
                  <button
                    className={`toggle-switch ${flag.enabled ? "toggle-on" : "toggle-off"}`}
                    onClick={() => toggle(flag.id)}
                    title={flag.enabled ? "Disable" : "Enable"}
                  >
                    <div className="toggle-knob" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Admin Router ─────────────────────────────────────────────────────────────
function AdminRouter() {
  return (
    <AdminShell>
      <Routes>
        <Route index element={<AdminDashboard />} />
        <Route path="review" element={<ReviewQueuePage />} />
        <Route path="sources" element={<SourceManagement />} />
        <Route path="duplicates" element={<DuplicatesPage />} />
        <Route path="flags" element={<DataFlagsPage />} />
        <Route path="model" element={<ModelDashboard />} />
        <Route path="health" element={<SystemHealthPage />} />
        <Route path="users" element={<UserManagement />} />
        <Route path="audit" element={<AuditLogPage />} />
        <Route path="config" element={<ConfigPage />} />
      </Routes>
    </AdminShell>
  );
}

export default AdminRouter;
