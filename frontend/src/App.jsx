/**
 * @file App.jsx
 * @description Main application routing and shell for Hackathon Radar AI.
 */

import React, { useMemo, useState } from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Link,
  NavLink,
  useNavigate,
  useParams,
} from 'react-router-dom';

import {
  Search,
  Home as HomeIcon,
  Compass,
  Sparkles,
  Building2,
  Bookmark,
  CalendarDays,
  MapPin,
  Users,
  ArrowRight,
  CheckCircle2,
  Clock3,
  ExternalLink,
  SlidersHorizontal,
  ChevronDown,
  Bell,
  Menu,
  X,
  BrainCircuit,
  ShieldCheck,
  TrendingUp,
  Award,
  Globe2,
} from 'lucide-react';

import { AuthProvider } from './context/AuthProvider';
import { useAuth } from './context/AuthContext';

import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import ForgotPassword from './pages/auth/ForgotPassword';

import { events, predictions, organizers } from './publicData';

import './App.css';
import './publicPages.css';

/* =========================================================
   PUBLIC PAGE COMPONENTS
   ========================================================= */

function Layout({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const nav = [
    { to: '/home', label: 'Home', icon: HomeIcon },
    { to: '/explore', label: 'Explore', icon: Compass },
    { to: '/predictions', label: 'Predictions', icon: Sparkles },
    {
      to: '/organizer/microsoft',
      label: 'Organizers',
      icon: Building2,
    },
  ];

  return (
    <div className="app-shell">
      <header className="navbar">
        <Link className="brand" to="/home">
          <span className="brand-mark">
            <BrainCircuit size={21} />
          </span>
          <span>
            Hackathon <b>Radar</b>
          </span>
        </Link>

        <button
          className="mobile-menu"
          type="button"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle navigation"
        >
          {mobileOpen ? <X /> : <Menu />}
        </button>

        <nav className={mobileOpen ? 'nav-links open' : 'nav-links'}>
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                isActive ? 'nav-link active' : 'nav-link'
              }
            >
              <Icon size={17} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="nav-actions">
          <button
            className="icon-btn"
            type="button"
            title="Notifications"
          >
            <Bell size={18} />
          </button>

          <button className="profile-chip" type="button">
            <span>NK</span>
            <b>My Profile</b>
          </button>
        </div>
      </header>

      <main>{children}</main>

      <footer className="footer">
        <div>
          <span className="brand-mark small">
            <BrainCircuit size={16} />
          </span>
          Hackathon Radar AI
        </div>
        <span>Discover opportunities. Prepare earlier.</span>
      </footer>
    </div>
  );
}

function StatusBadge({ status }) {
  return (
    <span className={`status ${status.toLowerCase()}`}>
      <span className="status-dot" />
      {status}
    </span>
  );
}

