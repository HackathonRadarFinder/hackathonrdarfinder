import React, { useState, useEffect, useRef, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Sparkles, Globe2, Compass, ArrowRight, Trophy, Clock3,
  Building2, Zap, BrainCircuit, ShieldCheck, TrendingUp,
  MapPin, CheckCircle2, ChevronRight, Filter, Flame
} from "lucide-react";

// ─── 1. Aceternity Spotlight Cone ──────────────────────────────────────────────
export function AceternitySpotlight({ className = "", fill = "#7667ff" }) {
  return (
    <svg
      className={`aceternity-spotlight ${className}`}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 3787 2842"
      fill="none"
      aria-hidden="true"
    >
      <g filter="url(#spotlight-filter)">
        <ellipse
          cx="1924.71"
          cy="273.501"
          rx="1924.71"
          ry="273.501"
          transform="matrix(-0.822377 -0.568943 -0.568943 0.822377 3631.88 2291.09)"
          fill={fill}
          fillOpacity="0.22"
        />
      </g>
      <defs>
        <filter
          id="spotlight-filter"
          x="0.860352"
          y="0.838989"
          width="3785.16"
          height="2840.26"
          filterUnits="userSpaceOnUse"
          colorInterpolationFilters="sRGB"
        >
          <feFlood floodOpacity="0" result="BackgroundImageFix" />
          <feBlend mode="normal" in="SourceGraphic" in2="BackgroundImageFix" result="shape" />
          <feGaussianBlur stdDeviation="151" result="effect1_foregroundBlur" />
        </filter>
      </defs>
    </svg>
  );
}

// ─── 2. Text Generate Effect ───────────────────────────────────────────────────
export function TextGenerateEffect({ words, className = "", highlightWords = [] }) {
  const [complete, setComplete] = useState(false);
  const wordsArray = useMemo(() => words.split(" "), [words]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setComplete(true);
    }, 100);
    return () => clearTimeout(timer);
  }, []);

  return (
    <span className={`text-generate-container ${className}`}>
      {wordsArray.map((word, idx) => {
        const isHighlight = highlightWords.some(
          (hw) => word.toLowerCase().includes(hw.toLowerCase())
        );
        return (
          <span
            key={idx}
            className={`generate-word ${isHighlight ? "word-highlight" : ""} ${
              complete ? "visible" : ""
            }`}
            style={{
              transitionDelay: `${idx * 0.08}s`,
            }}
          >
            {word}&nbsp;
          </span>
        );
      })}
    </span>
  );
}

// ─── 3. Hero Highlight Wrapper ─────────────────────────────────────────────────
export function HeroHighlight({ children, className = "" }) {
  return (
    <span className={`hero-highlight-pill ${className}`}>
      <span className="hero-highlight-gradient" />
      <span className="hero-highlight-content">{children}</span>
    </span>
  );
}

// ─── 4. Placeholders And Vanish Input ──────────────────────────────────────────
export function PlaceholdersAndVanishInput({
  placeholders = [],
  value = "",
  onChange,
  onSubmit,
}) {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [animating, setAnimating] = useState(false);

  useEffect(() => {
    if (!placeholders.length) return;
    const interval = setInterval(() => {
      setAnimating(true);
      setTimeout(() => {
        setCurrentIdx((prev) => (prev + 1) % placeholders.length);
        setAnimating(false);
      }, 400);
    }, 3200);

    return () => clearInterval(interval);
  }, [placeholders]);

  return (
    <form onSubmit={onSubmit} className="vanish-search-form">
      <div className="vanish-input-container">
        <span className="vanish-search-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </span>

        <input
          type="text"
          value={value}
          onChange={onChange}
          className="vanish-text-input"
          autoComplete="off"
          spellCheck="false"
        />

        {/* Animated Rotating Placeholder overlay when input is empty */}
        {!value && (
          <div className="vanish-placeholder-track">
            <span
              className={`vanish-placeholder-text ${
                animating ? "vanish-exit" : "vanish-enter"
              }`}
            >
              {placeholders[currentIdx] || "Search hackathons..."}
            </span>
          </div>
        )}

        <button type="submit" className="vanish-submit-btn" aria-label="Search">
          <span>Search</span>
          <ArrowRight size={16} />
        </button>
      </div>
    </form>
  );
}

// ─── 5. High-Tech World Map Projection & Signal Arcs ───────────────────────────
// Equirectangular projection map coordinates (width: 1000, height: 500)
function geoToSvg(lat, lng, width = 1000, height = 500) {
  const x = ((lng + 180) / 360) * width;
  const y = ((90 - lat) / 180) * height;
  return { x, y };
}

