import React, { useMemo, useState, useEffect } from "react";
import { Link, NavLink, Route, Routes, useNavigate, useParams, useLocation } from "react-router-dom";
import {
  Search, Home as HomeIcon, Compass, Sparkles, Building2, Bookmark,
  CalendarDays, MapPin, Users, ArrowRight, CheckCircle2, Clock3,
  ExternalLink, SlidersHorizontal, ChevronDown, Bell, Menu, X,
  BrainCircuit, ShieldCheck, TrendingUp, Award, Globe2, LayoutDashboard,
  Share2, Heart, Filter, Flame, Zap, Trophy, Briefcase, GraduationCap,
  ArrowUpRight, Check, Copy, AlertCircle, RefreshCw, Layers, Grid, List
} from "lucide-react";
import { events, predictions, organizers } from "./data";
import AdminRouter from "./Admin";
import {
  AceternitySpotlight,
  TextGenerateEffect,
  HeroHighlight,
  PlaceholdersAndVanishInput,
  HeroInteractiveRadar,
  CardSpotlightWrapper,
  MovingBorderBox,
  TracingBeamTimeline,
  AnimatedCounter,
  LiveRadarSection,
  MagneticButton
} from "./AceternityUI";

// ─── Toast System Context / Hook ────────────────────────────────────────────────
const ToastContext = React.createContext({
  showToast: () => {}
});

