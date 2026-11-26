/** Editorial visual stage for the Hackathon Radar hero using live catalog counts when loaded. */
export default function ShowcaseVisual({ totalEvents, organizationCount }) {
  const eventCountLabel = Number.isInteger(totalEvents) ? String(totalEvents) : 'Live';
  const orgCountLabel = Number.isInteger(organizationCount) ? String(organizationCount) : 'Verified';

  return (
    <div className="radar-hero-stage" aria-hidden="true">
      <div className="radar-device-frame">
        <div className="radar-device-chrome">
          <div className="radar-chrome-dots">
            <span />
            <span />
            <span />
          </div>
          <span>catalog.hackathonradar</span>
          <span>UTC · Reviewed</span>
        </div>

        <div className="radar-device-body">
          <div>
            <span className="platform-eyebrow">LIVE CATALOG OVERVIEW</span>
            <p className="radar-band-lead">
              Every listing is reviewed before publication, with original organizer URLs and UTC calendar filtering.
            </p>
            <div className="radar-stage-metrics">
              <div className="radar-stage-stat">
                <strong>{eventCountLabel}</strong>
                <span>Matching catalog events</span>
              </div>
              <div className="radar-stage-stat">
                <strong>{orgCountLabel}</strong>
                <span>Indexed organizations</span>
              </div>
            </div>
          </div>

          <div className="radar-stage-visual">
            <svg className="radar-svg-artwork" viewBox="0 0 240 240" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="120" cy="120" r="104" stroke="currentColor" strokeOpacity="0.12" strokeWidth="1.5" />
              <circle cx="120" cy="120" r="76" stroke="currentColor" strokeOpacity="0.18" strokeWidth="1.5" />
              <circle cx="120" cy="120" r="48" stroke="currentColor" strokeOpacity="0.24" strokeWidth="1.5" />
              <line x1="16" y1="120" x2="224" y2="120" stroke="currentColor" strokeOpacity="0.1" strokeWidth="1" />
              <line x1="120" y1="16" x2="120" y2="224" stroke="currentColor" strokeOpacity="0.1" strokeWidth="1" />
              <g className="radar-sweep-ring">
                <path d="M120 120 L195 55 A104 104 0 0 1 224 120 Z" fill="#0066cc" fillOpacity="0.14" />
                <line x1="120" y1="120" x2="195" y2="55" stroke="#0066cc" strokeWidth="2" strokeOpacity="0.7" />
              </g>
              <circle cx="120" cy="120" r="10" fill="#0066cc" />
              <circle cx="172" cy="76" r="5" fill="#0066cc" />
              <circle cx="72" cy="156" r="4.5" fill="#4da6ff" />
              <circle cx="164" cy="166" r="4" fill="#0066cc" fillOpacity="0.65" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
}