// Sample continent dot matrix grid for high-tech holographic world look
const CONTINENT_DOTS = [
  // North America
  { x: 160, y: 120 }, { x: 180, y: 110 }, { x: 200, y: 100 }, { x: 220, y: 95 },
  { x: 150, y: 140 }, { x: 170, y: 135 }, { x: 195, y: 130 }, { x: 220, y: 125 },
  { x: 245, y: 120 }, { x: 270, y: 125 }, { x: 290, y: 135 }, { x: 160, y: 160 },
  { x: 185, y: 155 }, { x: 210, y: 150 }, { x: 235, y: 155 }, { x: 260, y: 165 },
  { x: 200, y: 180 }, { x: 220, y: 190 }, { x: 240, y: 210 },
  // South America
  { x: 280, y: 260 }, { x: 300, y: 280 }, { x: 320, y: 295 }, { x: 310, y: 320 },
  { x: 330, y: 340 }, { x: 320, y: 370 }, { x: 310, y: 400 }, { x: 300, y: 430 },
  // Europe
  { x: 480, y: 95 }, { x: 500, y: 105 }, { x: 520, y: 100 }, { x: 540, y: 95 },
  { x: 490, y: 120 }, { x: 510, y: 120 }, { x: 535, y: 125 }, { x: 560, y: 115 },
  { x: 480, y: 140 }, { x: 505, y: 140 }, { x: 525, y: 145 }, { x: 550, y: 140 },
  // Africa
  { x: 485, y: 180 }, { x: 510, y: 180 }, { x: 540, y: 185 }, { x: 565, y: 200 },
  { x: 490, y: 210 }, { x: 515, y: 225 }, { x: 545, y: 235 }, { x: 580, y: 230 },
  { x: 520, y: 270 }, { x: 540, y: 285 }, { x: 560, y: 295 }, { x: 530, y: 330 },
  { x: 550, y: 350 }, { x: 540, y: 380 },
  // Asia
  { x: 600, y: 90 }, { x: 630, y: 95 }, { x: 670, y: 100 }, { x: 710, y: 105 },
  { x: 750, y: 100 }, { x: 790, y: 110 }, { x: 830, y: 120 }, { x: 870, y: 115 },
  { x: 620, y: 130 }, { x: 660, y: 135 }, { x: 700, y: 140 }, { x: 740, y: 145 },
  { x: 780, y: 140 }, { x: 820, y: 150 }, { x: 860, y: 145 }, { x: 890, y: 155 },
  { x: 640, y: 170 }, { x: 680, y: 180 }, { x: 715, y: 195 }, { x: 750, y: 190 },
  { x: 785, y: 210 }, { x: 825, y: 210 }, { x: 705, y: 215 }, { x: 725, y: 230 },
  { x: 790, y: 250 }, { x: 830, y: 260 },
  // Australia
  { x: 820, y: 340 }, { x: 850, y: 330 }, { x: 880, y: 345 }, { x: 830, y: 375 },
  { x: 865, y: 380 }, { x: 890, y: 385 }
];