function EventCard({ event }) {
  const [saved, setSaved] = useState(false);

  return (
    <article className="event-card">
      <div className={`event-logo ${event.color}`}>
        {event.organizer
          .split(' ')
          .map((x) => x[0])
          .slice(0, 2)
          .join('')}
      </div>

      <div className="event-card-body">
        <div className="card-top">
          <StatusBadge status={event.status} />

          <button
            className={saved ? 'save-btn saved' : 'save-btn'}
            type="button"
            onClick={() => setSaved(!saved)}
          >
            <Bookmark
              size={17}
              fill={saved ? 'currentColor' : 'none'}
            />
          </button>
        </div>

        <Link
          to={`/event/${event.id}`}
          className="event-title"
        >
          {event.title}
        </Link>

        <p className="organizer-name">{event.organizer}</p>

        <div className="event-meta">
          <span>
            <CalendarDays size={15} />
            {event.date}
          </span>

          <span>
            <MapPin size={15} />
            {event.location}
          </span>

          <span>
            <Award size={15} />
            {event.prize}
          </span>
        </div>

        <div className="tags">
          {event.tags.map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
      </div>
    </article>
  );
}

function Home() {
  const [query, setQuery] = useState('');

  const results = events.filter(
    (e) =>
      e.title.toLowerCase().includes(query.toLowerCase()) ||
      e.organizer.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div>
      <section className="hero">
        <div className="hero-glow" />

        <div className="hero-content">
          <div className="eyebrow">
            <Sparkles size={15} />
            AI-powered hackathon intelligence
          </div>

          <h1>
            Find your next
            <br />
            <span>big opportunity.</span>
          </h1>

          <p>
            Discover verified hackathons and get early signals
            about events that may be announced soon.
          </p>

          <div className="hero-search">
            <Search size={20} />

            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search hackathons, organizers, technologies..."
            />

            <Link to="/explore" className="search-action">
              Explore
            </Link>
          </div>

          <div className="trust-row">
            <span>
              <ShieldCheck size={16} />
              Verified sources
            </span>

            <span>
              <BrainCircuit size={16} />
              AI predictions
            </span>

            <span>
              <Clock3 size={16} />
              Fresh data
            </span>
          </div>
        </div>

        <div className="hero-panel">
          <div className="radar-circle">
            <div className="radar-ring r1" />
            <div className="radar-ring r2" />
            <div className="radar-dot d1" />
            <div className="radar-dot d2" />

            <div className="radar-center">
              <BrainCircuit size={25} />
            </div>
          </div>

          <div className="signal-card">
            <span className="pulse" />

            <div>
              <b>Prediction signal detected</b>
              <small>Microsoft · 91% confidence</small>
            </div>
          </div>
        </div>
      </section>

      <section className="stats-strip">
        <div>
          <b>1,240+</b>
          <span>Verified Events</span>
        </div>

        <div>
          <b>185</b>
          <span>Organizers</span>
        </div>

        <div>
          <b>92%</b>
          <span>Data Freshness</span>
        </div>

        <div>
          <b>85%+</b>
          <span>Prediction Target</span>
        </div>
      </section>

      <section className="section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">DISCOVER</p>
            <h2>Upcoming hackathons</h2>
          </div>

          <Link to="/explore" className="text-link">
            View all <ArrowRight size={16} />
          </Link>
        </div>

        <div className="event-grid">
          {results
            .slice(0, 4)
            .map((e) => (
              <EventCard key={e.id} event={e} />
            ))}
        </div>
      </section>

      <section className="prediction-banner">
        <div className="prediction-icon">
          <Sparkles />
        </div>

        <div>
          <span className="eyebrow">
            PREDICTIVE INTELLIGENCE
          </span>

          <h2>
            Know what's coming before it's announced.
          </h2>

          <p>
            Our prediction engine looks at historical recurrence,
            organizer activity and trusted signals.
          </p>
        </div>

        <Link to="/predictions" className="primary-btn">
          View predictions <ArrowRight size={17} />
        </Link>
      </section>
    </div>
  );
}

function Explore() {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('All');
  const [status, setStatus] = useState('All');
  const [sort, setSort] = useState('Recommended');

  const filtered = useMemo(() => {
    let list = events.filter(
      (e) =>
        (
          e.title +
          e.organizer +
          e.theme +
          e.tags.join(' ')
        )
          .toLowerCase()
          .includes(query.toLowerCase()) &&
        (mode === 'All' || e.mode === mode) &&
        (status === 'All' || e.status === status)
    );

    if (sort === 'Prize') {
      list = [...list].sort((a, b) =>
        b.prize.localeCompare(a.prize)
      );
    }

    return list;
  }, [query, mode, status, sort]);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">DISCOVERY</p>
          <h1>Explore hackathons</h1>
          <p>
            Search and filter verified opportunities from trusted
            sources.
          </p>
        </div>

        <div className="result-count">
          <b>{filtered.length}</b> events found
        </div>
      </div>

      <div className="filter-bar">
        <div className="filter-search">
          <Search size={18} />

          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search events, organizers, skills..."
          />
        </div>

        <div className="select-wrap">
          <SlidersHorizontal size={16} />

          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          >
            <option>All</option>
            <option>Remote</option>
            <option>Hybrid</option>
          </select>
        </div>

        <div className="select-wrap">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option>All</option>
            <option>Official</option>
            <option>Reported</option>
          </select>
        </div>

        <div className="select-wrap">
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option>Recommended</option>
            <option>Prize</option>
          </select>

          <ChevronDown size={15} />
        </div>
      </div>

      <div className="explore-layout">
        <aside className="side-filter">
          <h3>Filter by</h3>

          <label>Theme</label>

          {[
            'Artificial Intelligence',
            'Web Development',
            'Cloud Computing',
            'Sustainability',
            'Open Innovation',
          ].map((x) => (
            <button key={x} type="button">
              {x}
              <span>›</span>
            </button>
          ))}

          <label>Eligibility</label>

          {['Students', 'Developers', 'Everyone'].map((x) => (
            <button key={x} type="button">
              {x}
              <span>›</span>
            </button>
          ))}
        </aside>

        <div className="event-list">
          {filtered.map((e) => (
            <EventCard key={e.id} event={e} />
          ))}

          {!filtered.length && (
            <div className="empty">
              <Compass size={38} />
              <h3>No events found</h3>
              <p>Try changing your search or filters.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function EventDetails() {
  const { id } = useParams();

  const event =
    events.find((e) => e.id === id) || events[0];

  const [saved, setSaved] = useState(false);

  return (
    <div className="page">
      <Link to="/explore" className="back-link">
        ← Back to explore
      </Link>

      <div className="detail-hero">
        <div className={`big-event-logo ${event.color}`}>
          {event.organizer
            .split(' ')
            .map((x) => x[0])
            .slice(0, 2)
            .join('')}
        </div>

        <div className="detail-heading">
          <div>
            <StatusBadge status={event.status} />

            <span className="verified">
              <CheckCircle2 size={15} />
              Verified {event.verified}
            </span>
          </div>

          <h1>{event.title}</h1>
          <p>{event.organizer}</p>
        </div>

        <button
          className={
            saved ? 'primary-btn saved-main' : 'primary-btn'
          }
          type="button"
          onClick={() => setSaved(!saved)}
        >
          <Bookmark
            size={17}
            fill={saved ? 'currentColor' : 'none'}
          />
          {saved ? 'Saved' : 'Save event'}
        </button>
      </div>

      <div className="detail-grid">
        <div>
          <section className="content-card">
            <h2>About this hackathon</h2>
            <p>{event.description}</p>

            <p>
              This event is listed with its current public
              information. Dates and eligibility may change, so
              always verify details at the authoritative source
              before registering.
            </p>
          </section>

          <section className="content-card">
            <h2>Event information</h2>

            <div className="info-grid">
              <Info
                icon={<CalendarDays />}
                title="Dates"
                value={event.date}
              />

              <Info
                icon={<Clock3 />}
                title="Registration deadline"
                value={event.deadline}
              />

              <Info
                icon={<MapPin />}
                title="Location"
                value={event.location}
              />

              <Info
                icon={<Users />}
                title="Team size"
                value={event.teamSize}
              />

              <Info
                icon={<Award />}
                title="Prize"
                value={event.prize}
              />

              <Info
                icon={<Globe2 />}
                title="Mode"
                value={event.mode}
              />
            </div>
          </section>

          <section className="content-card">
            <h2>Eligibility</h2>

            <div className="eligibility">
              <CheckCircle2 />
              {event.eligibility}
            </div>
          </section>
        </div>

        <aside>
          <div className="source-card">
            <div className="source-title">
              <ShieldCheck />

              <div>
                <b>Source verification</b>
                <small>Evidence & freshness</small>
              </div>
            </div>

            <div className="source-row">
              <span>Status</span>
              <b>Authoritative</b>
            </div>

            <div className="source-row">
              <span>Last verified</span>
              <b>{event.verified}</b>
            </div>

            <a
              href="#"
              onClick={(e) => e.preventDefault()}
            >
              View source <ExternalLink size={14} />
            </a>
          </div>

          <div className="source-card">
            <h3>Quick facts</h3>

            <div className="tags big-tags">
              {event.tags.map((t) => (
                <span key={t}>{t}</span>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function Info({ icon, title, value }) {
  return (
    <div className="info-item">
      <span className="info-icon">{icon}</span>

      <div>
        <small>{title}</small>
        <b>{value}</b>
      </div>
    </div>
  );
}

function Predictions() {
  return (
    <div className="page">
      <div className="page-header prediction-head">
        <div>
          <p className="eyebrow">
            <Sparkles size={14} />
            AI INTELLIGENCE
          </p>

          <h1>Predictions</h1>

          <p>
            Early signals for hackathons that may be announced
            soon.
          </p>
        </div>

        <div className="model-pill">
          <BrainCircuit size={16} />
          Model v1.0.0
        </div>
      </div>

      <div className="notice">
        <ShieldCheck size={20} />

        <div>
          <b>
            Predictions are not official announcements.
          </b>

          <p>
            Every forecast includes a confidence level, evidence
            signals and a date window. Never treat a prediction
            as a confirmed event.
          </p>
        </div>
      </div>

      <div className="prediction-grid">
        {predictions.map((p) => (
          <article className="prediction-card" key={p.id}>
            <div className="prediction-card-top">
              <span
                className={`confidence ${p.confidence.toLowerCase()}`}
              >
                <TrendingUp size={14} />
                {p.confidence} confidence
              </span>

              <b>{Math.round(p.probability * 100)}%</b>
            </div>

            <p className="mini-label">{p.organizer}</p>

            <h2>{p.event}</h2>

            <div className="window">
              <CalendarDays size={17} />

              <div>
                <small>Predicted window</small>
                <b>{p.window}</b>
              </div>
            </div>

            <div className="signals">
              <b>Why we think so</b>

              {p.signals.map((s, i) => (
                <div key={i}>
                  <CheckCircle2 size={15} />
                  {s}
                </div>
              ))}
            </div>

            <div className="model-row">
              Model {p.model}
              <span>Generated recently</span>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function OrganizerProfile() {
  const { name = 'microsoft' } = useParams();

  const org =
    organizers[name] || organizers.microsoft;

  return (
    <div className="page">
      <Link to="/explore" className="back-link">
        ← Back to explore
      </Link>

      <section className="org-hero">
        <div className="org-avatar">{org.initials}</div>

        <div>
          <p className="eyebrow">ORGANIZER PROFILE</p>

          <h1>{org.name}</h1>

          <p>{org.description}</p>

          <a
            href="#"
            onClick={(e) => e.preventDefault()}
          >
            {org.domain} <ExternalLink size={14} />
          </a>
        </div>

        <button className="secondary-btn" type="button">
          Follow organizer
        </button>
      </section>

      <div className="org-stats">
        <div>
          <b>{org.events.length}</b>
          <span>Past events</span>
        </div>

        <div>
          <b>3.8 yrs</b>
          <span>Recurrence history</span>
        </div>

        <div>
          <b>High</b>
          <span>Prediction confidence</span>
        </div>

        <div>
          <b>Global</b>
          <span>Coverage</span>
        </div>
      </div>

      <div className="detail-grid org-grid">
        <section className="content-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">HISTORY</p>
              <h2>Event timeline</h2>
            </div>
          </div>

          <div className="timeline">
            {org.events.map((e, i) => (
              <div className="timeline-item" key={i}>
                <div className="timeline-dot" />

                <div>
                  <span>{e.year}</span>
                  <h3>{e.title}</h3>
                  <StatusBadge status={e.status} />
                </div>
              </div>
            ))}
          </div>
        </section>

        <aside>
          <div className="content-card">
            <h3>Recurrence pattern</h3>

            <div className="recurrence">
              <div className="bar b1" />
              <div className="bar b2" />
              <div className="bar b3" />
              <div className="bar b4" />
            </div>

            <p>
              Historical activity suggests this organizer
              regularly runs technology-focused challenges.
              Future predictions use this recurrence along with
              current signals.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}

/* =========================================================
   TEAM DASHBOARD
   ========================================================= */

function DashboardView() {
  const { user, logout, isLoading } = useAuth();

  return (
    <div className="auth-page-container">
      <div className="auth-card auth-dashboard-card">
        <div className="auth-brand-badge">
          <span
            className="auth-radar-pulse"
            aria-hidden="true"
          />

          <span className="auth-brand-text">
            HACKATHON RADAR AI
          </span>
        </div>

        <div className="auth-header">
          <div className="auth-avatar-circle">
            {user?.name
              ? user.name.charAt(0).toUpperCase()
              : 'U'}
          </div>

          <h1 className="auth-title">
            Welcome, {user?.name || 'Hacker'}!
          </h1>

          <p className="auth-subtitle">
            You are signed in to Hackathon Radar AI.
          </p>
        </div>

        <div className="auth-session-details">
          <div className="auth-session-row">
            <span className="auth-session-label">
              Email:
            </span>

            <span className="auth-session-val">
              {user?.email}
            </span>
          </div>

          <div className="auth-session-row">
            <span className="auth-session-label">
              Status:
            </span>

            <span className="auth-status-pill">
              <span className="auth-status-dot" />
              Authenticated
            </span>
          </div>
        </div>

        <div className="auth-dashboard-actions">
          <button
            type="button"
            onClick={logout}
            disabled={isLoading}
            className="auth-submit-btn auth-btn-secondary"
            id="dashboard-logout-btn"
          >
            {isLoading ? 'Signing Out...' : 'Sign Out'}
          </button>
        </div>
      </div>
    </div>
  );
}

function ProtectedDashboard() {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <DashboardView />;
}

/* =========================================================
   MAIN APPLICATION
   ========================================================= */

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Team authentication */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/forgot-password"
            element={<ForgotPassword />}
          />

          {/* Team protected dashboard */}
          <Route
            path="/"
            element={<ProtectedDashboard />}
          />

          {/* Public pages from original project */}
          <Route
            path="/home"
            element={
              <Layout>
                <Home />
              </Layout>
            }
          />

          <Route
            path="/explore"
            element={
              <Layout>
                <Explore />
              </Layout>
            }
          />

          <Route
            path="/event/:id"
            element={
              <Layout>
                <EventDetails />
              </Layout>
            }
          />

          <Route
            path="/predictions"
            element={
              <Layout>
                <Predictions />
              </Layout>
            }
          />

          <Route
            path="/organizer/:name"
            element={
              <Layout>
                <OrganizerProfile />
              </Layout>
            }
          />

          {/* Unknown routes */}
          <Route
            path="*"
            element={<Navigate to="/home" replace />}
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}