function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const showToast = (message, type = "info") => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3600);
  };

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="toast-container" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast-card toast-${t.type}`}>
            <div className="toast-icon">
              {t.type === "success" && <CheckCircle2 size={18} />}
              {t.type === "info" && <Sparkles size={18} />}
              {t.type === "alert" && <Flame size={18} />}
            </div>
            <div className="toast-text">{t.message}</div>
            <button className="toast-close" onClick={() => removeToast(t.id)}>
              <X size={14} />
            </button>
            <div className="toast-progress" />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function useToast() {
  return React.useContext(ToastContext);
}

// ─── Live Countdown Hook ────────────────────────────────────────────────────────
function useCountdown(targetDays = 4) {
  const [timeLeft, setTimeLeft] = useState({
    days: targetDays,
    hours: 14,
    minutes: 32,
    seconds: 45
  });

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev.seconds > 0) {
          return { ...prev, seconds: prev.seconds - 1 };
        }
        if (prev.minutes > 0) {
          return { ...prev, minutes: prev.minutes - 1, seconds: 59 };
        }
        if (prev.hours > 0) {
          return { ...prev, hours: prev.hours - 1, minutes: 59, seconds: 59 };
        }
        if (prev.days > 0) {
          return { ...prev, days: prev.days - 1, hours: 23, minutes: 59, seconds: 59 };
        }
        return prev;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return timeLeft;
}

// ─── Global State for Bookmarked Events ─────────────────────────────────────────
const SavedContext = React.createContext({
  savedIds: new Set(),
  toggleSaved: () => {},
  isSaved: () => false
});

function SavedProvider({ children }) {
  const [savedIds, setSavedIds] = useState(new Set(["1", "2"]));

  const toggleSaved = (id) => {
    setSavedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const isSaved = (id) => savedIds.has(id);

  return (
    <SavedContext.Provider value={{ savedIds, toggleSaved, isSaved }}>
      {children}
    </SavedContext.Provider>
  );
}

function useSaved() {
  return React.useContext(SavedContext);
}

// ─── Registration Modal ─────────────────────────────────────────────────────────
function RegistrationModal({ event, isOpen, onClose }) {
  const { showToast } = useToast();
  const [step, setStep] = useState(1);
  const [teamType, setTeamType] = useState("team");
  const [track, setTrack] = useState(event?.tags?.[0] || "Generative AI");
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen || !event) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitting(true);
    setTimeout(() => {
      setSubmitting(false);
      setStep(2);
      showToast(`Successfully registered for ${event.title}! 🎉`, "success");
    }, 700);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>
          <X size={20} />
        </button>

        {step === 1 ? (
          <div>
            <div className="modal-badge">
              <span className="live-indicator-dot" /> Registration Open
            </div>
            <h2 className="modal-title">Register for {event.title}</h2>
            <p className="modal-subtitle">
              Hosted by <b>{event.organizer}</b> · Prize pool: <span className="highlight-prize">{event.prize}</span>
            </p>

            <form onSubmit={handleSubmit} className="modal-form">
              <div className="form-group">
                <label>Participation Mode</label>
                <div className="segmented-control">
                  <button
                    type="button"
                    className={teamType === "solo" ? "active" : ""}
                    onClick={() => setTeamType("solo")}
                  >
                    Solo Hacker
                  </button>
                  <button
                    type="button"
                    className={teamType === "team" ? "active" : ""}
                    onClick={() => setTeamType("team")}
                  >
                    Team ({event.teamSize})
                  </button>
                  <button
                    type="button"
                    className={teamType === "matchmaking" ? "active" : ""}
                    onClick={() => setTeamType("matchmaking")}
                  >
                    Find Teammates
                  </button>
                </div>
              </div>

              <div className="form-group">
                <label>Primary Track / Theme</label>
                <select value={track} onChange={(e) => setTrack(e.target.value)}>
                  {event.tags.map((t) => (
                    <option key={t} value={t}>{t} Specialization</option>
                  ))}
                  <option value="Open Innovation">Open Innovation Track</option>
                </select>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Full Name</label>
                  <input type="text" placeholder="Nakul King" defaultValue="Nakul King" required />
                </div>
                <div className="form-group">
                  <label>GitHub / Portfolio URL</label>
                  <input type="text" placeholder="https://github.com/..." defaultValue="https://github.com/nakul" required />
                </div>
              </div>

              <div className="modal-perks">
                <div className="perk-item">
                  <CheckCircle2 size={16} /> Free compute credits & API access key
                </div>
                <div className="perk-item">
                  <CheckCircle2 size={16} /> Official participant digital credentials
                </div>
                <div className="perk-item">
                  <CheckCircle2 size={16} /> Discord community networking channel
                </div>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={onClose}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? (
                    <>
                      <RefreshCw size={16} className="spin" /> Registering...
                    </>
                  ) : (
                    <>
                      Confirm Free Registration <ArrowRight size={16} />
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        ) : (
          <div className="modal-success-state">
            <div className="success-icon-badge">
              <Trophy size={36} />
            </div>
            <h2>You're in the Hackathon!</h2>
            <p>
              Your participant registration for <b>{event.title}</b> is confirmed. Check your email for API access codes, Discord invites, and submission links.
            </p>
            <div className="ticket-summary">
              <div>
                <small>Event</small>
                <b>{event.title}</b>
              </div>
              <div>
                <small>Deadline</small>
                <b>{event.deadline}</b>
              </div>
              <div>
                <small>Format</small>
                <b>{event.mode} ({event.location})</b>
              </div>
            </div>
            <button className="btn-primary full-width" onClick={onClose}>
              Done & Explore More
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Status & Category Badges ───────────────────────────────────────────────────
function StatusPill({ status, badgeType }) {
  if (badgeType === "live" || status === "Live Now") {
    return (
      <span className="status-pill status-live">
        <span className="live-ping" />
        <span className="live-dot" />
        LIVE NOW
      </span>
    );
  }
  if (badgeType === "urgent" || status === "Closing Soon") {
    return (
      <span className="status-pill status-urgent">
        <Flame size={12} />
        CLOSING SOON
      </span>
    );
  }
  if (badgeType === "hiring" || status === "Hiring Track") {
    return (
      <span className="status-pill status-hiring">
        <Briefcase size={12} />
        HIRING TRACK
      </span>
    );
  }
  if (status === "Upcoming") {
    return (
      <span className="status-pill status-upcoming">
        <Clock3 size={12} />
        UPCOMING
      </span>
    );
  }
  return (
    <span className="status-pill status-default">
      <CheckCircle2 size={12} />
      {status}
    </span>
  );
}

// ─── Interactive Hackathon Card (HackerEarth Style) ─────────────────────────────
function EventCard({ event, onRegister, viewMode = "grid" }) {
  const { isSaved, toggleSaved } = useSaved();
  const { showToast } = useToast();
  const saved = isSaved(event.id);
  const countdown = useCountdown(event.deadlineDays || 4);

  const handleSave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    toggleSaved(event.id);
    showToast(
      saved ? `Removed ${event.title} from saved` : `Saved ${event.title} to your radar! 🎯`,
      saved ? "info" : "success"
    );
  };

  const handleShare = (e) => {
    e.preventDefault();
    e.stopPropagation();
    navigator.clipboard?.writeText(window.location.origin + `/event/${event.id}`);
    showToast(`Shareable challenge link copied! 📋`, "info");
  };

  if (viewMode === "list") {
    return (
      <article className="event-list-row">
        <div className={`list-logo-mark ${event.color}`}>
          {event.organizerInitials || event.organizer.slice(0, 2)}
        </div>
        <div className="list-main-info">
          <div className="list-header-row">
            <StatusPill status={event.status} badgeType={event.badgeType} />
            <span className="list-organizer-chip">
              <Building2 size={12} /> {event.organizer}
            </span>
            <span className="list-time-badge">
              <Clock3 size={12} /> {countdown.days}d {countdown.hours}h left
            </span>
          </div>
          <Link to={`/event/${event.id}`} className="list-title">
            {event.title}
          </Link>
          <div className="list-tags-row">
            {event.tags.slice(0, 3).map((tag) => (
              <span key={tag} className="tag-pill">{tag}</span>
            ))}
            <span className="meta-text"><Users size={12} /> {event.participants?.toLocaleString()} registered</span>
            <span className="meta-text"><MapPin size={12} /> {event.location}</span>
          </div>
        </div>
        <div className="list-prize-action">
          <div className="list-prize-col">
            <small>Prize Pool</small>
            <b>{event.prize}</b>
          </div>
          <div className="list-actions-group">
            <button className={`icon-action-btn ${saved ? "active" : ""}`} onClick={handleSave} title="Bookmark">
              <Bookmark size={16} fill={saved ? "currentColor" : "none"} />
            </button>
            <button className="btn-secondary btn-sm" onClick={() => onRegister(event)}>
              Register
            </button>
            <Link to={`/event/${event.id}`} className="btn-primary btn-sm">
              View <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </article>
    );
  }

  return (
    <CardSpotlightWrapper className="event-card-spotlight-item">
      <article className="event-card-v2">
        <div className="card-top-banner">
          <div className="banner-badges">
            <StatusPill status={event.status} badgeType={event.badgeType} />
            {event.featured && (
              <span className="featured-pill">
                <Sparkles size={11} /> Featured
              </span>
            )}
            <span className="ai-match-score-pill">
              <Sparkles size={11} /> {event.aiMatchScore || 95}% Match
            </span>
          </div>
          <div className="banner-actions">
            <button
              className={`card-tool-btn ${saved ? "saved-active" : ""}`}
              onClick={handleSave}
              title={saved ? "Remove bookmark" : "Save challenge"}
            >
              <Bookmark size={15} fill={saved ? "currentColor" : "none"} />
            </button>
            <button className="card-tool-btn" onClick={handleShare} title="Copy link">
              <Share2 size={15} />
            </button>
          </div>
        </div>

        <div className="card-body-content">
          <div className="organizer-header-row">
            <div className={`org-avatar-chip ${event.color}`}>
              {event.organizerInitials || event.organizer.slice(0, 2)}
            </div>
            <div className="org-details">
              <Link to={`/organizer/${event.organizerKey || "microsoft"}`} className="org-link">
                {event.organizer} <ArrowUpRight size={12} />
              </Link>
              <span className="platform-label">{event.platform || "Official"}</span>
            </div>
          </div>

          <Link to={`/event/${event.id}`} className="card-title-link">
            {event.title}
          </Link>

          <p className="card-desc-snippet">{event.description}</p>

          <div className="card-metrics-grid">
            <div className="metric-box">
              <div className="metric-icon prize-icon"><Trophy size={14} /></div>
              <div>
                <small>Prizes</small>
                <b>{event.prize}</b>
              </div>
            </div>
            <div className="metric-box">
              <div className="metric-icon"><Users size={14} /></div>
              <div>
                <small>Hackers</small>
                <b>{event.participants ? `${(event.participants / 1000).toFixed(1)}k` : "1.2k"}</b>
              </div>
            </div>
            <div className="metric-box">
              <div className="metric-icon"><Clock3 size={14} /></div>
              <div>
                <small>Closes in</small>
                <b>{countdown.days}d {countdown.hours}h</b>
              </div>
            </div>
          </div>

          {/* Progress Bar for Registration Activity */}
          <div className="activity-meter">
            <div className="meter-header">
              <span>Registration Activity</span>
              <b>{Math.min(96, Math.max(45, 100 - (event.deadlineDays || 4) * 3))}% filled</b>
            </div>
            <div className="meter-track">
              <div
                className="meter-fill"
                style={{ width: `${Math.min(96, Math.max(45, 100 - (event.deadlineDays || 4) * 3))}%` }}
              />
            </div>
          </div>

          <div className="tags-cloud">
            {event.tags.slice(0, 3).map((tag) => (
              <span key={tag} className="tag-chip">{tag}</span>
            ))}
            {event.tags.length > 3 && (
              <span className="tag-more">+{event.tags.length - 3}</span>
            )}
          </div>
        </div>

        <div className="card-footer-actions">
          <button className="register-quick-btn" onClick={() => onRegister(event)}>
            <Zap size={14} /> Register Now
          </button>
          <Link to={`/event/${event.id}`} className="details-quick-btn">
            Details <ArrowRight size={14} />
          </Link>
        </div>
      </article>
    </CardSpotlightWrapper>
  );
}

// ─── Header & Navigation ────────────────────────────────────────────────────────
function Layout({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { savedIds } = useSaved();
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 40);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const nav = [
    { to: "/", label: "Home", icon: HomeIcon },
    { to: "/explore", label: "Explore Hackathons", icon: Compass },
    { to: "/predictions", label: "AI Predictions", icon: Sparkles, badge: "AI" },
    { to: "/organizer/microsoft", label: "Organizers", icon: Building2 },
    { to: "/admin", label: "Admin Console", icon: LayoutDashboard },
  ];

  const recentNotifications = [
    { id: 1, title: "New $150K Gemini Hackathon Live", time: "10m ago", icon: Flame },
    { id: 2, title: "Microsoft Imagine Cup closes soon", time: "2h ago", icon: Clock3 },
    { id: 3, title: "Predicted AWS Hackathon confidence increased to 88%", time: "5h ago", icon: Sparkles }
  ];

  return (
    <div className="app-shell">
      {/* Top Banner Alert Bar */}
      <div className="top-radar-ticker">
        <div className="ticker-track">
          <span className="ticker-item">
            <span className="pulse-beacon" /> <b>RADAR LIVE:</b> 28 Verified Hackathons Tracked across Google, AWS, Microsoft & OpenAI
          </span>
          <span className="ticker-divider">•</span>
          <span className="ticker-item">
            <Trophy size={13} /> <b>$1,420,000+</b> Total Active Prize Pool
          </span>
          <span className="ticker-divider">•</span>
          <span className="ticker-item">
            <Sparkles size={13} /> <b>5 New AI Predictions</b> Detected for Summer 2027
          </span>
        </div>
      </div>

      <div className={`navbar-outer-wrapper ${scrolled ? "is-scrolled" : ""}`}>
        <header className={`navbar ${scrolled ? "scrolled" : ""}`}>
          <Link className="brand" to="/">
            <div className="brand-logo-glow">
              <BrainCircuit size={22} />
            </div>
            <div className="brand-text">
              <span>Hackathon<b>Radar</b></span>
              <small>AI DISCOVERY PLATFORM</small>
            </div>
          </Link>

          <button className="mobile-menu" onClick={() => setMobileOpen(!mobileOpen)} aria-label="Toggle Navigation">
            {mobileOpen ? <X /> : <Menu />}
          </button>

          <nav className={`nav-links ${mobileOpen ? "open" : ""}`}>
            {nav.map(({ to, label, icon: Icon, badge }) => (
              <NavLink
                key={to}
                to={to}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
              >
                <Icon size={16} />
                <span>{label}</span>
                {badge && <span className="nav-mini-badge">{badge}</span>}
              </NavLink>
            ))}
          </nav>

          <div className="nav-actions">
            {/* Saved Items Quick Counter */}
            <Link to="/explore" className="saved-counter-chip" title="Saved Hackathons">
              <Bookmark size={15} />
              <span>Saved</span>
              <b className="saved-count-pill">{savedIds.size}</b>
            </Link>

            {/* Notifications Dropdown Toggle */}
            <div className="notif-wrapper">
              <button
                className={`icon-btn ${notificationsOpen ? "active" : ""}`}
                onClick={() => setNotificationsOpen(!notificationsOpen)}
                title="Recent Signals & Alerts"
              >
                <Bell size={17} />
                <span className="notif-ping-dot" />
              </button>

              {notificationsOpen && (
                <div className="notifications-popover">
                  <div className="notif-popover-header">
                    <b>Radar Notifications</b>
                    <span className="badge-new">3 New</span>
                  </div>
                  <div className="notif-list">
                    {recentNotifications.map((n) => {
                      const NIcon = n.icon;
                      return (
                        <div key={n.id} className="notif-item">
                          <div className="notif-icon-wrap"><NIcon size={14} /></div>
                          <div>
                            <p>{n.title}</p>
                            <small>{n.time}</small>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <Link
                    to="/predictions"
                    className="notif-footer-link"
                    onClick={() => setNotificationsOpen(false)}
                  >
                    View all predictive alerts <ArrowRight size={13} />
                  </Link>
                </div>
              )}
            </div>

            <div className="profile-chip">
              <div className="avatar-gradient">NK</div>
              <div className="profile-info">
                <b>Nakul King</b>
                <small>Hacker Pro</small>
              </div>
            </div>
          </div>
        </header>
      </div>

      <main>{children}</main>

      <footer className="footer-v2">
        <div className="footer-content-wrap">
          <div className="footer-brand-col">
            <div className="brand footer-brand">
              <div className="brand-logo-glow small">
                <BrainCircuit size={18} />
              </div>
              <span>Hackathon<b>Radar</b> AI</span>
            </div>
            <p className="footer-desc">
              The real-time discovery engine and predictive intelligence platform for global hackathons, coding challenges, and innovation sprints.
            </p>
            <div className="footer-social-row">
              <span className="platform-tag">Built for Developers & Innovators</span>
            </div>
          </div>

          <div className="footer-links-grid">
            <div className="footer-links-col">
              <h4>Explore</h4>
              <Link to="/explore">All Hackathons</Link>
              <Link to="/explore">Generative AI Sprints</Link>
              <Link to="/explore">Hiring Challenges</Link>
              <Link to="/predictions">AI Event Forecasts</Link>
            </div>
            <div className="footer-links-col">
              <h4>Organizers</h4>
              <Link to="/organizer/microsoft">Microsoft</Link>
              <Link to="/organizer/google">Google Developers</Link>
              <Link to="/organizer/aws">Amazon Web Services</Link>
              <Link to="/organizer/openai">OpenAI</Link>
            </div>
            <div className="footer-links-col">
              <h4>Intelligence</h4>
              <Link to="/predictions">Recurrence Radar</Link>
              <Link to="/admin">Admin Operations</Link>
              <a href="#rules" onClick={(e) => e.preventDefault()}>Verification Standards</a>
              <a href="#api" onClick={(e) => e.preventDefault()}>Data Freshness Guarantee</a>
            </div>
          </div>
        </div>

        <div className="footer-bottom-bar">
          <div>© 2027 HackathonRadar AI · Modeled after premier developer platforms like HackerEarth & Devpost</div>
          <div className="footer-status-pill">
            <span className="live-dot" /> All Pipeline Scrapers Operational (99.98% Uptime)
          </div>
        </div>
      </footer>
    </div>
  );
}

// ─── Home Page ──────────────────────────────────────────────────────────────────
function Home() {
  const [query, setQuery] = useState("");
  const [activeTab, setActiveTab] = useState("all");
  const [modalEvent, setModalEvent] = useState(null);
  const navigate = useNavigate();

  const heroCountdown = useCountdown(4);

  // Filter events according to active tab
  const displayedEvents = useMemo(() => {
    let list = events;
    if (activeTab === "live") list = list.filter((e) => e.status === "Live Now");
    if (activeTab === "upcoming") list = list.filter((e) => e.status === "Upcoming" || e.status === "Closing Soon");
    if (activeTab === "ai") list = list.filter((e) => e.category === "AI & ML" || e.tags.includes("Generative AI"));
    if (activeTab === "hiring") list = list.filter((e) => e.category === "Hiring Challenge" || e.tags.includes("Hiring Track"));
    if (query.trim()) {
      list = list.filter(
        (e) =>
          e.title.toLowerCase().includes(query.toLowerCase()) ||
          e.organizer.toLowerCase().includes(query.toLowerCase()) ||
          e.tags.some((t) => t.toLowerCase().includes(query.toLowerCase()))
      );
    }
    return list;
  }, [activeTab, query]);

  const featuredHeroEvent = events[0]; // Google Gemini AI Global Hackathon

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    navigate(`/explore?search=${encodeURIComponent(query)}`);
  };

  return (
    <div className="home-container">
      {/* ─── Hero Section with Dynamic Motion ──────────────────────────────── */}
      <section className="hero-section">
        {/* Aceternity Spotlight Cone */}
        <AceternitySpotlight className="hero-spotlight-beam" fill="#7667ff" />

        {/* Ambient Animated Glows & Grid Pattern */}
        <div className="ambient-orb orb-1" />
        <div className="ambient-orb orb-2" />
        <div className="hero-grid-pattern" />

        <div className="hero-inner">
          <div className="hero-main-col">
            <div className="hero-pill-badge">
              <span className="sparkle-icon"><Sparkles size={14} /></span>
              <span>Next-Gen Hackathon Intelligence Engine</span>
              <span className="pill-dot">•</span>
              <span className="highlight-text">Live 2027 Season</span>
            </div>

            <h1 className="hero-headline">
              <TextGenerateEffect words="Participate in" />{" "}
              <HeroHighlight>World-Class</HeroHighlight>{" "}
              <TextGenerateEffect words="Hackathons & Challenges." />
            </h1>

            <p className="hero-description">
              Find verified hackathons, compete for over <b>$1.4M+</b> in cash prizes, and uncover AI-predicted future events before they're officially announced.
            </p>

            {/* Smart Search: Aceternity Placeholders And Vanish Input */}
            <PlaceholdersAndVanishInput
              placeholders={[
                "Find AI hackathons",
                "Find hackathons under $100K",
                "Find Gemini hackathons",
                "Find hackathons in India",
                "Find beginner-friendly hackathons"
              ]}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onSubmit={handleSearchSubmit}
            />

            {/* Quick Pill Filter Suggestions */}
            <div className="quick-tags-strip">
              <span className="quick-tags-label">Trending Now:</span>
              <button type="button" onClick={() => setQuery("Gemini")} className="quick-pill">🤖 Gemini 2.0</button>
              <button type="button" onClick={() => setQuery("Azure")} className="quick-pill">⚡ Microsoft Azure</button>
              <button type="button" onClick={() => setQuery("Bedrock")} className="quick-pill">☁️ AWS Bedrock</button>
              <button type="button" onClick={() => setQuery("Hiring")} className="quick-pill">💼 Hiring Tracks</button>
              <button type="button" onClick={() => setQuery("Kaggle")} className="quick-pill">🏆 Kaggle Reasoning</button>
            </div>

            {/* Trust Badges Row */}
            <div className="trust-features-row">
              <div className="trust-feature">
                <ShieldCheck size={18} className="trust-icon-green" />
                <div>
                  <b>100% Verified Sources</b>
                  <small>No expired or spam listings</small>
                </div>
              </div>
              <div className="trust-feature">
                <BrainCircuit size={18} className="trust-icon-purple" />
                <div>
                  <b>AI Recurrence Signals</b>
                  <small>Know events weeks earlier</small>
                </div>
              </div>
              <div className="trust-feature">
                <Clock3 size={18} className="trust-icon-cyan" />
                <div>
                  <b>Hourly Data Refresh</b>
                  <small>Live deadline countdowns</small>
                </div>
              </div>
            </div>
          </div>

          {/* Aceternity Interactive World Map & 3D Globe Visual Panel */}
          <div className="hero-visual-col">
            <HeroInteractiveRadar events={events} />
          </div>
        </div>
      </section>

      {/* ─── High Stakes Metrics Strip (Aceternity Animated Counters & Spotlight) ────── */}
      <section className="metrics-strip-v2">
        <CardSpotlightWrapper className="metric-cell">
          <div className="metric-num">
            <AnimatedCounter target={1420000} prefix="$" suffix="+" duration={2000} />
          </div>
          <div className="metric-text">
            <b>Active Prize Pool</b>
            <small>Across 12 verified hackathons</small>
          </div>
        </CardSpotlightWrapper>

        <CardSpotlightWrapper className="metric-cell">
          <div className="metric-num">
            <AnimatedCounter target={115000} suffix="+" duration={2200} />
          </div>
          <div className="metric-text">
            <b>Registered Builders</b>
            <small>Global developer community</small>
          </div>
        </CardSpotlightWrapper>

        <CardSpotlightWrapper className="metric-cell">
          <div className="metric-num">
            <AnimatedCounter target={94.2} decimals={1} suffix="%" duration={1800} />
          </div>
          <div className="metric-text">
            <b>Prediction Accuracy</b>
            <small>Historical cadence model</small>
          </div>
        </CardSpotlightWrapper>

        <CardSpotlightWrapper className="metric-cell">
          <div className="metric-num">
            <AnimatedCounter target={28} suffix="+" duration={1500} />
          </div>
          <div className="metric-text">
            <b>Verified Events Tracked</b>
            <small>Multi-source ingestion engine</small>
          </div>
        </CardSpotlightWrapper>
      </section>

      {/* ─── LIVE HACKATHON RADAR (Aceternity World Map & Telemetry) ───────────── */}
      <LiveRadarSection events={events} onRegister={setModalEvent} />

      {/* ─── Featured Spotlight Banner (HackerEarth Style) ─────────────────── */}
      <section className="featured-spotlight-section">
        <div className="spotlight-card">
          <div className="spotlight-glow" />
          <div className="spotlight-content">
            <div className="spotlight-top-meta">
              <span className="spotlight-tag">
                <Flame size={14} /> CHALLENGE OF THE WEEK
              </span>
              <StatusPill status="Live Now" badgeType="live" />
              <span className="spotlight-org">
                <Building2 size={13} /> {featuredHeroEvent.organizer}
              </span>
            </div>

            <h2 className="spotlight-title">{featuredHeroEvent.title}</h2>
            <p className="spotlight-desc">{featuredHeroEvent.description}</p>

            <div className="spotlight-highlights-row">
              {featuredHeroEvent.highlights.map((h, i) => (
                <div key={i} className="highlight-pill">
                  <CheckCircle2 size={14} /> {h}
                </div>
              ))}
            </div>

            {/* Countdown Clock Display */}
            <div className="countdown-widget">
              <div className="countdown-label">
                <Clock3 size={15} /> Registration & Submission Closes In:
              </div>
              <div className="countdown-digits">
                <div className="digit-box">
                  <b>{String(heroCountdown.days).padStart(2, "0")}</b>
                  <small>DAYS</small>
                </div>
                <span className="colon">:</span>
                <div className="digit-box">
                  <b>{String(heroCountdown.hours).padStart(2, "0")}</b>
                  <small>HOURS</small>
                </div>
                <span className="colon">:</span>
                <div className="digit-box">
                  <b>{String(heroCountdown.minutes).padStart(2, "0")}</b>
                  <small>MINS</small>
                </div>
                <span className="colon">:</span>
                <div className="digit-box accent-box">
                  <b>{String(heroCountdown.seconds).padStart(2, "0")}</b>
                  <small>SECS</small>
                </div>
              </div>
            </div>

            <div className="spotlight-cta-row">
              <button
                className="btn-primary btn-lg"
                onClick={() => setModalEvent(featuredHeroEvent)}
              >
                <Zap size={18} /> Register for Challenge
              </button>
              <Link to={`/event/${featuredHeroEvent.id}`} className="btn-secondary btn-lg">
                View Full Details & Tracks <ArrowRight size={17} />
              </Link>
              <div className="registered-stack">
                <div className="avatar-group">
                  <span className="avatar-mini a1">JD</span>
                  <span className="avatar-mini a2">AR</span>
                  <span className="avatar-mini a3">SK</span>
                  <span className="avatar-mini a4">+</span>
                </div>
                <small><b>7,840+</b> hackers registered</small>
              </div>
            </div>
          </div>

          <div className="spotlight-prize-card">
            <div className="prize-badge-card">
              <div className="trophy-glow"><Trophy size={42} /></div>
              <small>Grand Prize Pool</small>
              <div className="big-prize-value">{featuredHeroEvent.prize}</div>
              <div className="prize-perks-list">
                <div><span>1st Place</span> <b>$60,000</b></div>
                <div><span>2nd Place</span> <b>$35,000</b></div>
                <div><span>3rd Place</span> <b>$20,000</b></div>
                <div><span>Tracks</span> <b>$35,000</b></div>
              </div>
              <div className="sponsor-tag">Sponsored by Google DeepMind</div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Hackathons Explorer Grid (HackerEarth Navigation Tabs) ────────── */}
      <section className="section-container">
        <div className="section-header-flex">
          <div>
            <div className="section-eyebrow">
              <Flame size={14} /> LIVE & UPCOMING OPPORTUNITIES
            </div>
            <h2 className="section-heading">Browse Active Challenges</h2>
            <p className="section-subtext">
              Filter through verified competitions across AI, Web3, Cloud, and Hiring pipelines.
            </p>
          </div>
          <Link to="/explore" className="view-all-link">
            <span>Explore all {events.length} hackathons</span>
            <ArrowRight size={16} />
          </Link>
        </div>

        {/* HackerEarth Filter Pills Bar */}
        <div className="tabs-bar-v2">
          <div className="tabs-scroller">
            <button
              className={`tab-btn ${activeTab === "all" ? "active" : ""}`}
              onClick={() => setActiveTab("all")}
            >
              All Challenges <span className="tab-count">{events.length}</span>
            </button>
            <button
              className={`tab-btn ${activeTab === "live" ? "active" : ""}`}
              onClick={() => setActiveTab("live")}
            >
              <span className="live-dot" /> Live Now <span className="tab-count">7</span>
            </button>
            <button
              className={`tab-btn ${activeTab === "upcoming" ? "active" : ""}`}
              onClick={() => setActiveTab("upcoming")}
            >
              <Clock3 size={13} /> Upcoming & Closing <span className="tab-count">3</span>
            </button>
            <button
              className={`tab-btn ${activeTab === "ai" ? "active" : ""}`}
              onClick={() => setActiveTab("ai")}
            >
              <Sparkles size={13} /> AI & Machine Learning <span className="tab-count">6</span>
            </button>
            <button
              className={`tab-btn ${activeTab === "hiring" ? "active" : ""}`}
              onClick={() => setActiveTab("hiring")}
            >
              <Briefcase size={13} /> Hiring Challenges <span className="tab-count">2</span>
            </button>
          </div>
        </div>

        {/* Hackathon Cards Grid */}
        <div className="events-grid-responsive">
          {displayedEvents.slice(0, 6).map((e) => (
            <EventCard key={e.id} event={e} onRegister={setModalEvent} />
          ))}
        </div>

        <div className="view-more-cta-wrapper">
          <Link to="/explore" className="btn-secondary btn-lg">
            <span>View All {events.length} Hackathons & Apply Filters</span>
            <ArrowRight size={16} />
          </Link>
        </div>
      </section>

      {/* ─── Top Organizers Showcase ────────────────────────────────────────── */}
      <section className="section-container organizers-section">
        <div className="section-header-flex">
          <div>
            <div className="section-eyebrow">
              <Building2 size={14} /> TRUSTED SPONSORS
            </div>
            <h2 className="section-heading">Top Sponsoring Tech Giants</h2>
            <p className="section-subtext">
              Track annual recurring programs from organizations that sponsor verified six-figure prize pools.
            </p>
          </div>
        </div>

        <div className="organizers-grid">
          {Object.values(organizers).map((org) => (
            <div key={org.name} className="organizer-showcase-card">
              <div className="org-card-top">
                <div className="org-big-avatar" style={{ background: org.logoColor + "22", color: org.logoColor, borderColor: org.logoColor + "44" }}>
                  {org.initials}
                </div>
                <div className="org-meta-info">
                  <Link to={`/organizer/${org.key}`} className="org-meta-name">
                    {org.name} <ArrowUpRight size={13} />
                  </Link>
                  <small>{org.type}</small>
                </div>
                {org.hiringPartner && (
                  <span className="hiring-badge" title="Direct hiring pipeline">
                    <Briefcase size={11} /> Hiring
                  </span>
                )}
              </div>

              <p className="org-description-snippet">{org.description}</p>

              <div className="org-stats-row">
                <div>
                  <small>Active Events</small>
                  <b>{org.activeHackathons}</b>
                </div>
                <div>
                  <small>Total Prizes</small>
                  <b className="green-text">{org.totalPrizesGiven}</b>
                </div>
              </div>

              <div className="org-card-footer">
                <Link to={`/organizer/${org.key}`} className="btn-secondary full-width btn-sm">
                  View Organization Profile & Timeline
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── Predictive Radar Section ───────────────────────────────────────── */}
      <section className="section-container predictive-section">
        <div className="prediction-hero-banner">
          <div className="prediction-hero-glow" />
          <div className="prediction-hero-content">
            <div className="section-eyebrow">
              <Sparkles size={14} /> PROPRIETARY AI CADENCE ENGINE
            </div>
            <h2 className="prediction-banner-title">
              Know what's launching <span>weeks before</span> it's officially announced.
            </h2>
            <p className="prediction-banner-desc">
              Hackathon Radar aggregates seasonal cadence, developer blog announcements, and domain registrations to calculate statistical recurrence probabilities with high accuracy.
            </p>
            <div className="prediction-signals-row">
              <div className="signal-bullet">
                <CheckCircle2 size={16} /> Historical 5-year seasonal correlation
              </div>
              <div className="signal-bullet">
                <CheckCircle2 size={16} /> GitHub repository activity tracking
              </div>
              <div className="signal-bullet">
                <CheckCircle2 size={16} /> Sponsor budget release cycles
              </div>
            </div>
            <Link to="/predictions" className="btn-primary btn-lg">
              Explore Active AI Predictions ({predictions.length}) <ArrowRight size={17} />
            </Link>
          </div>

          <div className="prediction-mini-cards">
            {predictions.slice(0, 2).map((p) => (
              <MovingBorderBox key={p.id} className="prediction-moving-border-card">
                <div className="prediction-spotlight-item">
                  <div className="spotlight-pred-header">
                    <span className="pred-org-label">{p.organizer}</span>
                    <span className="pred-score-pill">
                      <TrendingUp size={12} /> {Math.round(p.probability * 100)}% Match
                    </span>
                  </div>
                  <h4 className="pred-item-title">{p.event}</h4>
                  <div className="pred-window-row">
                    <CalendarDays size={14} /> Expected Window: <b>{p.window}</b>
                  </div>
                  <div className="pred-signals-step-list">
                    {p.signals.slice(0, 2).map((sig, sIdx) => (
                      <div key={sIdx} className="pred-signal-step-pill">
                        <CheckCircle2 size={13} />
                        <span>{sig}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </MovingBorderBox>
            ))}
          </div>
        </div>
      </section>

      {/* Registration Modal */}
      <RegistrationModal
        event={modalEvent}
        isOpen={Boolean(modalEvent)}
        onClose={() => setModalEvent(null)}
      />
    </div>
  );
}

// ─── Explore Page ───────────────────────────────────────────────────────────────
function Explore() {
  const [locationState] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get("search") || "";
  });

  const [query, setQuery] = useState(locationState);
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [selectedMode, setSelectedMode] = useState("All");
  const [selectedSort, setSelectedSort] = useState("Recommended");
  const [selectedPrizeFilter, setSelectedPrizeFilter] = useState("All");
  const [viewMode, setViewMode] = useState("grid");
  const [modalEvent, setModalEvent] = useState(null);

  const categories = ["All", "AI & ML", "Hackathon", "Hiring Challenge"];
  const modes = ["All", "Remote", "Hybrid"];
  const prizeRanges = ["All", ">$50K", ">$100K"];

  const filteredEvents = useMemo(() => {
    let list = events.filter((e) => {
      const matchQuery =
        !query.trim() ||
        (e.title + e.organizer + e.theme + e.tags.join(" ")).toLowerCase().includes(query.toLowerCase());
      const matchCategory =
        selectedCategory === "All" || e.category === selectedCategory;
      const matchMode = selectedMode === "All" || e.mode === selectedMode;
      const matchPrize =
        selectedPrizeFilter === "All" ||
        (selectedPrizeFilter === ">$50K" && (e.prizeNumeric || 0) >= 50000) ||
        (selectedPrizeFilter === ">$100K" && (e.prizeNumeric || 0) >= 100000);

      return matchQuery && matchCategory && matchMode && matchPrize;
    });

    if (selectedSort === "Prize: High to Low") {
      list = [...list].sort((a, b) => (b.prizeNumeric || 0) - (a.prizeNumeric || 0));
    } else if (selectedSort === "Ending Soonest") {
      list = [...list].sort((a, b) => (a.deadlineDays || 99) - (b.deadlineDays || 99));
    } else if (selectedSort === "Most Participants") {
      list = [...list].sort((a, b) => (b.participants || 0) - (a.participants || 0));
    }

    return list;
  }, [query, selectedCategory, selectedMode, selectedSort, selectedPrizeFilter]);

  const clearAllFilters = () => {
    setQuery("");
    setSelectedCategory("All");
    setSelectedMode("All");
    setSelectedPrizeFilter("All");
    setSelectedSort("Recommended");
  };

  return (
    <div className="explore-page-wrapper">
      {/* Page Header */}
      <div className="explore-hero-strip">
        <div className="explore-hero-inner">
          <div className="section-eyebrow">
            <Compass size={14} /> LIVE DATABASE
          </div>
          <h1 className="explore-page-title">Explore Hackathons</h1>
          <p className="explore-page-subtitle">
            Filter verified hackathons by tech stack, prize size, hiring eligibility, and format.
          </p>
        </div>
      </div>

      <div className="explore-main-container">
        {/* Top Filter & Command Bar */}
        <div className="explore-controls-bar">
          <div className="search-field-wrap">
            <Search size={18} />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by keywords, sponsors, or tags..."
            />
            {query && (
              <button className="clear-search-btn" onClick={() => setQuery("")}>
                <X size={14} />
              </button>
            )}
          </div>

          <div className="controls-right-group">
            <div className="select-picker">
              <label>Sort:</label>
              <select value={selectedSort} onChange={(e) => setSelectedSort(e.target.value)}>
                <option>Recommended</option>
                <option>Prize: High to Low</option>
                <option>Ending Soonest</option>
                <option>Most Participants</option>
              </select>
            </div>

            {/* Grid / List View Switcher */}
            <div className="view-switcher-pills">
              <button
                className={`switch-btn ${viewMode === "grid" ? "active" : ""}`}
                onClick={() => setViewMode("grid")}
                title="Grid view"
              >
                <Grid size={16} />
              </button>
              <button
                className={`switch-btn ${viewMode === "list" ? "active" : ""}`}
                onClick={() => setViewMode("list")}
                title="List view"
              >
                <List size={16} />
              </button>
            </div>
          </div>
        </div>

        <div className="explore-content-layout">
          {/* Sticky Sidebar Filters */}
          <aside className="explore-sidebar">
            <div className="sidebar-filter-block">
              <div className="filter-header-row">
                <h3>Filters</h3>
                {(query || selectedCategory !== "All" || selectedMode !== "All" || selectedPrizeFilter !== "All") && (
                  <button className="reset-btn" onClick={clearAllFilters}>
                    Reset all
                  </button>
                )}
              </div>

              {/* Category Radio / Pills */}
              <div className="filter-group">
                <label className="filter-group-title">Challenge Type</label>
                <div className="pill-options-list">
                  {categories.map((c) => (
                    <button
                      key={c}
                      className={`filter-chip ${selectedCategory === c ? "active" : ""}`}
                      onClick={() => setSelectedCategory(c)}
                    >
                      <span>{c}</span>
                      {selectedCategory === c && <Check size={13} />}
                    </button>
                  ))}
                </div>
              </div>

              {/* Format Filter */}
              <div className="filter-group">
                <label className="filter-group-title">Location & Mode</label>
                <div className="pill-options-list">
                  {modes.map((m) => (
                    <button
                      key={m}
                      className={`filter-chip ${selectedMode === m ? "active" : ""}`}
                      onClick={() => setSelectedMode(m)}
                    >
                      <span>{m}</span>
                      {selectedMode === m && <Check size={13} />}
                    </button>
                  ))}
                </div>
              </div>

              {/* Prize Pool Filter */}
              <div className="filter-group">
                <label className="filter-group-title">Prize Pool</label>
                <div className="pill-options-list">
                  {prizeRanges.map((p) => (
                    <button
                      key={p}
                      className={`filter-chip ${selectedPrizeFilter === p ? "active" : ""}`}
                      onClick={() => setSelectedPrizeFilter(p)}
                    >
                      <span>{p}</span>
                      {selectedPrizeFilter === p && <Check size={13} />}
                    </button>
                  ))}
                </div>
              </div>

              {/* Popular Tech Filters */}
              <div className="filter-group">
                <label className="filter-group-title">Filter by Technology</label>
                <div className="tags-pill-wrap">
                  {["Gemini", "Azure", "Bedrock", "NVIDIA", "PyTorch", "OpenAI", "Web3"].map((t) => (
                    <button
                      key={t}
                      className={`tag-filter-btn ${query === t ? "active" : ""}`}
                      onClick={() => setQuery(query === t ? "" : t)}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </aside>

          {/* Results Column */}
          <div className="explore-results-column">
            <div className="results-status-bar">
              <span className="results-counter">
                Showing <b>{filteredEvents.length}</b> verified challenges
              </span>
              <div className="active-filter-tags">
                {selectedCategory !== "All" && (
                  <span className="active-tag">
                    Type: {selectedCategory}
                    <button onClick={() => setSelectedCategory("All")}><X size={12} /></button>
                  </span>
                )}
                {selectedMode !== "All" && (
                  <span className="active-tag">
                    Mode: {selectedMode}
                    <button onClick={() => setSelectedMode("All")}><X size={12} /></button>
                  </span>
                )}
                {selectedPrizeFilter !== "All" && (
                  <span className="active-tag">
                    Prize: {selectedPrizeFilter}
                    <button onClick={() => setSelectedPrizeFilter("All")}><X size={12} /></button>
                  </span>
                )}
              </div>
            </div>

            {filteredEvents.length > 0 ? (
              <div className={viewMode === "grid" ? "events-grid-responsive" : "events-list-vertical"}>
                {filteredEvents.map((e) => (
                  <EventCard
                    key={e.id}
                    event={e}
                    onRegister={setModalEvent}
                    viewMode={viewMode}
                  />
                ))}
              </div>
            ) : (
              <div className="empty-results-box">
                <div className="empty-icon"><Compass size={42} /></div>
                <h3>No hackathons match your filters</h3>
                <p>Try resetting some filters or searching for broader keywords.</p>
                <button className="btn-secondary" onClick={clearAllFilters}>
                  Clear All Filters
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <RegistrationModal
        event={modalEvent}
        isOpen={Boolean(modalEvent)}
        onClose={() => setModalEvent(null)}
      />
    </div>
  );
}

// ─── Event Details Page ─────────────────────────────────────────────────────────
function EventDetails() {
  const { id } = useParams();
  const event = events.find((e) => e.id === id) || events[0];
  const [modalOpen, setModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const { isSaved, toggleSaved } = useSaved();
  const { showToast } = useToast();
  const saved = isSaved(event.id);
  const countdown = useCountdown(event.deadlineDays || 4);

  const handleShare = () => {
    navigator.clipboard?.writeText(window.location.href);
    showToast("Event URL copied to clipboard! 📋", "info");
  };

  const handleSave = () => {
    toggleSaved(event.id);
    showToast(saved ? "Removed from saved" : "Saved to your radar list! 🎯", "success");
  };

  return (
    <div className="event-detail-page">
      {/* Navigation Breadcrumb */}
      <div className="detail-breadcrumb-bar">
        <div className="detail-container">
          <Link to="/explore" className="breadcrumb-back-link">
            ← Back to All Hackathons
          </Link>
          <span className="breadcrumb-divider">/</span>
          <span className="breadcrumb-current">{event.title}</span>
        </div>
      </div>

      {/* Hero Header Banner */}
      <section className="detail-hero-banner">
        <div className="detail-hero-glow" />
        <div className="detail-container">
          <div className="detail-hero-layout">
            <div className="detail-hero-info">
              <div className="detail-badges-row">
                <StatusPill status={event.status} badgeType={event.badgeType} />
                <span className="detail-verified-badge">
                  <ShieldCheck size={14} /> Authoritative & Verified {event.verified}
                </span>
                <span className="detail-cat-badge">{event.category}</span>
              </div>

              <h1 className="detail-hero-title">{event.title}</h1>
              <div className="detail-organizer-row">
                <span className="organizer-prefix">Organized by</span>
                <Link to={`/organizer/${event.organizerKey || "microsoft"}`} className="organizer-name-link">
                  {event.organizer} <ArrowUpRight size={14} />
                </Link>
                <span className="separator">•</span>
                <span className="platform-tag-pill">{event.platform}</span>
              </div>

              <p className="detail-summary-text">{event.description}</p>

              <div className="detail-action-buttons">
                <button className="btn-primary btn-lg" onClick={() => setModalOpen(true)}>
                  <Zap size={18} /> Register for Free
                </button>
                <button className={`btn-secondary btn-lg ${saved ? "active-saved" : ""}`} onClick={handleSave}>
                  <Bookmark size={18} fill={saved ? "currentColor" : "none"} />
                  {saved ? "Saved to Radar" : "Save Challenge"}
                </button>
                <button className="btn-icon-square" onClick={handleShare} title="Share Link">
                  <Share2 size={18} />
                </button>
              </div>
            </div>

            {/* Countdown & Prize Summary Card */}
            <div className="detail-hero-card">
              <div className="hero-prize-highlight">
                <small>TOTAL PRIZE POOL</small>
                <div className="detail-prize-number">{event.prize}</div>
              </div>

              <div className="countdown-mini-strip">
                <div className="cd-title"><Clock3 size={14} /> Registration Closes In:</div>
                <div className="cd-values">
                  <span><b>{countdown.days}</b>d</span>:
                  <span><b>{countdown.hours}</b>h</span>:
                  <span><b>{countdown.minutes}</b>m</span>:
                  <span className="accent"><b>{countdown.seconds}</b>s</span>
                </div>
              </div>

              <div className="card-quick-specs">
                <div className="spec-item">
                  <CalendarDays size={15} />
                  <div>
                    <small>Hackathon Dates</small>
                    <b>{event.date}</b>
                  </div>
                </div>
                <div className="spec-item">
                  <MapPin size={15} />
                  <div>
                    <small>Format & Location</small>
                    <b>{event.mode} · {event.location}</b>
                  </div>
                </div>
                <div className="spec-item">
                  <Users size={15} />
                  <div>
                    <small>Team Size</small>
                    <b>{event.teamSize}</b>
                  </div>
                </div>
                <div className="spec-item">
                  <GraduationCap size={15} />
                  <div>
                    <small>Eligibility</small>
                    <b>{event.eligibility}</b>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Detail Content Section */}
      <section className="detail-body-section">
        <div className="detail-container">
          {/* Sub Navigation Tabs */}
          <div className="detail-tabs-strip">
            <button
              className={`detail-tab ${activeTab === "overview" ? "active" : ""}`}
              onClick={() => setActiveTab("overview")}
            >
              Overview & Tracks
            </button>
            <button
              className={`detail-tab ${activeTab === "prizes" ? "active" : ""}`}
              onClick={() => setActiveTab("prizes")}
            >
              Prizes Breakdown
            </button>
            <button
              className={`detail-tab ${activeTab === "timeline" ? "active" : ""}`}
              onClick={() => setActiveTab("timeline")}
            >
              Timeline & Phases
            </button>
            <button
              className={`detail-tab ${activeTab === "rules" ? "active" : ""}`}
              onClick={() => setActiveTab("rules")}
            >
              Eligibility & Rules
            </button>
          </div>

          <div className="detail-layout-grid">
            <div className="detail-main-column">
              {activeTab === "overview" && (
                <div className="tab-pane">
                  <div className="content-card-v2">
                    <h3>About the Challenge</h3>
                    <p>{event.description}</p>
                    <p>
                      Participants will have access to exclusive workshops, direct technical office hours with sponsor engineering leaders, and cloud sandbox credits to build functional prototypes.
                    </p>

                    <h4>Key Highlights</h4>
                    <div className="highlights-list">
                      {(event.highlights || [
                        "Official certificate of participation",
                        "Compute vouchers and API credits",
                        "Access to private developer Discord"
                      ]).map((h, i) => (
                        <div key={i} className="highlight-bullet">
                          <CheckCircle2 size={16} /> <span>{h}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="content-card-v2">
                    <h3>Required Skills & Technologies</h3>
                    <div className="tags-large-wrap">
                      {event.tags.map((t) => (
                        <span key={t} className="tag-pill-large">{t}</span>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "prizes" && (
                <div className="tab-pane">
                  <div className="content-card-v2">
                    <h3>Prize Pool Breakdown ({event.prize})</h3>
                    <div className="prizes-table">
                      {(event.prizeBreakdown || [
                        { rank: "1st Place Grand Winner", amount: "$50,000", perks: "Spotlight showcase + credits" },
                        { rank: "2nd Place", amount: "$30,000", perks: "Compute credits + swag" },
                        { rank: "3rd Place", amount: "$20,000", perks: "Digital badge" }
                      ]).map((p, i) => (
                        <div key={i} className="prize-row-item">
                          <div className="rank-badge">
                            <Trophy size={18} />
                          </div>
                          <div className="rank-info">
                            <b>{p.rank}</b>
                            <small>{p.perks}</small>
                          </div>
                          <div className="rank-amount">{p.amount}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "timeline" && (
                <div className="tab-pane">
                  <div className="content-card-v2">
                    <h3>Hackathon Schedule & Phases</h3>
                    <div className="phase-timeline-v2">
                      {(event.timeline || [
                        { phase: "Registration Opens", date: "Jan 15", status: "completed" },
                        { phase: "Hacking Sprint Starts", date: "Feb 01", status: "active" },
                        { phase: "Submissions Deadline", date: event.deadline, status: "upcoming" },
                        { phase: "Winner Announcement", date: "Apr 15", status: "upcoming" }
                      ]).map((item, index) => (
                        <div key={index} className={`timeline-phase-row phase-${item.status}`}>
                          <div className="timeline-node">
                            {item.status === "completed" && <Check size={12} />}
                            {item.status === "active" && <span className="active-dot" />}
                          </div>
                          <div className="timeline-content">
                            <div className="phase-date">{item.date}</div>
                            <div className="phase-name">{item.phase}</div>
                            <span className={`phase-badge badge-${item.status}`}>
                              {item.status.toUpperCase()}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "rules" && (
                <div className="tab-pane">
                  <div className="content-card-v2">
                    <h3>Eligibility Criteria</h3>
                    <div className="eligibility-box">
                      <CheckCircle2 size={20} />
                      <div>
                        <b>{event.eligibility}</b>
                        <p>All participants must comply with the competition terms and code of conduct.</p>
                      </div>
                    </div>

                    <h4>Rules of Participation</h4>
                    <ul className="rules-list">
                      <li>All code submitted must be newly developed during the official hackathon window.</li>
                      <li>Use of open-source libraries and public APIs is permitted provided they are properly attributed.</li>
                      <li>Teams can consist of <b>{event.teamSize}</b>. Individuals are also welcome to submit as solo hackers.</li>
                      <li>Submissions require a working demo link, GitHub repository with open access, and a short 3-minute video walk-through.</li>
                    </ul>
                  </div>
                </div>
              )}
            </div>

            {/* Aside Sidebar */}
            <aside className="detail-aside-column">
              <div className="aside-card-v2">
                <div className="source-verification-header">
                  <ShieldCheck size={20} />
                  <div>
                    <b>Authoritative Source</b>
                    <small>Verified by Radar Pipeline</small>
                  </div>
                </div>
                <div className="aside-meta-row">
                  <span>Host Platform</span>
                  <b>{event.platform}</b>
                </div>
                <div className="aside-meta-row">
                  <span>Freshness</span>
                  <b>Verified {event.verified}</b>
                </div>
                <div className="aside-meta-row">
                  <span>Recurrence</span>
                  <b>Annual Series</b>
                </div>
                <a
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    showToast("Opening authoritative external portal...", "info");
                  }}
                  className="btn-secondary full-width btn-sm mt-12"
                >
                  Visit Official Host Site <ExternalLink size={13} />
                </a>
              </div>

              <div className="aside-card-v2">
                <h4>Share this Challenge</h4>
                <p className="aside-subtext">Invite teammates to collaborate or bookmark for later.</p>
                <div className="share-btn-row">
                  <button className="btn-secondary btn-sm full-width" onClick={handleShare}>
                    <Copy size={13} /> Copy Link
                  </button>
                </div>
              </div>
            </aside>
          </div>
        </div>
      </section>

      <RegistrationModal
        event={event}
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
      />
    </div>
  );
}

// ─── Predictions Page ───────────────────────────────────────────────────────────
function Predictions() {
  const { showToast } = useToast();

  const handleSetAlert = (eventName) => {
    showToast(`Radar alert enabled for "${eventName}"! 🔔`, "success");
  };

  return (
    <div className="predictions-page">
      <div className="predictions-hero">
        <div className="pred-container">
          <div className="section-eyebrow">
            <Sparkles size={14} /> RADAR AI FORECASTING
          </div>
          <h1 className="pred-page-title">AI Hackathon Predictions</h1>
          <p className="pred-page-subtitle">
            Statistical forecasting of upcoming hackathons based on annual cadence patterns, organizer blog teasers, and DNS registrations.
          </p>

          <div className="model-stats-pill-row">
            <div className="model-stat-chip">
              <BrainCircuit size={15} /> <b>Model:</b> radar-cadence-v2.4
            </div>
            <div className="model-stat-chip">
              <TrendingUp size={15} /> <b>Accuracy:</b> 94.2% historical match
            </div>
            <div className="model-stat-chip">
              <Clock3 size={15} /> <b>Advantage:</b> ~28 days advance lead
            </div>
          </div>
        </div>
      </div>

      <div className="pred-container pred-main-body">
        <div className="disclaimer-alert-card">
          <AlertCircle size={22} />
          <div>
            <b>Predictive Intelligence Notice</b>
            <p>
              Predictions are probabilistic forecasts and are not official sponsor announcements until verified. Use these signals to prepare team formations and study prerequisites early.
            </p>
          </div>
        </div>

        <div className="predictions-cards-grid">
          {predictions.map((p) => (
            <MovingBorderBox key={p.id} className="prediction-full-moving-card">
              <article className="prediction-full-card">
                <div className="pred-card-top-row">
                  <div className="pred-org-tag">
                    <Building2 size={13} /> {p.organizer}
                  </div>
                  <div className="probability-gauge">
                    <span className="gauge-fill" style={{ width: `${Math.round(p.probability * 100)}%` }} />
                    <b>{Math.round(p.probability * 100)}% Probability</b>
                  </div>
                </div>

                <h2 className="pred-card-title">{p.event}</h2>

                <div className="pred-specs-grid">
                  <div className="spec-tile">
                    <CalendarDays size={14} />
                    <div>
                      <small>Predicted Window</small>
                      <b>{p.window}</b>
                    </div>
                  </div>
                  <div className="spec-tile">
                    <Trophy size={14} />
                    <div>
                      <small>Expected Prize</small>
                      <b>{p.expectedPrize}</b>
                    </div>
                  </div>
                  <div className="spec-tile">
                    <Clock3 size={14} />
                    <div>
                      <small>Cadence</small>
                      <b>{p.historicalCadence}</b>
                    </div>
                  </div>
                </div>

                <div className="evidence-signals-box">
                  <b>Detected Evidence & Radar Signals:</b>
                  <TracingBeamTimeline
                    steps={p.signals.map((sig, idx) => ({
                      title: `Signal Beacon #${idx + 1}`,
                      desc: sig,
                    }))}
                  />
                </div>

                <div className="pred-card-footer">
                  <button className="btn-primary full-width" onClick={() => handleSetAlert(p.event)}>
                    <Bell size={15} /> Set Instant Radar Alert
                  </button>
                </div>
              </article>
            </MovingBorderBox>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Organizer Profile Page ─────────────────────────────────────────────────────