export function AceternityWorldMap({
  events = [],
  selectedCategory = "ALL",
  onSelectEvent,
  className = "",
  compact = false,
}) {
  const [hoveredEvent, setHoveredEvent] = useState(null);
  const navigate = useNavigate();

  // Filter events based on category
  const filteredEvents = useMemo(() => {
    if (!selectedCategory || selectedCategory === "ALL") return events;
    return events.filter(
      (e) =>
        e.radarCategory === selectedCategory ||
        e.category?.toLowerCase().includes(selectedCategory.toLowerCase()) ||
        e.tags?.some((t) => t.toLowerCase().includes(selectedCategory.toLowerCase()))
    );
  }, [events, selectedCategory]);

  // Construct global hubs and connecting telemetry arcs
  const activeHubs = useMemo(() => {
    return filteredEvents
      .filter((e) => e.coordinates && e.coordinates.lat)
      .map((e) => {
        const { x, y } = geoToSvg(e.coordinates.lat, e.coordinates.lng, 1000, 500);
        return { ...e, svgX: x, svgY: y };
      });
  }, [filteredEvents]);

  // Precomputed telemetry arcs between premier global nodes
  const arcs = useMemo(() => {
    if (activeHubs.length < 2) return [];
    const connections = [];
    for (let i = 0; i < activeHubs.length - 1; i++) {
      const from = activeHubs[i];
      const to = activeHubs[i + 1];
      // Quadratic bezier arc midpoint arched upwards
      const dx = to.svgX - from.svgX;
      const dy = to.svgY - from.svgY;
      const midX = (from.svgX + to.svgX) / 2;
      const midY = (from.svgY + to.svgY) / 2 - Math.min(80, Math.max(30, Math.abs(dx) * 0.22));
      connections.push({
        id: `arc-${from.id}-${to.id}`,
        d: `M ${from.svgX} ${from.svgY} Q ${midX} ${midY} ${to.svgX} ${to.svgY}`,
        from,
        to,
      });
    }
    return connections;
  }, [activeHubs]);

  const handleMarkerClick = (event) => {
    if (onSelectEvent) {
      onSelectEvent(event);
    } else {
      navigate(`/event/${event.id}`);
    }
  };

  return (
    <div className={`world-map-wrapper ${compact ? "compact" : ""} ${className}`}>
      {/* Ambient background glow & grid */}
      <div className="map-ambient-glow" />
      <div className="map-grid-overlay" />

      <svg
        viewBox="0 0 1000 500"
        className="world-map-svg"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <radialGradient id="beaconGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#00d2ff" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#7667ff" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="arcGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#00d2ff" stopOpacity="0.8" />
            <stop offset="50%" stopColor="#9b7cff" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#00d2ff" stopOpacity="0.8" />
          </linearGradient>
          <filter id="glowFilter" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Global Dot Matrix Landmass Pattern */}
        <g className="continent-dots-group">
          {CONTINENT_DOTS.map((dot, i) => (
            <circle
              key={i}
              cx={dot.x}
              cy={dot.y}
              r="2.2"
              className="continent-dot"
            />
          ))}
        </g>

        {/* Animated Telemetry Connecting Arcs */}
        <g className="telemetry-arcs-group">
          {arcs.map((arc) => (
            <g key={arc.id}>
              {/* Underlying subtle trace */}
              <path
                d={arc.d}
                fill="none"
                stroke="rgba(118, 103, 255, 0.25)"
                strokeWidth="1.2"
                strokeDasharray="4 4"
              />
              {/* Glowing animated beam */}
              <path
                d={arc.d}
                fill="none"
                stroke="url(#arcGradient)"
                strokeWidth="2"
                strokeLinecap="round"
                filter="url(#glowFilter)"
                className="animated-arc-beam"
              />
            </g>
          ))}
        </g>

        {/* Pulsing Event Location Markers */}
        <g className="location-markers-group">
          {activeHubs.map((e) => {
            const isHovered = hoveredEvent?.id === e.id;
            return (
              <g
                key={e.id}
                className={`map-beacon-node ${isHovered ? "hovered" : ""}`}
                transform={`translate(${e.svgX}, ${e.svgY})`}
                onMouseEnter={() => setHoveredEvent(e)}
                onMouseLeave={() => setHoveredEvent(null)}
                onClick={() => handleMarkerClick(e)}
                style={{ cursor: "pointer" }}
              >
                {/* Outer ping concentric circles */}
                <circle r="14" className="beacon-ping-ring ping-1" />
                <circle r="22" className="beacon-ping-ring ping-2" />

                {/* Radar beacon central core */}
                <circle
                  r={isHovered ? "7" : "5.5"}
                  fill="#00d2ff"
                  className="beacon-core-dot"
                  filter="url(#glowFilter)"
                />
                <circle r="2.5" fill="#ffffff" />

                {/* City label on map */}
                <text
                  y="-12"
                  textAnchor="middle"
                  className={`beacon-city-label ${isHovered ? "active" : ""}`}
                >
                  {e.city || e.location.split("(")[0].trim()}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Floating Animated Tooltip with Event Intelligence */}
      {hoveredEvent && (
        <div
          className="map-animated-tooltip"
          style={{
            left: `${(hoveredEvent.svgX / 1000) * 100}%`,
            top: `${(hoveredEvent.svgY / 500) * 100}%`,
          }}
          onClick={() => handleMarkerClick(hoveredEvent)}
        >
          <div className="tooltip-glass-panel">
            <div className="tooltip-top-row">
              <span className="tooltip-org">
                <Building2 size={12} /> {hoveredEvent.organizer}
              </span>
              <span className="tooltip-ai-badge">
                <Sparkles size={11} /> {hoveredEvent.aiMatchScore || 95}% Match
              </span>
            </div>

            <h4 className="tooltip-title">{hoveredEvent.title}</h4>

            <div className="tooltip-details-grid">
              <div>
                <small>Prize Pool</small>
                <b className="prize-gold">{hoveredEvent.prize}</b>
              </div>
              <div>
                <small>Location</small>
                <b>{hoveredEvent.city || "Global Hub"}</b>
              </div>
              <div>
                <small>Closes in</small>
                <b>{hoveredEvent.deadlineDays || 4} days</b>
              </div>
            </div>

            <div className="tooltip-tags-row">
              {hoveredEvent.tags?.slice(0, 2).map((t) => (
                <span key={t} className="tooltip-mini-tag">{t}</span>
              ))}
            </div>

            <div className="tooltip-cta-line">
              <span>Click to view challenge</span>
              <ChevronRight size={13} />
            </div>
          </div>
        </div>
      )}

      {/* Live Radar Coordinates Telemetry Strip */}
      <div className="map-status-overlay">
        <div className="map-telemetry-badge">
          <span className="live-pulse-dot" />
          <span><b>{activeHubs.length}</b> LIVE GLOBAL BEACONS</span>
        </div>
        <div className="map-coverage-text">
          SF • Seattle • London • Geneva • Bengaluru • Singapore • Tokyo
        </div>
      </div>
    </div>
  );
}

// ─── 6. 3D Wireframe / Particle Globe Visualization ───────────────────────────
export function Aceternity3DGlobe({ events = [], onSelectEvent }) {
  const [rotation, setRotation] = useState(0);
  const [hoveredEvent, setHoveredEvent] = useState(null);
  const navigate = useNavigate();

  // Smooth continuous rotation
  useEffect(() => {
    let animId;
    const animate = () => {
      setRotation((prev) => (prev + 0.3) % 360);
      animId = requestAnimationFrame(animate);
    };
    animId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animId);
  }, []);

  const R = 150; // Globe radius
  const cx = 200;
  const cy = 200;

  // Compute 3D orthographic projection of events onto rotating globe
  const projectedBeacons = useMemo(() => {
    const rotRad = (rotation * Math.PI) / 180;
    return events
      .filter((e) => e.coordinates && e.coordinates.lat)
      .map((e) => {
        const latRad = (e.coordinates.lat * Math.PI) / 180;
        const lngRad = (e.coordinates.lng * Math.PI) / 180;

        // Spherical to 3D Cartesian coordinates
        const x3d = R * Math.cos(latRad) * Math.sin(lngRad + rotRad);
        const y3d = -R * Math.sin(latRad);
        const z3d = R * Math.cos(latRad) * Math.cos(lngRad + rotRad);

        // Visible only when on the front hemisphere (z3d > 0)
        return {
          ...e,
          projX: cx + x3d,
          projY: cy + y3d,
          visible: z3d > 0,
          scale: (z3d + R) / (2 * R), // Scale according to depth
        };
      });
  }, [events, rotation]);

  return (
    <div className="globe-3d-wrapper">
      <div className="globe-atmosphere-halo" />
      <svg viewBox="0 0 400 400" className="globe-3d-svg">
        <defs>
          <radialGradient id="globeSphereGrad" cx="40%" cy="35%" r="65%">
            <stop offset="0%" stopColor="#1a2444" stopOpacity="0.8" />
            <stop offset="60%" stopColor="#0b0f20" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#050711" stopOpacity="1" />
          </radialGradient>
          <radialGradient id="globeAtmosphere" cx="50%" cy="50%" r="50%">
            <stop offset="85%" stopColor="#7667ff" stopOpacity="0" />
            <stop offset="100%" stopColor="#00d2ff" stopOpacity="0.4" />
          </radialGradient>
        </defs>

        {/* Outer Globe Sphere */}
        <circle cx={cx} cy={cy} r={R} fill="url(#globeSphereGrad)" />
        <circle cx={cx} cy={cy} r={R} fill="url(#globeAtmosphere)" stroke="rgba(0, 210, 255, 0.4)" strokeWidth="1.5" />

        {/* Latitude Rings */}
        {[-60, -30, 0, 30, 60].map((lat) => {
          const rLat = R * Math.cos((lat * Math.PI) / 180);
          const yLat = cy - R * Math.sin((lat * Math.PI) / 180);
          return (
            <ellipse
              key={lat}
              cx={cx}
              cy={yLat}
              rx={rLat}
              ry={rLat * 0.28}
              fill="none"
              stroke="rgba(118, 103, 255, 0.18)"
              strokeWidth="0.9"
              strokeDasharray="2 3"
            />
          );
        })}

        {/* Rotating Longitude Meridians */}
        {[0, 45, 90, 135].map((deg) => {
          const effectiveDeg = (deg + rotation) % 180;
          const rxLong = R * Math.sin((effectiveDeg * Math.PI) / 180);
          return (
            <ellipse
              key={deg}
              cx={cx}
              cy={cy}
              rx={Math.abs(rxLong)}
              ry={R}
              fill="none"
              stroke="rgba(0, 210, 255, 0.16)"
              strokeWidth="0.9"
            />
          );
        })}

        {/* Projected Beacons on Front Hemisphere */}
        {projectedBeacons
          .filter((b) => b.visible)
          .map((b) => {
            const isHovered = hoveredEvent?.id === b.id;
            return (
              <g
                key={b.id}
                transform={`translate(${b.projX}, ${b.projY})`}
                onMouseEnter={() => setHoveredEvent(b)}
                onMouseLeave={() => setHoveredEvent(null)}
                onClick={() => (onSelectEvent ? onSelectEvent(b) : navigate(`/event/${b.id}`))}
                style={{ cursor: "pointer" }}
              >
                <circle r={8 * b.scale} className="beacon-ping-ring ping-1" />
                <circle
                  r={isHovered ? 7 : 4.5 * b.scale}
                  fill="#00d2ff"
                  filter="drop-shadow(0 0 6px #00d2ff)"
                />
                <circle r={2 * b.scale} fill="#ffffff" />
                {b.scale > 0.6 && (
                  <text y="-8" textAnchor="middle" className="globe-city-text">
                    {b.city}
                  </text>
                )}
              </g>
            );
          })}
      </svg>

      {/* Hover Tooltip on 3D Globe */}
      {hoveredEvent && (
        <div className="globe-tooltip-card">
          <b>{hoveredEvent.title}</b>
          <small>{hoveredEvent.organizer} · {hoveredEvent.prize}</small>
          <span className="globe-ai-score">{hoveredEvent.aiMatchScore}% AI Match</span>
        </div>
      )}
    </div>
  );
}

// ─── 7. Right Hero Visual Switcher (World Map & 3D Globe) ───────────────────────
export function HeroInteractiveRadar({ events = [] }) {
  const [mode, setMode] = useState("map"); // "map" or "globe"
  const navigate = useNavigate();

  return (
    <div className="hero-interactive-radar-card">
      {/* Top Header Mode Toggle & Status */}
      <div className="radar-card-topbar">
        <div className="radar-status-badge">
          <span className="radar-pulse-dot" />
          <span><b>LIVE RADAR TELEMETRY</b></span>
        </div>
        <div className="radar-view-mode-toggle">
          <button
            className={`view-mode-btn ${mode === "map" ? "active" : ""}`}
            onClick={() => setMode("map")}
            title="World Map Mode"
          >
            <Compass size={14} /> Map
          </button>
          <button
            className={`view-mode-btn ${mode === "globe" ? "active" : ""}`}
            onClick={() => setMode("globe")}
            title="3D Globe Mode"
          >
            <Globe2 size={14} /> 3D Globe
          </button>
        </div>
      </div>

      {/* Main Interactive Canvas */}
      <div className="radar-canvas-container">
        {mode === "map" ? (
          <AceternityWorldMap events={events} compact />
        ) : (
          <Aceternity3DGlobe events={events} />
        )}
      </div>

      {/* Floating Signal Indicator Banner */}
      <div className="floating-signal-badge">
        <span className="beacon-dot" />
        <div className="signal-badge-content">
          <small>AI PREDICTION MATCH</small>
          <b>Microsoft AI Cloud Summit</b>
          <span>94% probability · Expected window May 2027</span>
        </div>
        <Link to="/predictions" className="signal-arrow-btn" title="View prediction details">
          <ArrowRight size={14} />
        </Link>
      </div>
    </div>
  );
}

// ─── 8. Aceternity Card Spotlight Hook & Container ─────────────────────────────
export function CardSpotlightWrapper({ children, className = "" }) {
  const cardRef = useRef(null);

  const handleMouseMove = (e) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    cardRef.current.style.setProperty("--mouse-x", `${x}px`);
    cardRef.current.style.setProperty("--mouse-y", `${y}px`);
  };

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      className={`aceternity-card-spotlight ${className}`}
    >
      <div className="card-spotlight-radial-glow" />
      {children}
    </div>
  );
}

