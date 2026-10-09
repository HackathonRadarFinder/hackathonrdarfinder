import React, { useMemo, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, Bookmark, Sparkles, Bell, User, Settings, CalendarDays,
  Clock3, ArrowRight, Trash2, CheckCheck, X, Plus, Compass, TrendingUp,
  Link2, Target, Mail, MapPin, Award,
} from "lucide-react";
import { predictions } from "./data";
import { useUser } from "./UserContext";
import { EventCard, StatusBadge, logoText } from "./components";
import { INTERESTS, daysLeft, getInitials, matchesInterests } from "./userData";

/* ---------- shared bits ---------- */

function Toggle({ checked, onChange, label }) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label}
      className={checked ? "switch on" : "switch"} onClick={() => onChange(!checked)}>
      <span />
    </button>
  );
}

function PageTitle({ eyebrow, title, subtitle, action }) {
  return (
    <div className="acc-title">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

function Empty({ icon, title, text, to, cta }) {
  return (
    <div className="empty">
      {icon}<h3>{title}</h3><p>{text}</p>
      {to && <Link to={to} className="primary-btn">{cta}</Link>}
    </div>
  );
}

function deadlineChip(deadline) {
  const left = daysLeft(deadline);
  if (left === null) return null;
  if (left < 0) return <span className="deadline-chip closed">Closed</span>;
  const cls = left <= 14 ? "deadline-chip urgent" : left <= 45 ? "deadline-chip soon" : "deadline-chip";
  return <span className={cls}><Clock3 size={12} />{left === 0 ? "Closes today" : `${left} days left`}</span>;
}

/* ---------- layout with side menu ---------- */

export function AccountLayout() {
  const { unreadCount, savedIds, profile } = useUser();
  const items = [
    { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { to: "/saved", label: "Saved Events", icon: Bookmark, count: savedIds.length },
    { to: "/recommendations", label: "Recommendations", icon: Sparkles },
    { to: "/notifications", label: "Notifications", icon: Bell, count: unreadCount, alert: true },
    { to: "/profile", label: "Profile", icon: User },
    { to: "/preferences", label: "Preferences", icon: Settings },
  ];
  return (
    <div className="account-wrap">
      <aside className="account-nav">
        <div className="account-user">
          <span className="avatar">{getInitials(profile.name)}</span>
          <div><b>{profile.name || "Your profile"}</b><small>{profile.role}</small></div>
        </div>
        {items.map(({ to, label, icon: Icon, count, alert }) => (
          <NavLink key={to} to={to} className={({ isActive }) => (isActive ? "acc-link active" : "acc-link")}>
            <Icon size={17} />{label}
            {count > 0 && <em className={alert ? "count alert" : "count"}>{count}</em>}
          </NavLink>
        ))}
      </aside>
      <section className="account-main"><Outlet /></section>
    </div>
  );
}

/* ---------- Dashboard ---------- */

export function Dashboard() {
  const { profile, savedEvents, notifications, unreadCount, recommendations, completeness, markRead } = useUser();

  const upcoming = useMemo(
    () => savedEvents
      .map((e) => ({ ...e, left: daysLeft(e.deadline) }))
      .filter((e) => e.left !== null && e.left >= 0)
      .sort((a, b) => a.left - b.left),
    [savedEvents]
  );
  const top = recommendations.slice(0, 3);
  const firstName = profile.name.trim().split(" ")[0];

  return (
    <>
      <PageTitle eyebrow="USER DASHBOARD" title={firstName ? `Welcome back, ${firstName}` : "Welcome back"}
        subtitle="Your saved events, deadlines and personalised signals in one place."
        action={<Link to="/explore" className="primary-btn"><Compass size={16} />Explore events</Link>} />

      <div className="dash-stats">
        <Link to="/saved"><Bookmark size={18} /><b>{savedEvents.length}</b><span>Saved events</span></Link>
        <Link to="/saved"><Clock3 size={18} /><b>{upcoming.filter((e) => e.left <= 45).length}</b><span>Deadlines within 45 days</span></Link>
        <Link to="/notifications"><Bell size={18} /><b>{unreadCount}</b><span>Unread notifications</span></Link>
        <Link to="/recommendations"><Target size={18} /><b>{recommendations.filter((r) => r.score >= 60).length}</b><span>Strong matches</span></Link>
      </div>

      <div className="dash-grid">
        <div className="content-card">
          <div className="card-head"><h3>Upcoming deadlines</h3><Link to="/saved" className="text-link">All saved <ArrowRight size={14} /></Link></div>
          {upcoming.length === 0 ? (
            <p className="muted-text">No upcoming deadlines. Save an event to track it here.</p>
          ) : upcoming.slice(0, 4).map((e) => (
            <Link key={e.id} to={`/event/${e.id}`} className="mini-row">
              <span className={`event-logo ${e.color}`}>{logoText(e)}</span>
              <div><b>{e.title}</b><small>Registration deadline · {e.deadline}</small></div>
              {deadlineChip(e.deadline)}
            </Link>
          ))}
        </div>

        <div className="content-card">
          <div className="card-head"><h3>Profile strength</h3><b className="pct">{completeness}%</b></div>
          <div className="meter"><span style={{ width: `${completeness}%` }} /></div>
          <p className="muted-text">A complete profile and clear interests give sharper recommendations.</p>
          <Link to="/profile" className="secondary-btn inline">Complete profile</Link>
        </div>

        <div className="content-card">
          <div className="card-head"><h3>Top recommendations</h3><Link to="/recommendations" className="text-link">See all <ArrowRight size={14} /></Link></div>
          {top.map(({ event, score }) => (
            <Link key={event.id} to={`/event/${event.id}`} className="mini-row">
              <span className={`event-logo ${event.color}`}>{logoText(event)}</span>
              <div><b>{event.title}</b><small>{event.organizer}</small></div>
              <span className="match">{score}% match</span>
            </Link>
          ))}
        </div>

        <div className="content-card">
          <div className="card-head"><h3>Recent notifications</h3><Link to="/notifications" className="text-link">View all <ArrowRight size={14} /></Link></div>
          {notifications.slice(0, 3).map((n) => (
            <Link key={n.id} to={n.link} onClick={() => markRead(n.id)} className="mini-row">
              <span className={`n-icon ${n.type}`}><NotifIcon type={n.type} /></span>
              <div><b>{n.title}</b><small>{n.time}</small></div>
              {!n.read && <span className="unread-dot" />}
            </Link>
          ))}
          {notifications.length === 0 && <p className="muted-text">You're all caught up.</p>}
        </div>
      </div>
    </>
  );
}

/* ---------- Saved Events ---------- */

export function SavedEvents() {
  const { savedEvents, toggleSaved } = useUser();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("All");
  const [sort, setSort] = useState("Deadline");

  const list = useMemo(() => {
    let l = savedEvents.filter((e) =>
      (e.title + e.organizer + e.tags.join(" ")).toLowerCase().includes(query.toLowerCase()) &&
      (status === "All" || e.status === status));
    l = [...l].sort((a, b) =>
      sort === "Deadline" ? new Date(a.deadline) - new Date(b.deadline) : a.title.localeCompare(b.title));
    return l;
  }, [savedEvents, query, status, sort]);

  return (
    <>
      <PageTitle eyebrow="YOUR LIBRARY" title="Saved events"
        subtitle="Track the hackathons you care about and never miss a deadline."
        action={<div className="result-count"><b>{savedEvents.length}</b> saved</div>} />

      <div className="filter-bar">
        <div className="filter-search"><Compass size={18} />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search saved events..." /></div>
        <div className="select-wrap"><select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option>All</option><option>Official</option><option>Reported</option></select></div>
        <div className="select-wrap"><select value={sort} onChange={(e) => setSort(e.target.value)}>
          <option>Deadline</option><option>Title</option></select></div>
      </div>

      <div className="saved-list">
        {list.map((e) => (
          <article className="saved-row" key={e.id}>
            <span className={`event-logo ${e.color}`}>{logoText(e)}</span>
            <div className="saved-info">
              <div className="saved-top"><StatusBadge status={e.status} />{deadlineChip(e.deadline)}</div>
              <Link to={`/event/${e.id}`} className="event-title">{e.title}</Link>
              <p className="organizer-name">{e.organizer}</p>
              <div className="event-meta">
                <span><CalendarDays size={15} />{e.date}</span>
                <span><MapPin size={15} />{e.location}</span>
                <span><Award size={15} />{e.prize}</span>
              </div>
            </div>
            <div className="saved-actions">
              <Link to={`/event/${e.id}`} className="secondary-btn">View</Link>
              <button className="icon-btn danger" title="Remove" onClick={() => toggleSaved(e.id)}><Trash2 size={16} /></button>
            </div>
          </article>
        ))}
        {savedEvents.length === 0 && (
          <Empty icon={<Bookmark size={38} />} title="Nothing saved yet"
            text="Tap the bookmark on any event to keep it here." to="/explore" cta="Explore hackathons" />
        )}
        {savedEvents.length > 0 && list.length === 0 && (
          <Empty icon={<Compass size={38} />} title="No matches" text="Try changing your search or filters." />
        )}
      </div>
    </>
  );
}

/* ---------- Recommendations ---------- */

export function Recommendations() {
  const { recommendations, preferences } = useUser();
  const [min, setMin] = useState(0);
  const shown = recommendations.filter((r) => r.score >= min);

  const rank = { High: 2, Medium: 1 };
  const need = { All: 0, Medium: 1, High: 2 }[preferences.minConfidence];
  const matchedPredictions = predictions.filter(
    (p) => (rank[p.confidence] || 0) >= need &&
      matchesInterests([p.event, p.organizer], preferences.interests).length > 0
  );

  return (
    <>
      <PageTitle eyebrow="PERSONALISED" title="Recommended for you"
        subtitle={`Based on your interests: ${preferences.interests.join(", ") || "none selected yet"}.`}
        action={<Link to="/preferences" className="secondary-btn"><Settings size={14} /> Tune preferences</Link>} />

      {preferences.interests.length === 0 && (
        <div className="notice"><Sparkles size={20} /><div><b>Pick some interests</b>
          <p>Choose topics in Preferences so we can rank events for you.</p></div></div>
      )}

      <div className="pill-row">
        {[[0, "All matches"], [50, "50%+"], [70, "70%+"]].map(([v, l]) => (
          <button key={v} className={min === v ? "pill active" : "pill"} onClick={() => setMin(v)}>{l}</button>
        ))}
      </div>

      <div className="reco-list">
        {shown.map(({ event, score, reasons }) => (
          <div className="reco" key={event.id}>
            <div className="reco-score"><b>{score}%</b><small>match</small></div>
            <div className="reco-body">
              <EventCard event={event} />
              <div className="reasons">{reasons.map((r) => <span key={r}><TrendingUp size={12} />{r}</span>)}</div>
            </div>
          </div>
        ))}
        {shown.length === 0 && <Empty icon={<Sparkles size={38} />} title="No matches at this level" text="Lower the match filter to see more events." />}
      </div>

      <div className="section-heading sub"><div><p className="eyebrow">PREDICTED SOON</p><h2>Signals matching your interests</h2></div>
        <Link to="/predictions" className="text-link">All predictions <ArrowRight size={16} /></Link></div>
      <div className="notice"><Sparkles size={18} /><div><b>Predictions are not official announcements.</b>
        <p>Treat these as early signals only and verify with the organizer.</p></div></div>
      <div className="prediction-grid two">
        {matchedPredictions.map((p) => (
          <article className="prediction-card" key={p.id}>
            <div className="prediction-card-top">
              <span className={`confidence ${p.confidence.toLowerCase()}`}><TrendingUp size={14} />{p.confidence} confidence</span>
              <b>{Math.round(p.probability * 100)}%</b>
            </div>
            <p className="mini-label">{p.organizer}</p><h2>{p.event}</h2>
            <div className="window"><CalendarDays size={17} /><div><small>Predicted window</small><b>{p.window}</b></div></div>
          </article>
        ))}
        {matchedPredictions.length === 0 && <p className="muted-text">No predictions match your interests and confidence setting.</p>}
      </div>
    </>
  );
}

/* ---------- Notifications ---------- */

function NotifIcon({ type }) {
  if (type === "deadline") return <Clock3 size={16} />;
  if (type === "prediction") return <Sparkles size={16} />;
  if (type === "event") return <CalendarDays size={16} />;
  return <Bell size={16} />;
}

export function Notifications() {
  const { notifications, unreadCount, markRead, markAllRead, dismissNotification } = useUser();
  const navigate = useNavigate();
  const [tab, setTab] = useState("All");
  const tabs = ["All", "Unread", "Deadlines", "Predictions", "Events"];

  const list = notifications.filter((n) =>
    tab === "All" ? true : tab === "Unread" ? !n.read : n.type === { Deadlines: "deadline", Predictions: "prediction", Events: "event" }[tab]);

  return (
    <>
      <PageTitle eyebrow="ALERTS" title="Notifications"
        subtitle={unreadCount ? `${unreadCount} unread` : "You're all caught up."}
        action={<button className="secondary-btn" onClick={markAllRead} disabled={!unreadCount}><CheckCheck size={14} /> Mark all read</button>} />

      <div className="pill-row">
        {tabs.map((t) => <button key={t} className={tab === t ? "pill active" : "pill"} onClick={() => setTab(t)}>{t}</button>)}
      </div>

      <div className="notif-list">
        {list.map((n) => (
          <div key={n.id} className={n.read ? "notif" : "notif unread"}>
            <span className={`n-icon ${n.type}`}><NotifIcon type={n.type} /></span>
            <div className="notif-body" onClick={() => { markRead(n.id); navigate(n.link); }}>
              <b>{n.title}</b><p>{n.body}</p><small>{n.time}</small>
            </div>
            <div className="notif-actions">
              {!n.read && <button className="icon-btn" title="Mark read" onClick={() => markRead(n.id)}><CheckCheck size={15} /></button>}
              <button className="icon-btn" title="Dismiss" onClick={() => dismissNotification(n.id)}><X size={15} /></button>
            </div>
          </div>
        ))}
        {list.length === 0 && <Empty icon={<Bell size={38} />} title="Nothing here" text="New alerts will show up in this list." />}
      </div>
    </>
  );
}

/* ---------- Profile ---------- */

export function Profile() {
  const { profile, updateProfile, completeness } = useUser();
  const [draft, setDraft] = useState(profile);
  const [skill, setSkill] = useState("");
  const [saved, setSaved] = useState(false);
  const set = (k) => (e) => { setDraft({ ...draft, [k]: e.target.value }); setSaved(false); };

  const addSkill = () => {
    const s = skill.trim();
    if (s && !draft.skills.some((x) => x.toLowerCase() === s.toLowerCase())) {
      setDraft({ ...draft, skills: [...draft.skills, s] }); setSaved(false);
    }
    setSkill("");
  };
  const removeSkill = (s) => { setDraft({ ...draft, skills: draft.skills.filter((x) => x !== s) }); setSaved(false); };
  const submit = (e) => {
    e.preventDefault();
    updateProfile(draft);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <>
      <PageTitle eyebrow="ACCOUNT" title="Your profile" subtitle="Tell us about yourself to get better matches." />
      <div className="profile-grid">
        <aside className="content-card profile-card">
          <span className="avatar big">{getInitials(draft.name)}</span>
          <h3>{draft.name || "Your name"}</h3>
          <p>{draft.role}{draft.organization ? ` · ${draft.organization}` : ""}</p>
          <div className="meter"><span style={{ width: `${completeness}%` }} /></div>
          <small className="muted-text">{completeness}% complete</small>
        </aside>

        <form className="content-card form" onSubmit={submit}>
          <div className="form-grid">
            <label>Full name<input value={draft.name} onChange={set("name")} placeholder="Your name" /></label>
            <label>Email<div className="input-icon"><Mail size={15} /><input type="email" value={draft.email} onChange={set("email")} placeholder="you@example.com" /></div></label>
            <label>I am a
              <select value={draft.role} onChange={set("role")}>
                <option>Student</option><option>Developer</option><option>Professional</option>
              </select></label>
            <label>College / Organization<input value={draft.organization} onChange={set("organization")} placeholder="Where you study or work" /></label>
            <label>Location<div className="input-icon"><MapPin size={15} /><input value={draft.location} onChange={set("location")} placeholder="City, Country" /></div></label>
            <label>GitHub<div className="input-icon"><Link2 size={15} /><input value={draft.github} onChange={set("github")} placeholder="github.com/username" /></div></label>
            <label>LinkedIn<div className="input-icon"><Link2 size={15} /><input value={draft.linkedin} onChange={set("linkedin")} placeholder="linkedin.com/in/username" /></div></label>
          </div>
          <label>Bio<textarea rows={3} value={draft.bio} onChange={set("bio")} placeholder="A line or two about what you build." /></label>

          <label>Skills</label>
          <div className="tags editable">
            {draft.skills.map((s) => <span key={s}>{s}<button type="button" onClick={() => removeSkill(s)} aria-label={`Remove ${s}`}><X size={11} /></button></span>)}
          </div>
          <div className="skill-add">
            <input value={skill} onChange={(e) => setSkill(e.target.value)} placeholder="Add a skill"
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addSkill(); } }} />
            <button type="button" className="secondary-btn" onClick={addSkill}><Plus size={14} /> Add</button>
          </div>

          <div className="form-actions">
            <button className="primary-btn" type="submit">Save profile</button>
            {saved && <span className="saved-msg">Profile saved</span>}
          </div>
        </form>
      </div>
    </>
  );
}

/* ---------- Preferences ---------- */

export function Preferences() {
  const { preferences, updatePreferences, resetPreferences } = useUser();
  const toggleInterest = (i) =>
    updatePreferences((p) => ({
      interests: p.interests.includes(i) ? p.interests.filter((x) => x !== i) : [...p.interests, i],
    }));
  const setNotify = (k) => (v) => updatePreferences((p) => ({ notify: { ...p.notify, [k]: v } }));
  const setChannel = (k) => (v) => updatePreferences((p) => ({ channels: { ...p.channels, [k]: v } }));

  const Segment = ({ value, options, onChange }) => (
    <div className="segment">
      {options.map((o) => <button type="button" key={o} className={value === o ? "active" : ""} onClick={() => onChange(o)}>{o}</button>)}
    </div>
  );

  return (
    <>
      <PageTitle eyebrow="SETTINGS" title="Preferences" subtitle="Changes are saved automatically."
        action={<button className="secondary-btn" onClick={resetPreferences}>Reset to defaults</button>} />

      <section className="content-card">
        <h3>Interests</h3>
        <p className="muted-text">Used to rank recommendations and predictions.</p>
        <div className="pill-row wrap">
          {INTERESTS.map((i) => (
            <button key={i} className={preferences.interests.includes(i) ? "pill active" : "pill"} onClick={() => toggleInterest(i)}>{i}</button>
          ))}
        </div>
      </section>

      <section className="content-card">
        <h3>Event preferences</h3>
        <div className="pref-row"><div><b>Event mode</b><small>Remote, hybrid or either</small></div>
          <Segment value={preferences.mode} options={["Any", "Remote", "Hybrid"]} onChange={(v) => updatePreferences({ mode: v })} /></div>
        <div className="pref-row"><div><b>Eligibility</b><small>Events you can join</small></div>
          <Segment value={preferences.eligibility} options={["Students", "Developers", "Professionals"]} onChange={(v) => updatePreferences({ eligibility: v })} /></div>
        <div className="pref-row"><div><b>Prediction confidence</b><small>Minimum level shown in your feed</small></div>
          <Segment value={preferences.minConfidence} options={["All", "Medium", "High"]} onChange={(v) => updatePreferences({ minConfidence: v })} /></div>
      </section>

      <section className="content-card">
        <h3>Notify me about</h3>
        {[
          ["deadlines", "Registration deadlines", "Reminders for events you saved"],
          ["newEvents", "New verified events", "Events that match your interests"],
          ["predictions", "Prediction signals", "Early signals, never official announcements"],
          ["digest", "Digest summary", "A roundup instead of individual alerts"],
        ].map(([k, t, d]) => (
          <div className="pref-row" key={k}><div><b>{t}</b><small>{d}</small></div>
            <Toggle label={t} checked={preferences.notify[k]} onChange={setNotify(k)} /></div>
        ))}
        {preferences.notify.digest && (
          <div className="pref-row"><div><b>Digest frequency</b></div>
            <Segment value={preferences.digestFrequency} options={["Daily", "Weekly"]} onChange={(v) => updatePreferences({ digestFrequency: v })} /></div>
        )}
      </section>

      <section className="content-card">
        <h3>Channels</h3>
        <div className="pref-row"><div><b>Email</b><small>Alerts to your profile email</small></div>
          <Toggle label="Email" checked={preferences.channels.email} onChange={setChannel("email")} /></div>
        <div className="pref-row"><div><b>In-app / push</b><small>Shown in the bell menu</small></div>
          <Toggle label="Push" checked={preferences.channels.push} onChange={setChannel("push")} /></div>
      </section>
    </>
  );
}