function OrganizerProfile() {
  const { name = "microsoft" } = useParams();
  const org = organizers[name] || organizers.microsoft;
  const { showToast } = useToast();
  const [following, setFollowing] = useState(false);

  const toggleFollow = () => {
    setFollowing(!following);
    showToast(
      following ? `Unfollowed ${org.name}` : `Following ${org.name}! You'll receive radar alerts. 🔔`,
      following ? "info" : "success"
    );
  };

  return (
    <div className="organizer-profile-page">
      <div className="org-profile-hero">
        <div className="org-container">
          <div className="org-hero-box">
            <div className="org-big-logo" style={{ color: org.logoColor, background: org.logoColor + "22", borderColor: org.logoColor + "55" }}>
              {org.initials}
            </div>

            <div className="org-hero-details">
              <div className="org-eyebrow-row">
                <span className="org-type-badge">{org.type}</span>
                <span className="org-location-badge"><MapPin size={12} /> {org.country}</span>
              </div>
              <h1 className="org-profile-title">{org.name}</h1>
              <p className="org-profile-desc">{org.description}</p>
              <a href={`https://${org.domain}`} target="_blank" rel="noreferrer" className="org-website-link">
                {org.domain} <ExternalLink size={13} />
              </a>
            </div>

            <div className="org-follow-action">
              <button
                className={`btn-primary ${following ? "btn-following" : ""}`}
                onClick={toggleFollow}
              >
                {following ? <Check size={16} /> : <Zap size={16} />}
                {following ? "Following" : "Follow Organizer"}
              </button>
            </div>
          </div>

          <div className="org-metrics-row">
            <div>
              <small>Active Hackathons</small>
              <b>{org.activeHackathons}</b>
            </div>
            <div>
              <small>Total Prizes Awarded</small>
              <b className="green-text">{org.totalPrizesGiven}</b>
            </div>
            <div>
              <small>Verification Guarantee</small>
              <b>100% Tier-1</b>
            </div>
          </div>
        </div>
      </div>

      <div className="org-container org-body-section">
        <div className="org-layout-grid">
          <div className="org-main-col">
            <div className="content-card-v2">
              <h3>Hackathons History & Timeline</h3>
              <div className="org-events-timeline">
                {org.events.map((evt, idx) => (
                  <div key={idx} className="org-history-row">
                    <div className="history-year-pill">{evt.year}</div>
                    <div className="history-info">
                      <b>{evt.title}</b>
                      <div className="history-meta">
                        <span><Trophy size={12} /> {evt.prize}</span>
                        <span><Users size={12} /> {evt.participants} participants</span>
                      </div>
                    </div>
                    <StatusPill status={evt.status} />
                  </div>
                ))}
              </div>
            </div>
          </div>

          <aside className="org-aside-col">
            <div className="aside-card-v2">
              <h4>Recurrence Pattern Analysis</h4>
              <p className="aside-subtext">
                Historical quarterly frequency shows consistent seasonal releases every spring & summer.
              </p>
              <div className="cadence-bars-visual">
                <div className="cadence-col"><div className="c-bar h40" /><small>Q1</small></div>
                <div className="cadence-col"><div className="c-bar h85 accent" /><small>Q2</small></div>
                <div className="cadence-col"><div className="c-bar h60" /><small>Q3</small></div>
                <div className="cadence-col"><div className="c-bar h30" /><small>Q4</small></div>
              </div>
              <small className="cadence-note">★ Peak challenge activity detected in Q2 (April - June)</small>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

// ─── Main App Root with Providers ───────────────────────────────────────────────
function App() {
  return (
    <ToastProvider>
      <SavedProvider>
        <Routes>
          <Route path="/admin/*" element={<AdminRouter />} />
          <Route
            path="/*"
            element={
              <Layout>
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/explore" element={<Explore />} />
                  <Route path="/event/:id" element={<EventDetails />} />
                  <Route path="/predictions" element={<Predictions />} />
                  <Route path="/organizer/:name" element={<OrganizerProfile />} />
                  <Route path="*" element={<Home />} />
                </Routes>
              </Layout>
            }
          />
        </Routes>
      </SavedProvider>
    </ToastProvider>
  );
}

export default App;