// ─── 9. Moving Border Element ──────────────────────────────────────────────────
export function MovingBorderBox({ children, className = "", duration = 4000 }) {
  return (
    <div className={`moving-border-container ${className}`}>
      <div
        className="moving-border-beam"
        style={{ animationDuration: `${duration}ms` }}
      />
      <div className="moving-border-content">{children}</div>
    </div>
  );
}

// ─── 10. Tracing Beam Container ────────────────────────────────────────────────
export function TracingBeamTimeline({ steps = [] }) {
  return (
    <div className="tracing-beam-timeline">
      <div className="tracing-beam-line">
        <span className="tracing-beam-glow-dot" />
      </div>
      <div className="tracing-beam-steps">
        {steps.map((step, idx) => (
          <div key={idx} className="tracing-step-item">
            <div className="step-indicator">
              <span className="step-num">{idx + 1}</span>
            </div>
            <div className="step-content">
              <b>{step.title}</b>
              <p>{step.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── 11. Viewport Triggered Animated Counter ───────────────────────────────────
export function AnimatedCounter({
  target = 100,
  prefix = "",
  suffix = "",
  decimals = 0,
  duration = 2000,
  formatter,
}) {
  const [value, setValue] = useState(0);
  const elementRef = useRef(null);
  const startedRef = useRef(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !startedRef.current) {
          startedRef.current = true;
          const startTime = performance.now();
          const tick = (now) => {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // Ease-out cubic calculation
            const easeProgress = 1 - Math.pow(1 - progress, 3);
            const current = easeProgress * target;
            setValue(current);
            if (progress < 1) {
              requestAnimationFrame(tick);
            } else {
              setValue(target);
            }
          };
          requestAnimationFrame(tick);
        }
      },
      { threshold: 0.2 }
    );

    if (elementRef.current) {
      observer.observe(elementRef.current);
    }
    return () => observer.disconnect();
  }, [target, duration]);

  const displayString = useMemo(() => {
    if (formatter) return formatter(value);
    if (decimals > 0) return value.toFixed(decimals);
    return Math.round(value).toLocaleString();
  }, [value, decimals, formatter]);

  return (
    <span ref={elementRef} className="animated-counter-num">
      {prefix}{displayString}{suffix}
    </span>
  );
}

// ─── 12. Aceternity Live Radar Section with Filtering ──────────────────────────
export function LiveRadarSection({ events = [], onRegister }) {
  const [activeFilter, setActiveFilter] = useState("ALL");
  const [selectedEvent, setSelectedEvent] = useState(events[0] || null);

  const filters = [
    "ALL",
    "AI",
    "CLOUD",
    "WEB3",
    "ROBOTICS",
    "CYBERSECURITY",
    "OPEN SOURCE",
  ];

  return (
    <section className="live-radar-section">
      <div className="section-container">
        <div className="section-header-flex">
          <div>
            <div className="section-eyebrow">
              <Zap size={14} /> REAL-TIME SATELLITE TELEMETRY
            </div>
            <h2 className="section-heading">Live Hackathon Radar</h2>
            <p className="section-subtext">
              Track global hackathon signals, developer hubs, and cash prize deployments across worldwide innovation epicenters.
            </p>
          </div>

          <div className="radar-pulse-indicator-pill">
            <span className="live-pulse-dot" />
            <span>Telemetry Active · Refreshing Hourly</span>
          </div>
        </div>

        {/* Category Filter Pills Bar */}
        <div className="radar-filter-bar">
          <div className="radar-filter-scroller">
            {filters.map((f) => (
              <button
                key={f}
                className={`radar-filter-pill ${activeFilter === f ? "active" : ""}`}
                onClick={() => setActiveFilter(f)}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Big Interactive Map Canvas */}
        <div className="radar-big-map-container">
          <AceternityWorldMap
            events={events}
            selectedCategory={activeFilter}
            onSelectEvent={(evt) => setSelectedEvent(evt)}
          />
        </div>

        {/* Selected Hub Intelligence Card Drawer */}
        {selectedEvent && (
          <div className="radar-focused-event-drawer">
            <div className="drawer-glow-border" />
            <div className="drawer-content">
              <div className="drawer-meta-col">
                <span className="drawer-tag">
                  <MapPin size={13} /> {selectedEvent.city || selectedEvent.location}
                </span>
                <span className="drawer-ai-score">
                  <Sparkles size={13} /> {selectedEvent.aiMatchScore || 96}% AI Radar Match
                </span>
              </div>

              <div className="drawer-main-col">
                <h3 className="drawer-title">{selectedEvent.title}</h3>
                <p className="drawer-desc">{selectedEvent.description}</p>
                <div className="drawer-tags-list">
                  {selectedEvent.tags?.map((t) => (
                    <span key={t} className="drawer-tag-chip">{t}</span>
                  ))}
                </div>
              </div>

              <div className="drawer-prize-col">
                <div className="drawer-prize-card">
                  <small>Prize Pool</small>
                  <b>{selectedEvent.prize}</b>
                  <span>Closes in {selectedEvent.deadlineDays || 4} days</span>
                </div>
                <div className="drawer-actions-row">
                  <Link to={`/event/${selectedEvent.id}`} className="btn-secondary btn-sm">
                    View Details
                  </Link>
                  <button
                    className="btn-primary btn-sm"
                    onClick={() => onRegister && onRegister(selectedEvent)}
                  >
                    Register <ArrowRight size={13} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

// ─── 13. Magnetic Button Microinteraction Component ────────────────────────────
export function MagneticButton({ children, className = "", onClick, ...props }) {
  const btnRef = useRef(null);

  const handleMouseMove = (e) => {
    if (!btnRef.current) return;
    const rect = btnRef.current.getBoundingClientRect();
    const x = e.clientX - (rect.left + rect.width / 2);
    const y = e.clientY - (rect.top + rect.height / 2);
    btnRef.current.style.transform = `translate(${x * 0.15}px, ${y * 0.15}px)`;
  };

  const handleMouseLeave = () => {
    if (!btnRef.current) return;
    btnRef.current.style.transform = "translate(0px, 0px)";
  };

  return (
    <button
      ref={btnRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
      className={`magnetic-btn ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

// ─── 14. Aceternity Bento Grid Component ───────────────────────────────────────
export function AceternityBentoGrid() {
  return (
    <section className="bento-grid-section">
      <div className="section-container">
        <div className="section-header-flex">
          <div>
            <div className="section-eyebrow">
              <Sparkles size={14} /> INTELLIGENCE SUITE
            </div>
            <h2 className="section-heading">Platform Intelligence At Scale</h2>
            <p className="section-subtext">
              Engineered with predictive data pipelines, global satellite telemetry, and real-time eligibility scoring.
            </p>
          </div>
        </div>

        <div className="bento-grid-container">
          {/* Card 1: AI Discovery (Span 2 cols) */}
          <div className="bento-card bento-span-2 bento-ai-discovery">
            <div className="bento-card-header">
              <span className="bento-badge"><Zap size={13} /> Real-Time Telemetry</span>
              <h3 className="bento-title">AI Discovery Engine</h3>
              <p className="bento-desc">
                Continuously tracks official sponsor portals, Devpost, HackerEarth, and GitHub repositories to index verified hackathons within minutes of publication.
              </p>
            </div>
            <div className="bento-discovery-visual">
              <div className="discovery-query-chip">
                <span className="query-dot" />
                <span>"Find Gemini 2.0 hackathons with $100K+ prize pools"</span>
              </div>
              <div className="discovery-results-preview">
                <div className="result-mini-row">
                  <span className="res-logo google">GD</span>
                  <div className="res-meta">
                    <b>Google Gemini AI Global Hackathon</b>
                    <small>Online · $150,000 Cash Pool · 98% AI Match</small>
                  </div>
                  <span className="res-tag">Verified</span>
                </div>
                <div className="result-mini-row">
                  <span className="res-logo msft">MS</span>
                  <div className="res-meta">
                    <b>Microsoft Imagine Cup 2027</b>
                    <small>Seattle / Hybrid · $100,000 · 96% Match</small>
                  </div>
                  <span className="res-tag">Verified</span>
                </div>
              </div>
            </div>
          </div>

          {/* Card 2: AI Predictions */}
          <div className="bento-card bento-ai-predictions">
            <div className="bento-card-header">
              <span className="bento-badge purple"><TrendingUp size={13} /> Cadence Radar</span>
              <h3 className="bento-title">AI Recurrence Predictions</h3>
              <p className="bento-desc">
                Machine learning model forecasting seasonal developer competitions weeks before official press releases.
              </p>
            </div>
            <div className="bento-prediction-visual">
              <div className="pred-gauge-circle">
                <span className="pred-pct">94%</span>
                <span className="pred-label">Probability</span>
              </div>
              <div className="pred-preview-info">
                <b>Microsoft AI Cloud Summit</b>
                <small>Expected Window: May 2027</small>
                <span className="pred-status-pill">Signal Lock Active</span>
              </div>
            </div>
          </div>

          {/* Card 3: Global Radar */}
          <div className="bento-card bento-global-radar">
            <div className="bento-card-header">
              <span className="bento-badge cyan"><Globe2 size={13} /> Global Mesh</span>
              <h3 className="bento-title">Global Radar Tracking</h3>
              <p className="bento-desc">
                Live geolocation coordinates spanning SF, London, Bengaluru, Tokyo, Geneva, and Singapore.
              </p>
            </div>
            <div className="bento-radar-visual">
              <div className="radar-node-pill sf"><span>SF Hub</span><b>3 Events</b></div>
              <div className="radar-node-pill blr"><span>Bengaluru</span><b>4 Events</b></div>
              <div className="radar-node-pill ldn"><span>London</span><b>2 Events</b></div>
              <div className="radar-node-pill tyo"><span>Tokyo</span><b>2 Events</b></div>
            </div>
          </div>

          {/* Card 4: Prize Pool Tracking */}
          <div className="bento-card bento-prize-tracking">
            <div className="bento-card-header">
              <span className="bento-badge gold"><Trophy size={13} /> Non-Dilutive Capital</span>
              <h3 className="bento-title">Active Prize Tracking</h3>
              <p className="bento-desc">
                Real-time tracking of cash pools, GPU credits, and venture interview fast-tracks.
              </p>
            </div>
            <div className="bento-prize-visual">
              <div className="big-prize-display">$1,420,000+</div>
              <div className="prize-tiers-row">
                <div><small>1st Place Tiers</small><b>$50K - $100K</b></div>
                <div><small>Cloud Credits</small><b>$20K / Team</b></div>
              </div>
            </div>
          </div>

          {/* Card 5: Organizer Intelligence (Span 2 cols) */}
          <div className="bento-card bento-span-2 bento-organizers">
            <div className="bento-card-header">
              <span className="bento-badge"><Building2 size={13} /> Verified Sponsors</span>
              <h3 className="bento-title">Organizer Intelligence</h3>
              <p className="bento-desc">
                In-depth annual budget patterns and hiring track records for premier technology organizers.
              </p>
            </div>
            <div className="bento-organizers-row">
              <div className="org-mini-tile">
                <span className="org-avatar ms">MS</span>
                <b>Microsoft</b>
                <small>$1.4M+ Given · 42K Followers</small>
              </div>
              <div className="org-mini-tile">
                <span className="org-avatar goog">GD</span>
                <b>Google Devs</b>
                <small>$2.1M+ Given · 68K Followers</small>
              </div>
              <div className="org-mini-tile">
                <span className="org-avatar aws">AWS</span>
                <b>AWS Bedrock</b>
                <small>$950K+ Given · 38K Followers</small>
              </div>
              <div className="org-mini-tile">
                <span className="org-avatar nv">NV</span>
                <b>NVIDIA</b>
                <small>$1.1M+ Given · 51K Followers</small>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── 15. Visual AI Intelligence Signal Flow ────────────────────────────────────
export function AIPredictionSignalFlow({ prediction }) {
  const defaultPrediction = prediction || {
    event: "Microsoft AI Cloud Innovation Summit 2027",
    organizer: "Microsoft",
    probability: 0.94,
    window: "May 15 - Jun 20, 2027",
  };

  const signals = [
    { title: "Organizer History", desc: "Annual recurrence observed for 4 consecutive years (98% correlation)" },
    { title: "Event Timing & Cadence", desc: "Q2 fiscal release cycle synchronized with Microsoft Build" },
    { title: "Technology Trends", desc: "Azure AI Foundry & Copilot Studio developer incentives spiked +34%" },
    { title: "Community Activity", desc: "DNS registrations and GitHub sample repository commits detected" },
  ];

  return (
    <div className="ai-intelligence-flow-card">
      <div className="flow-card-top">
        <span className="flow-eyebrow"><Sparkles size={13} /> AI INTELLIGENCE CASCADE</span>
        <span className="flow-match-pill">{Math.round(defaultPrediction.probability * 100)}% MATCH</span>
      </div>

      <div className="flow-diagram-container">
        {/* Step 0: Input Signals */}
        <div className="flow-step-node root-node">
          <span className="node-tag">DATA SIGNALS</span>
          <b>Multi-Vector Continuous Ingestion</b>
        </div>
        <div className="flow-arrow-down">↓</div>

        {/* 4 Signals Grid / List */}
        <div className="flow-signals-cascade-grid">
          {signals.map((sig, idx) => (
            <div key={idx} className="cascade-signal-card">
              <span className="cascade-idx">0{idx + 1}</span>
              <div>
                <b>{sig.title}</b>
                <small>{sig.desc}</small>
              </div>
            </div>
          ))}
        </div>

        <div className="flow-arrow-down">↓</div>

        {/* Step 5: AI Analysis */}
        <div className="flow-step-node analysis-node">
          <span className="node-tag">AI ANALYSIS</span>
          <b>Statistical Recurrence & Bayesian Cadence Synthesis</b>
        </div>
        <div className="flow-arrow-down">↓</div>

        {/* Step 6: Prediction Output */}
        <div className="flow-final-prediction-box">
          <div className="final-pred-header">
            <span className="final-org">{defaultPrediction.organizer}</span>
            <span className="final-score-badge">
              <Sparkles size={13} /> {Math.round(defaultPrediction.probability * 100)}% MATCH
            </span>
          </div>
          <h3 className="final-event-title">{defaultPrediction.event}</h3>
          <div className="final-window-row">
            <Clock3 size={15} /> Expected Window: <b>{defaultPrediction.window}</b>
          </div>
        </div>
      </div>
    </div>
  );
}

