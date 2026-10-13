import React, { useState, useEffect, useRef, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Sparkles, Globe2, Compass, ArrowRight, Trophy, Clock3,
  Building2, Zap, TrendingUp,
  MapPin, CheckCircle2, ChevronRight, Flame,
  Bookmark, BookmarkCheck, Search, ZoomIn, ZoomOut, RotateCcw,
  SlidersHorizontal, ArrowUpRight, X, Laptop
} from "lucide-react";
import { CompanyLogo } from "./CompanyLogo";

// ─── 1. Aceternity Spotlight Cone ──────────────────────────────────────────────
export function AceternitySpotlight({ className = "", fill = "#6366F1" }) {
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
          fillOpacity="0.08"
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

// Conflict-free label offsets to prevent overlapping labels
const HUB_LABEL_CONFIG = {
  "Seattle": { dx: 0, dy: -18, anchor: "middle" },
  "San Francisco": { dx: -12, dy: 18, anchor: "end" },
  "San Jose": { dx: -12, dy: 18, anchor: "end" },
  "New York": { dx: 12, dy: -12, anchor: "start" },
  "London": { dx: -14, dy: -16, anchor: "end" },
  "Geneva": { dx: 14, dy: 18, anchor: "start" },
  "Mumbai": { dx: -14, dy: -14, anchor: "end" },
  "Bengaluru": { dx: 14, dy: 18, anchor: "start" },
  "Singapore": { dx: 12, dy: 16, anchor: "start" },
  "Tokyo": { dx: 14, dy: -12, anchor: "start" },
};

// Recognizable world map continent outlines (Equirectangular 1000x500)
const WORLD_CONTINENTS = [
  // North America
  "M 110,65 L 140,55 L 180,50 L 220,55 L 260,70 L 300,90 L 315,120 L 295,140 L 270,145 L 245,175 L 255,205 L 235,215 L 210,195 L 185,160 L 145,150 L 130,120 L 105,95 Z",
  // Greenland
  "M 340,40 L 380,35 L 400,55 L 375,80 L 340,70 Z",
  // South America
  "M 270,250 L 315,260 L 350,290 L 345,340 L 320,390 L 295,445 L 285,420 L 290,360 L 265,300 L 260,265 Z",
  // Europe
  "M 460,110 L 490,90 L 525,85 L 560,95 L 565,135 L 530,150 L 495,155 L 465,145 L 455,125 Z",
  // British Isles
  "M 460,95 L 475,85 L 470,115 L 455,110 Z",
  // Africa
  "M 470,175 L 540,175 L 585,210 L 595,270 L 550,360 L 515,365 L 480,270 L 460,210 Z",
  // Madagascar
  "M 605,325 L 615,320 L 610,360 L 600,355 Z",
  // Asia
  "M 565,95 L 630,80 L 720,75 L 810,85 L 880,105 L 890,145 L 850,170 L 810,195 L 755,190 L 730,220 L 695,210 L 670,175 L 610,170 L 575,135 Z",
  // Indian Subcontinent
  "M 685,185 L 725,185 L 735,225 L 715,265 L 690,225 Z",
  // Japan / East Asia
  "M 875,130 L 895,145 L 885,175 L 870,165 Z",
  // Southeast Asia / Malay
  "M 760,230 L 805,240 L 830,265 L 780,285 L 750,250 Z",
  // Australia
  "M 795,335 L 860,320 L 900,345 L 885,405 L 825,410 L 790,375 Z",
  // New Zealand
  "M 920,410 L 935,405 L 930,440 L 915,435 Z"
];

export function AceternityWorldMap({
  events = [],
  selectedCategory = "ALL",
  selectedCity = null,
  onSelectEvent,
  onSelectCity,
  className = "",
  compact = false,
}) {
  const [hoveredHub, setHoveredHub] = useState(null);
  const [zoomLevel, setZoomLevel] = useState(1);

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

  // Aggregate events by City Hubs so beacons never duplicate or collide
  const cityHubs = useMemo(() => {
    const hubsMap = new Map();
    filteredEvents.forEach((evt) => {
      if (!evt.coordinates || !evt.coordinates.lat) return;
      const cityName = evt.city || evt.location.split("(")[0].trim();
      const { x, y } = geoToSvg(evt.coordinates.lat, evt.coordinates.lng, 1000, 500);

      if (!hubsMap.has(cityName)) {
        hubsMap.set(cityName, {
          id: `hub-${cityName.toLowerCase().replace(/\s+/g, "-")}`,
          city: cityName,
          country: evt.country || "Global",
          coordinates: evt.coordinates,
          svgX: x,
          svgY: y,
          events: [evt],
          totalPrizeNumeric: evt.prizeNumeric || 0,
          labelConfig: HUB_LABEL_CONFIG[cityName] || { dx: 0, dy: -14, anchor: "middle" }
        });
      } else {
        const hub = hubsMap.get(cityName);
        hub.events.push(evt);
        hub.totalPrizeNumeric += evt.prizeNumeric || 0;
      }
    });
    return Array.from(hubsMap.values());
  }, [filteredEvents]);

  // Arcs between active global city hubs
  const arcs = useMemo(() => {
    if (cityHubs.length < 2) return [];
    const connections = [];
    for (let i = 0; i < cityHubs.length - 1; i++) {
      const from = cityHubs[i];
      const to = cityHubs[i + 1];
      const dx = to.svgX - from.svgX;
          const midX = (from.svgX + to.svgX) / 2;
      const midY = (from.svgY + to.svgY) / 2 - Math.min(60, Math.max(25, Math.abs(dx) * 0.18));
      connections.push({
        id: `arc-${from.id}-${to.id}`,
        d: `M ${from.svgX} ${from.svgY} Q ${midX} ${midY} ${to.svgX} ${to.svgY}`,
        from,
        to,
      });
    }
    return connections;
  }, [cityHubs]);

  const handleHubClick = (hub) => {
    if (onSelectCity) {
      onSelectCity(hub.city);
    }
    if (onSelectEvent && hub.events.length > 0) {
      onSelectEvent(hub.events[0]);
    }
  };

  const handleZoomIn = () => setZoomLevel((z) => Math.min(2.2, z + 0.35));
  const handleZoomOut = () => setZoomLevel((z) => Math.max(1, z - 0.35));
  const handleResetZoom = () => setZoomLevel(1);

  // Compute zoomed viewBox around center or hovered hub
  const viewWidth = 1000 / zoomLevel;
  const viewHeight = 500 / zoomLevel;
  const viewX = (1000 - viewWidth) / 2;
  const viewY = (500 - viewHeight) / 2;

  return (
    <div className={`world-map-wrapper ${compact ? "compact" : ""} ${className}`}>
      {/* Ambient background glow & grid */}
      <div className="map-ambient-glow" />
      <div className="map-grid-overlay" />

      {/* Interactive Map Controls */}
      <div className="map-zoom-controls">
        <button type="button" onClick={handleZoomIn} className="map-ctrl-btn" title="Zoom In">
          <ZoomIn size={14} />
        </button>
        <button type="button" onClick={handleZoomOut} className="map-ctrl-btn" title="Zoom Out">
          <ZoomOut size={14} />
        </button>
        <button type="button" onClick={handleResetZoom} className="map-ctrl-btn" title="Reset Projection">
          <RotateCcw size={13} />
        </button>
      </div>

      <svg
        viewBox={`${viewX} ${viewY} ${viewWidth} ${viewHeight}`}
        className="world-map-svg"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <radialGradient id="beaconGlowCyan" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#00d2ff" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="arcBeamGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#00d2ff" stopOpacity="0.9" />
            <stop offset="50%" stopColor="#818cf8" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#00d2ff" stopOpacity="0.9" />
          </linearGradient>
          <filter id="mapGlowFilter" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Global Coordinate Grid (Meridians & Parallels) */}
        <g className="map-geo-grid" stroke="rgba(15, 23, 42, 0.05)" strokeWidth="0.8" strokeDasharray="3 4">
          {/* Parallels */}
          <line x1="0" y1="125" x2="1000" y2="125" />
          <line x1="0" y1="250" x2="1000" y2="250" stroke="rgba(79, 70, 229, 0.1)" strokeWidth="1" />
          <line x1="0" y1="375" x2="1000" y2="375" />
          {/* Meridians */}
          <line x1="166" y1="0" x2="166" y2="500" />
          <line x1="333" y1="0" x2="333" y2="500" />
          <line x1="500" y1="0" x2="500" y2="500" stroke="rgba(79, 70, 229, 0.1)" strokeWidth="1" />
          <line x1="666" y1="0" x2="666" y2="500" />
          <line x1="833" y1="0" x2="833" y2="500" />
        </g>

        {/* Recognizable Continent Silhouettes */}
        <g className="world-continents-group">
          {WORLD_CONTINENTS.map((pathD, idx) => (
            <path
              key={`continent-${idx}`}
              d={pathD}
              className="world-continent-path"
              fill="#F1F5F9"
              stroke="#CBD5E1"
              strokeWidth="1.2"
              strokeLinejoin="round"
            />
          ))}
        </g>

        {/* Telemetry Connecting Arcs */}
        <g className="telemetry-arcs-group">
          {arcs.map((arc) => (
            <g key={arc.id}>
              <path
                d={arc.d}
                fill="none"
                stroke="rgba(99, 102, 241, 0.2)"
                strokeWidth="1.2"
                strokeDasharray="4 4"
              />
              <path
                d={arc.d}
                fill="none"
                stroke="url(#arcBeamGrad)"
                strokeWidth="1.6"
                strokeLinecap="round"
                className="animated-arc-beam"
              />
            </g>
          ))}
        </g>

        {/* Global City Hub Beacons with Smart Label Positions */}
        <g className="location-markers-group">
          {cityHubs.map((hub) => {
            const isHovered = hoveredHub?.id === hub.id;
            const isSelected = selectedCity === hub.city;
            const { dx, dy, anchor } = hub.labelConfig;

            return (
              <g
                key={hub.id}
                className={`map-beacon-node ${isHovered || isSelected ? "hovered" : ""}`}
                transform={`translate(${hub.svgX}, ${hub.svgY})`}
                onMouseEnter={() => setHoveredHub(hub)}
                onMouseLeave={() => setHoveredHub(null)}
                onClick={() => handleHubClick(hub)}
                style={{ cursor: "pointer" }}
              >
                {/* Concentric Pulsing Radar Rings */}
                <circle r="14" className="beacon-ping-ring ping-1" />
                <circle r="22" className="beacon-ping-ring ping-2" />

                {/* Central Beacon Core */}
                <circle
                  r={isSelected ? "8" : isHovered ? "7" : "5.5"}
                  fill={isSelected ? "#38bdf8" : "#00d2ff"}
                  className="beacon-core-dot"
                  filter="url(#mapGlowFilter)"
                />
                <circle r="2" fill="#ffffff" />

                {/* Event Count Pill Indicator */}
                {hub.events.length > 1 && (
                  <g transform="translate(6, -6)">
                    <rect
                      x="0"
                      y="-7"
                      width="13"
                      height="12"
                      rx="3"
                      fill="#6366f1"
                      stroke="#05070d"
                      strokeWidth="1"
                    />
                    <text
                      x="6.5"
                      y="2"
                      fill="#ffffff"
                      fontSize="8"
                      fontWeight="bold"
                      textAnchor="middle"
                      fontFamily="JetBrains Mono, monospace"
                    >
                      {hub.events.length}
                    </text>
                  </g>
                )}

                {/* City Label with collision-free offset */}
                <text
                  x={dx}
                  y={dy}
                  textAnchor={anchor}
                  className={`beacon-city-label ${isHovered || isSelected ? "active" : ""}`}
                >
                  {hub.city}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Floating Tooltip upon Hub Hover */}
      {hoveredHub && (
        <div
          className="map-animated-tooltip"
          style={{
            left: `${(hoveredHub.svgX / 1000) * 100}%`,
            top: `${(hoveredHub.svgY / 500) * 100}%`,
          }}
          onClick={() => handleHubClick(hoveredHub)}
        >
          <div className="tooltip-glass-panel">
            <div className="tooltip-top-row">
              <span className="tooltip-org">
                <MapPin size={12} /> {hoveredHub.city}, {hoveredHub.country}
              </span>
              <span className="tooltip-ai-badge">
                <Sparkles size={11} /> {hoveredHub.events.length} {hoveredHub.events.length === 1 ? "Event" : "Events"}
              </span>
            </div>

            <h4 className="tooltip-title">{hoveredHub.events[0]?.title}</h4>

            <div className="tooltip-details-grid">
              <div>
                <small>Combined Prize</small>
                <b className="prize-gold">${(hoveredHub.totalPrizeNumeric).toLocaleString()}</b>
              </div>
              <div>
                <small>Organizer</small>
                <b>{hoveredHub.events[0]?.organizer}</b>
              </div>
              <div>
                <small>Closes in</small>
                <b>{hoveredHub.events[0]?.deadlineDays || 4} days</b>
              </div>
            </div>

            <div className="tooltip-cta-line">
              <span>Click beacon to explore local events</span>
              <ChevronRight size={13} />
            </div>
          </div>
        </div>
      )}

      {/* Live Radar Telemetry Status Bar */}
      <div className="map-status-overlay">
        <div className="map-telemetry-badge">
          <span className="live-pulse-dot" />
          <span><b>{cityHubs.length}</b> ACTIVE HUBS · <b>{filteredEvents.length}</b> VERIFIED BEACONS</span>
        </div>
        <div className="map-coverage-text">
          <span>Click any city beacon to filter opportunities</span>
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
          <radialGradient id="globeSphereGrad" cx="35%" cy="30%" r="70%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.9" />
            <stop offset="60%" stopColor="#F8FAFC" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#E2E8F0" stopOpacity="1" />
          </radialGradient>
          <radialGradient id="globeAtmosphere" cx="50%" cy="50%" r="50%">
            <stop offset="85%" stopColor="#4F46E5" stopOpacity="0" />
            <stop offset="100%" stopColor="#4F46E5" stopOpacity="0.15" />
          </radialGradient>
        </defs>

        {/* Outer Globe Sphere */}
        <circle cx={cx} cy={cy} r={R} fill="url(#globeSphereGrad)" />
        <circle cx={cx} cy={cy} r={R} fill="url(#globeAtmosphere)" stroke="rgba(79, 70, 229, 0.25)" strokeWidth="1.2" />

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
              stroke="rgba(79, 70, 229, 0.18)"
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
              stroke="rgba(2, 132, 199, 0.18)"
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

// ─── 7. Right Hero Visual: Live Radar Signal Monitor ─────────────────────────────
export function HeroInteractiveRadar({ events = [] }) {
  const [filter, setFilter] = useState("trending"); // "trending" | "prize" | "closing"
  const navigate = useNavigate();

  const displayedList = useMemo(() => {
    let list = [...events];
    if (filter === "prize") {
      list.sort((a, b) => (b.prizeNumeric || 0) - (a.prizeNumeric || 0));
    } else if (filter === "closing") {
      list.sort((a, b) => (a.deadlineDays || 99) - (b.deadlineDays || 99));
    } else {
      list = list.filter((e) => e.trending || e.featured);
    }
    return list.slice(0, 4);
  }, [events, filter]);

  return (
    <div className="hero-interactive-radar-card">
      {/* Top Header Mode Toggle & Status */}
      <div className="radar-card-topbar">
        <div className="radar-status-badge">
          <span className="radar-pulse-dot" />
          <span><b>LIVE RADAR STREAM</b></span>
        </div>
        <div className="radar-view-mode-toggle">
          <button
            type="button"
            className={`radar-mode-btn ${filter === "trending" ? "active" : ""}`}
            onClick={() => setFilter("trending")}
          >
            Trending
          </button>
          <button
            type="button"
            className={`radar-mode-btn ${filter === "prize" ? "active" : ""}`}
            onClick={() => setFilter("prize")}
          >
            Top Prizes
          </button>
          <button
            type="button"
            className={`radar-mode-btn ${filter === "closing" ? "active" : ""}`}
            onClick={() => setFilter("closing")}
          >
            Closing
          </button>
        </div>
      </div>

      {/* Main Interactive Stream List */}
      <div className="radar-stream-list">
        {displayedList.map((item) => (
          <div
            key={item.id}
            className="radar-stream-row"
            onClick={() => navigate(`/event/${item.id}`)}
          >
            <div className="stream-avatar">
              <CompanyLogo organizerKey={item.organizerKey} name={item.organizer} size={22} />
            </div>
            <div className="stream-info">
              <div className="stream-title-row">
                <span className="stream-title">{item.title}</span>
                <ArrowUpRight size={13} className="stream-arrow" />
              </div>
              <div className="stream-meta">
                <span className="stream-org">{item.organizer}</span>
                <span className="meta-bullet">•</span>
                <span className="stream-deadline">
                  <Clock3 size={11} /> {item.deadlineDays || 4}d left
                </span>
              </div>
            </div>
            <div className="stream-badges">
              <span className="stream-prize">{item.prize}</span>
              <span className="stream-match">{item.aiMatchScore || 95}% Match</span>
            </div>
          </div>
        ))}
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

// ─── 12. Aceternity Live Radar Section with Filtering & Opportunity Grid ──────────
export function LiveRadarSection({
  events = [],
  onRegister,
  isSaved = () => false,
  onToggleSave = () => {},
}) {
  const [activeFilter, setActiveFilter] = useState("ALL");
  const [selectedCity, setSelectedCity] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedMode, setSelectedMode] = useState("ALL");
  const [sortBy, setSortBy] = useState("deadline");

  const filters = [
    "ALL",
    "AI",
    "CLOUD",
    "WEB3",
    "ROBOTICS",
    "CYBERSECURITY",
    "OPEN SOURCE",
  ];

  // Genuine multi-criteria filtering for opportunities
  const filteredOpportunities = useMemo(() => {
    return events
      .filter((e) => {
        // Category filter
        if (activeFilter !== "ALL") {
          const cat = activeFilter.toLowerCase();
          const matchCat =
            (e.radarCategory && e.radarCategory.toLowerCase() === cat) ||
            (e.category && e.category.toLowerCase().includes(cat)) ||
            (e.tags && e.tags.some((t) => t.toLowerCase().includes(cat)));
          if (!matchCat) return false;
        }

        // City beacon filter
        if (selectedCity) {
          const cityName = (e.city || "").toLowerCase();
          const locName = (e.location || "").toLowerCase();
          const target = selectedCity.toLowerCase();
          if (!cityName.includes(target) && !locName.includes(target)) {
            return false;
          }
        }

        // Mode filter
        if (selectedMode !== "ALL") {
          if ((e.mode || "").toLowerCase() !== selectedMode.toLowerCase()) {
            return false;
          }
        }

        // Search query
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchSearch =
            (e.title && e.title.toLowerCase().includes(q)) ||
            (e.organizer && e.organizer.toLowerCase().includes(q)) ||
            (e.city && e.city.toLowerCase().includes(q)) ||
            (e.description && e.description.toLowerCase().includes(q)) ||
            (e.tags && e.tags.some((t) => t.toLowerCase().includes(q)));
          if (!matchSearch) return false;
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === "deadline") {
          return (a.deadlineDays || 99) - (b.deadlineDays || 99);
        }
        if (sortBy === "prize") {
          return (b.prizeNumeric || 0) - (a.prizeNumeric || 0);
        }
        if (sortBy === "match") {
          return (b.aiMatchScore || 0) - (a.aiMatchScore || 0);
        }
        return 0;
      });
  }, [events, activeFilter, selectedCity, selectedMode, searchQuery, sortBy]);

  const handleCitySelect = (city) => {
    if (selectedCity === city) {
      setSelectedCity(null); // toggle off
    } else {
      setSelectedCity(city);
    }
  };

  return (
    <section className="live-radar-section" id="radar-explorer">
      <div className="section-container">
        {/* Section Header */}
        <div className="section-header-flex">
          <div>
            <div className="section-eyebrow">
              <Zap size={14} /> REAL-TIME SATELLITE TELEMETRY
            </div>
            <h2 className="section-heading">Global Hackathon Radar</h2>
            <p className="section-subtext">
              Track live hackathon signals, developer hubs, and cash prize deployments across worldwide innovation epicenters. Select any beacon to explore local opportunities.
            </p>
          </div>

          <div className="radar-pulse-indicator-pill">
            <span className="live-pulse-dot" />
            <span>Telemetry Active · 12 Verified Hubs</span>
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
            selectedCity={selectedCity}
            onSelectCity={handleCitySelect}
          />
        </div>

        {/* ─── Opportunity Discovery Panel Directly Below Map ─────────── */}
        <div className="radar-opportunities-panel">
          {/* Header & City Filter Notice */}
          <div className="opp-discovery-header">
            <div className="opp-title-group">
              <div className="opp-eyebrow">
                <Sparkles size={13} /> VERIFIED OPPORTUNITIES
              </div>
              <h3 className="opp-section-title">
                {selectedCity ? `Opportunities in ${selectedCity}` : "Explore Opportunities Worldwide"}
              </h3>
              <p className="opp-section-desc">
                Displaying <b>{filteredOpportunities.length}</b> verified competitions
                {selectedCity ? ` centered around ${selectedCity}` : ""}. Real deadlines, prizes, and application links.
              </p>
            </div>

            {selectedCity && (
              <div className="active-city-filter-badge">
                <MapPin size={13} />
                <span>Beacon: <b>{selectedCity}</b></span>
                <button
                  type="button"
                  onClick={() => setSelectedCity(null)}
                  className="clear-city-btn"
                  title="Clear city filter"
                >
                  <X size={13} />
                </button>
              </div>
            )}
          </div>

          {/* Search, Format & Sort Controls Toolbar */}
          <div className="opp-controls-toolbar">
            <div className="opp-search-box">
              <Search size={15} />
              <input
                type="text"
                placeholder="Search by title, skills, or organizer..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="opp-search-input"
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery("")} className="opp-clear-search">
                  <X size={14} />
                </button>
              )}
            </div>

            <div className="opp-format-pills">
              {["ALL", "Remote", "In-Person", "Hybrid"].map((mode) => (
                <button
                  key={mode}
                  className={`opp-format-btn ${selectedMode === mode ? "active" : ""}`}
                  onClick={() => setSelectedMode(mode)}
                >
                  {mode === "ALL" ? "All Formats" : mode}
                </button>
              ))}
            </div>

            <div className="opp-sort-select-wrapper">
              <SlidersHorizontal size={14} />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="opp-sort-select"
              >
                <option value="deadline">Closing Soonest</option>
                <option value="prize">Highest Prize Pool</option>
                <option value="match">Highest AI Match</option>
              </select>
            </div>
          </div>

          {/* Opportunities Cards Grid */}
          {filteredOpportunities.length > 0 ? (
            <div className="opp-cards-grid">
              {filteredOpportunities.map((item) => {
                const saved = isSaved(item.id);
                return (
                  <div key={item.id} className="opportunity-cyber-card">
                    <div className="opp-card-glow-bar" />

                    <div className="opp-card-header">
                      <div className="opp-header-tags">
                        <span className={`opp-mode-pill mode-${(item.mode || "remote").toLowerCase()}`}>
                          {item.mode === "Remote" ? (
                            <Globe2 size={12} />
                          ) : item.mode === "Hybrid" ? (
                            <Laptop size={12} />
                          ) : (
                            <MapPin size={12} />
                          )}
                          {item.mode || "Remote"}
                        </span>
                        <span className="opp-category-pill">
                          {item.radarCategory || item.category}
                        </span>
                        <span className="opp-verified-pill">
                          <CheckCircle2 size={11} /> Verified
                        </span>
                      </div>

                      <button
                        type="button"
                        className={`opp-bookmark-btn ${saved ? "saved" : ""}`}
                        onClick={() => onToggleSave(item.id)}
                        title={saved ? "Remove from bookmarks" : "Save hackathon"}
                      >
                        {saved ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}
                      </button>
                    </div>

                    <div className="opp-body">
                      <div className="opp-org-line">
                        <span className="opp-org-avatar">
                          <CompanyLogo organizerKey={item.organizerKey} name={item.organizer} size={18} />
                        </span>
                        <span className="opp-org-name">{item.organizer}</span>
                        <span className="opp-dot-sep">·</span>
                        <span className="opp-location-tag">
                          <MapPin size={11} /> {item.city || item.location}
                        </span>
                      </div>

                      <h3 className="opp-title">
                        <Link to={`/event/${item.id}`}>{item.title}</Link>
                      </h3>

                      <p className="opp-desc-snippet">{item.description}</p>
                    </div>

                    {/* Key Metrics Row: Prize, Deadline, Countdown, Eligibility */}
                    <div className="opp-metrics-grid">
                      <div className="opp-metric-cell">
                        <small>Prize Pool</small>
                        <b className="prize-cyan">{item.prize}</b>
                      </div>
                      <div className="opp-metric-cell">
                        <small>Deadline</small>
                        <b>{item.deadline}</b>
                      </div>
                      <div className="opp-metric-cell countdown-cell">
                        <small>Countdown</small>
                        <span className={`countdown-chip ${item.deadlineDays <= 3 ? "urgent" : ""}`}>
                          {item.deadlineDays <= 3 ? (
                            <Flame size={12} className="flame-pulse" />
                          ) : (
                            <Clock3 size={12} />
                          )}
                          <b>{item.deadlineDays}d left</b>
                        </span>
                      </div>
                      <div className="opp-metric-cell">
                        <small>Eligibility</small>
                        <span className="opp-eligibility-text">{item.eligibility || "Open to All"}</span>
                      </div>
                    </div>

                    {/* AI Match Reason Banner */}
                    <div className="opp-ai-match-banner">
                      <div className="ai-match-score-pill">
                        <Sparkles size={11} /> {item.aiMatchScore || 94}% AI Match
                      </div>
                      <span className="ai-match-reason">
                        {item.radarCategory === "AI"
                          ? "Matches generative AI, multimodal agents, and LLM orchestration tracks"
                          : item.radarCategory === "CLOUD"
                          ? "High alignment with cloud infrastructure and enterprise deployment models"
                          : item.radarCategory === "WEB3"
                          ? "Optimal fit for decentralized protocols, smart contracts, and ZK proofs"
                          : item.radarCategory === "ROBOTICS"
                          ? "Direct match for microservice acceleration, inference pipelines, and IoT"
                          : "Strong timing match with verified student and developer eligibility"}
                      </span>
                    </div>

                    {/* Footer Tags & Actions */}
                    <div className="opp-footer-actions">
                      <div className="opp-tags-row">
                        {item.tags?.slice(0, 3).map((tag) => (
                          <span key={tag} className="opp-tag-chip">
                            #{tag}
                          </span>
                        ))}
                      </div>

                      <div className="opp-action-buttons">
                        <Link to={`/event/${item.id}`} className="btn-secondary btn-sm">
                          View Details
                        </Link>
                        <button
                          type="button"
                          className="btn-primary btn-sm"
                          onClick={() => onRegister && onRegister(item)}
                        >
                          Apply Now <ArrowRight size={13} />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="opp-empty-state">
              <div className="opp-empty-icon">
                <Compass size={32} />
              </div>
              <h4>No Hackathons Found</h4>
              <p>
                No verified opportunities currently match your filter criteria in this view.
              </p>
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => {
                  setActiveFilter("ALL");
                  setSelectedCity(null);
                  setSearchQuery("");
                  setSelectedMode("ALL");
                }}
              >
                Reset All Filters
              </button>
            </div>
          )}
        </div>
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
                <span className="org-avatar">
                  <CompanyLogo organizerKey="microsoft" size={24} />
                </span>
                <b>Microsoft</b>
                <small>$1.4M+ Given · 42K Followers</small>
              </div>
              <div className="org-mini-tile">
                <span className="org-avatar">
                  <CompanyLogo organizerKey="google" size={24} />
                </span>
                <b>Google Devs</b>
                <small>$2.1M+ Given · 68K Followers</small>
              </div>
              <div className="org-mini-tile">
                <span className="org-avatar">
                  <CompanyLogo organizerKey="aws" size={24} />
                </span>
                <b>AWS Bedrock</b>
                <small>$950K+ Given · 38K Followers</small>
              </div>
              <div className="org-mini-tile">
                <span className="org-avatar">
                  <CompanyLogo organizerKey="nvidia" size={24} />
                </span>
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
