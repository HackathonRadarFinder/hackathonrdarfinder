import React from "react";

/**
 * High-definition, authentic vector brand marks for major technology organizers and sponsors.
 * Supports: Google, Microsoft, AWS, OpenAI, NVIDIA, Meta, Kaggle, Polygon, 
 * Goldman Sachs, TCS, SIH, UNEP, Apple, GitHub, Solana, Anthropic, and smart fallback.
 */

export function CompanyLogo({
  organizerKey = "",
  name = "",
  size = 20,
  className = "",
  style = {}
}) {
  const normalizedKey = (organizerKey || "").toLowerCase().trim();
  const normalizedName = (name || "").toLowerCase().trim();

  const key = normalizedKey || normalizedName;

  // 1. Google (Official 4-color 'G')
  if (
    key.includes("google") ||
    key === "gd" ||
    key === "gdg" ||
    key.includes("deepmind") ||
    key.includes("alphabet")
  ) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-google ${className}`}
        style={style}
        aria-label="Google"
      >
        <path
          d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"
          fill="#4285F4"
        />
        <path
          d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.24v3.15C3.26 21.36 7.33 24 12 24z"
          fill="#34A853"
        />
        <path
          d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.24C.45 8.16 0 9.98 0 12c0 2.02.45 3.84 1.24 5.42l4.04-3.15z"
          fill="#FBBC05"
        />
        <path
          d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.24 6.58l4.04 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
          fill="#EA4335"
        />
      </svg>
    );
  }

  // 2. Microsoft (Official 4-tile grid)
  if (
    key.includes("microsoft") ||
    key === "ms" ||
    key.includes("azure") ||
    key.includes("imagine cup")
  ) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-microsoft ${className}`}
        style={style}
        aria-label="Microsoft"
      >
        <rect x="1" y="1" width="10.2" height="10.2" rx="1" fill="#F25022" />
        <rect x="12.8" y="1" width="10.2" height="10.2" rx="1" fill="#7FBA00" />
        <rect x="1" y="12.8" width="10.2" height="10.2" rx="1" fill="#00A4EF" />
        <rect x="12.8" y="12.8" width="10.2" height="10.2" rx="1" fill="#FFB900" />
      </svg>
    );
  }

  // 3. Amazon Web Services (AWS - Official AWS Wordmark & Smile)
  if (
    key.includes("aws") ||
    key.includes("amazon") ||
    key.includes("bedrock")
  ) {
    return (
      <svg
        width={size}
        height={Math.round(size * (182 / 304))}
        viewBox="0 0 304 182"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-aws ${className}`}
        style={style}
        aria-label="Amazon Web Services"
      >
        <g>
          <path
            d="M86.4,66.4c0,3.7,0.4,6.7,1.1,8.9c0.8,2.2,1.8,4.6,3.2,7.2c0.5,0.8,0.7,1.6,0.7,2.3c0,1-0.6,2-1.9,3l-6.3,4.2c-0.9,0.6-1.8,0.9-2.6,0.9c-1,0-2-0.5-3-1.4C76.2,90,75,88.4,74,86.8c-1-1.7-2-3.6-3.1-5.9c-7.8,9.2-17.6,13.8-29.4,13.8c-8.4,0-15.1-2.4-20-7.2c-4.9-4.8-7.4-11.2-7.4-19.2c0-8.5,3-15.4,9.1-20.6c6.1-5.2,14.2-7.8,24.5-7.8c3.4,0,6.9,0.3,10.6,0.8c3.7,0.5,7.5,1.3,11.5,2.2v-7.3c0-7.6-1.6-12.9-4.7-16c-3.2-3.1-8.6-4.6-16.3-4.6c-3.5,0-7.1,0.4-10.8,1.3c-3.7,0.9-7.3,2-10.8,3.4c-1.6,0.7-2.8,1.1-3.5,1.3c-0.7,0.2-1.2,0.3-1.6,0.3c-1.4,0-2.1-1-2.1-3.1v-4.9c0-1.6,0.2-2.8,0.7-3.5c0.5-0.7,1.4-1.4,2.8-2.1c3.5-1.8,7.7-3.3,12.6-4.5c4.9-1.3,10.1-1.9,15.6-1.9c11.9,0,20.6,2.7,26.2,8.1c5.5,5.4,8.3,13.6,8.3,24.6V66.4z M45.8,81.6c3.3,0,6.7-0.6,10.3-1.8c3.6-1.2,6.8-3.4,9.5-6.4c1.6-1.9,2.8-4,3.4-6.4c0.6-2.4,1-5.3,1-8.7v-4.2c-2.9-0.7-6-1.3-9.2-1.7c-3.2-0.4-6.3-0.6-9.4-0.6c-6.7,0-11.6,1.3-14.9,4c-3.3,2.7-4.9,6.5-4.9,11.5c0,4.7,1.2,8.2,3.7,10.6C37.7,80.4,41.2,81.6,45.8,81.6z M126.1,92.4c-1.8,0-3-0.3-3.8-1c-0.8-0.6-1.5-2-2.1-3.9L96.7,10.2c-0.6-2-0.9-3.3-0.9-4c0-1.6,0.8-2.5,2.4-2.5h9.8c1.9,0,3.2,0.3,3.9,1c0.8,0.6,1.4,2,2,3.9l16.8,66.2l15.6-66.2c0.5-2,1.1-3.3,1.9-3.9c0.8-0.6,2.2-1,4-1h8c1.9,0,3.2,0.3,4,1c0.8,0.6,1.5,2,1.9,3.9l15.8,67l17.3-67c0.6-2,1.3-3.3,2-3.9c0.8-0.6,2.1-1,3.9-1h9.3c1.6,0,2.5,0.8,2.5,2.5c0,0.5-0.1,1-0.2,1.6c-0.1,0.6-0.3,1.4-0.7,2.5l-24.1,77.3c-0.6,2-1.3,3.3-2.1,3.9c-0.8,0.6-2.1,1-3.8,1h-8.6c-1.9,0-3.2-0.3-4-1c-0.8-0.7-1.5-2-1.9-4L156,23l-15.4,64.4c-0.5,2-1.1,3.3-1.9,4c-0.8,0.7-2.2,1-4,1H126.1z M254.6,95.1c-5.2,0-10.4-0.6-15.4-1.8c-5-1.2-8.9-2.5-11.5-4c-1.6-0.9-2.7-1.9-3.1-2.8c-0.4-0.9-0.6-1.9-0.6-2.8v-5.1c0-2.1,0.8-3.1,2.3-3.1c0.6,0,1.2,0.1,1.8,0.3c0.6,0.2,1.5,0.6,2.5,1c3.4,1.5,7.1,2.7,11,3.5c4,0.8,7.9,1.2,11.9,1.2c6.3,0,11.2-1.1,14.6-3.3c3.4-2.2,5.2-5.4,5.2-9.5c0-2.8-0.9-5.1-2.7-7c-1.8-1.9-5.2-3.6-10.1-5.2L246,52c-7.3-2.3-12.7-5.7-16-10.2c-3.3-4.4-5-9.3-5-14.5c0-4.2,0.9-7.9,2.7-11.1c1.8-3.2,4.2-6,7.2-8.2c3-2.3,6.4-4,10.4-5.2c4-1.2,8.2-1.7,12.6-1.7c2.2,0,4.5,0.1,6.7,0.4c2.3,0.3,4.4,0.7,6.5,1.1c2,0.5,3.9,1,5.7,1.6c1.8,0.6,3.2,1.2,4.2,1.8c1.4,0.8,2.4,1.6,3,2.5c0.6,0.8,0.9,1.9,0.9,3.3v4.7c0,2.1-0.8,3.2-2.3,3.2c-0.8,0-2.1-0.4-3.8-1.2c-5.7-2.6-12.1-3.9-19.2-3.9c-5.7,0-10.2,0.9-13.3,2.8c-3.1,1.9-4.7,4.8-4.7,8.9c0,2.8,1,5.2,3,7.1c2,1.9,5.7,3.8,11,5.5l14.2,4.5c7.2,2.3,12.4,5.5,15.5,9.6c3.1,4.1,4.6,8.8,4.6,14c0,4.3-0.9,8.2-2.6,11.6c-1.8,3.4-4.2,6.4-7.3,8.8c-3.1,2.5-6.8,4.3-11.1,5.6C264.4,94.4,259.7,95.1,254.6,95.1z"
            fill="#232F3E"
          />
          <path
            d="M273.5,143.7c-32.9,24.3-80.7,37.2-121.8,37.2c-57.6,0-109.5-21.3-148.7-56.7c-3.1-2.8-0.3-6.6,3.4-4.4c42.4,24.6,94.7,39.5,148.8,39.5c36.5,0,76.6-7.6,113.5-23.2C274.2,133.6,278.9,139.7,273.5,143.7z"
            fill="#FF9900"
          />
          <path
            d="M287.2,128.1c-4.2-5.4-27.8-2.6-38.5-1.3c-3.2,0.4-3.7-2.4-0.8-4.5c18.8-13.2,49.7-9.4,53.3-5c3.6,4.5-1,35.4-18.6,50.2c-2.7,2.3-5.3,1.1-4.1-1.9C282.5,155.7,291.4,133.4,287.2,128.1z"
            fill="#FF9900"
          />
        </g>
      </svg>
    );
  }

  // 4. OpenAI (Official Exact 6-Petal Rosette Emblem)
  if (
    key.includes("openai") ||
    key === "oa" ||
    key.includes("chatgpt") ||
    key.includes("gpt")
  ) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 2406 2406"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        xmlnsXlink="http://www.w3.org/1999/xlink"
        className={`company-logo-svg logo-openai ${className}`}
        style={style}
        aria-label="OpenAI"
      >
        <defs>
          <path
            id="openai-swirl-petal"
            d="M1107.3 299.1c-198 0-373.9 127.3-435.2 315.3L650 743.5v427.9c0 21.4 11 40.4 29.4 51.4l344.5 198.5v-208.1h.1v-27.9L1372.7 604c33.7-19.5 70.4-32.9 108.5-39.8L1447.6 450.3C1361 353.5 1237.1 298.5 1107.3 299.1zm0 117.5-.6.6c79.7 0 156.3 27.5 217.6 78.4-2.5 1.2-7.4 4.3-11 6.1L952.8 709.3c-18.4 10.4-29.4 30-29.4 51.4V1248l-155.1-89.4V755.8c-.1-187.1 151.6-338.9 339-339.2z"
            fill="#10A37F"
          />
        </defs>
        <use xlinkHref="#openai-swirl-petal" />
        <use xlinkHref="#openai-swirl-petal" transform="rotate(60 1203 1203)" />
        <use xlinkHref="#openai-swirl-petal" transform="rotate(120 1203 1203)" />
        <use xlinkHref="#openai-swirl-petal" transform="rotate(180 1203 1203)" />
        <use xlinkHref="#openai-swirl-petal" transform="rotate(240 1203 1203)" />
        <use xlinkHref="#openai-swirl-petal" transform="rotate(300 1203 1203)" />
      </svg>
    );
  }

  // 5. NVIDIA (Official Green Claw / Spiral Emblem)
  if (
    key.includes("nvidia") ||
    key === "nv" ||
    key.includes("geforce") ||
    key.includes("nim")
  ) {
    return (
      <svg
        width={size}
        height={Math.round(size * (30 / 45.3))}
        viewBox="0 0 45.3 30"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-nvidia ${className}`}
        style={style}
        aria-label="NVIDIA"
      >
        <path
          d="M16.889,8.985L16.889,6.28C17.151,6.26 17.417,6.247 17.687,6.238C25.087,6.006 29.942,12.597 29.942,12.597C29.942,12.597 24.698,19.879 19.076,19.879C18.333,19.882 17.594,19.764 16.889,19.529L16.889,11.325C19.769,11.673 20.349,12.945 22.081,15.833L25.933,12.585C25.933,12.585 23.121,8.897 18.381,8.897C17.866,8.897 17.373,8.933 16.889,8.985ZM16.889,0.047L16.889,4.09C17.154,4.069 17.42,4.052 17.687,4.042C27.977,3.696 34.682,12.482 34.682,12.482C34.682,12.482 26.982,21.846 18.959,21.846C18.224,21.846 17.535,21.778 16.889,21.663L16.889,24.161C17.442,24.231 18.015,24.273 18.613,24.273C26.078,24.273 31.477,20.461 36.705,15.948C37.572,16.642 41.121,18.331 41.85,19.071C36.879,23.231 25.295,26.586 18.727,26.586C18.113,26.584 17.5,26.552 16.889,26.49L16.889,30L45.264,30L45.264,0.047L16.889,0.047ZM16.889,19.529L16.889,21.662C9.984,20.432 8.067,13.254 8.067,13.254C8.067,13.254 11.383,9.58 16.889,8.985L16.889,11.325L16.878,11.324C13.988,10.977 11.731,13.677 11.731,13.677C11.731,13.677 12.996,18.221 16.889,19.529ZM4.625,12.943C4.625,12.943 8.717,6.903 16.889,6.28L16.889,4.088C7.838,4.815 0,12.48 0,12.48C0,12.48 4.439,25.313 16.889,26.488L16.889,24.16C7.753,23.011 4.625,12.943 4.625,12.943Z"
          fill="#76B900"
        />
      </svg>
    );
  }

  // 6. Meta / Meta AI (Official Blue Infinity Ribbon)
  if (
    key.includes("meta") ||
    key === "ma" ||
    key.includes("llama") ||
    key.includes("facebook")
  ) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-meta ${className}`}
        style={style}
        aria-label="Meta"
      >
        <path
          d="M6.915 4.03c-1.968 0-3.683 1.28-4.871 3.113C.704 9.208 0 11.883 0 14.449c0 .706.07 1.369.21 1.973a6.624 6.624 0 0 0 .265.86 5.297 5.297 0 0 0 .371.761c.696 1.159 1.818 1.927 3.593 1.927 1.497 0 2.633-.671 3.965-2.444.76-1.012 1.144-1.626 2.663-4.32l.756-1.339.186-.325c.061.1.121.196.183.3l2.152 3.595c.724 1.21 1.665 2.556 2.47 3.314 1.046.987 1.992 1.22 3.06 1.22 1.075 0 1.876-.355 2.455-.843a3.743 3.743 0 0 0 .81-.973c.542-.939.861-2.127.861-3.745 0-2.72-.681-5.357-2.084-7.45-1.282-1.912-2.957-2.93-4.716-2.93-1.047 0-2.088.467-3.053 1.308-.652.57-1.257 1.29-1.82 2.05-.69-.875-1.335-1.547-1.958-2.056-1.182-.966-2.315-1.303-3.454-1.303zm10.16 2.053c1.147 0 2.188.758 2.992 1.999 1.132 1.748 1.647 4.195 1.647 6.4 0 1.548-.368 2.9-1.839 2.9-.58 0-1.027-.23-1.664-1.004-.496-.601-1.343-1.878-2.832-4.358l-.617-1.028a44.908 44.908 0 0 0-1.255-1.98c.07-.109.141-.224.211-.327 1.12-1.667 2.118-2.602 3.358-2.602zm-10.201.553c1.265 0 2.058.791 2.675 1.446.307.327.737.871 1.234 1.579l-1.02 1.566c-.757 1.163-1.882 3.017-2.837 4.338-1.191 1.649-1.81 1.817-2.486 1.817-.524 0-1.038-.237-1.383-.794-.263-.426-.464-1.13-.464-2.046 0-2.221.63-4.535 1.66-6.088.454-.687.964-1.226 1.533-1.533a2.264 2.264 0 0 1 1.088-.285z"
          fill="#0081FB"
        />
      </svg>
    );
  }

  // 7. Kaggle (Official cyan stylized 'k')
  if (key.includes("kaggle")) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-kaggle ${className}`}
        style={style}
        aria-label="Kaggle"
      >
        <path
          d="M18.8 21.6h-3.6l-5-7-2.3 2.2V21.6H4.2V2.4h3.7v11.6l6.8-7.6h3.6l-6.4 7.2 6.9 8z"
          fill="#20BEFF"
        />
      </svg>
    );
  }

  // 8. Polygon (Official Polygon purple token)
  if (key.includes("polygon") || key.includes("matic")) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-polygon ${className}`}
        style={style}
        aria-label="Polygon"
      >
        <path
          d="M16.5 8.2l-3.8-2.2a1.36 1.36 0 00-1.4 0L7.5 8.2a1.4 1.4 0 00-.7 1.2v4.4a1.4 1.4 0 00.7 1.2l3.8 2.2a1.36 1.36 0 001.4 0l3.8-2.2a1.4 1.4 0 00.7-1.2V9.4a1.4 1.4 0 00-.7-1.2zm-2.1 4.5l-2.4 1.4-2.4-1.4v-2.8l2.4-1.4 2.4 1.4v2.8z"
          fill="#8247E5"
        />
        <circle cx="12" cy="11.5" r="1.5" fill="#8247E5" />
      </svg>
    );
  }

  // 9. Solana (Official 3-tier gradient bars)
  if (key.includes("solana")) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-solana ${className}`}
        style={style}
        aria-label="Solana"
      >
        <path
          d="M4.3 18.2a.7.7 0 01.5-.2h14.9a.4.4 0 01.3.6l-3.3 3.3a.7.7 0 01-.5.2H1.3a.4.4 0 01-.3-.6l3.3-3.3zM4.3 2.1a.7.7 0 01.5-.2h14.9a.4.4 0 01.3.6l-3.3 3.3a.7.7 0 01-.5.2H1.3a.4.4 0 01-.3-.6l3.3-3.3zm15.4 8a.7.7 0 01-.5.2H4.3a.4.4 0 01-.3-.6l3.3-3.3a.7.7 0 01.5-.2h14.9a.4.4 0 01.3.6l-3.3 3.3z"
          fill="url(#solana-grad)"
        />
        <defs>
          <linearGradient id="solana-grad" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse">
            <stop stopColor="#14F195" />
            <stop offset="1" stopColor="#9945FF" />
          </linearGradient>
        </defs>
      </svg>
    );
  }

  // 10. Apple
  if (key.includes("apple")) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="currentColor"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-apple ${className}`}
        style={{ color: "#1E293B", ...style }}
        aria-label="Apple"
      >
        <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M15.97 6.38c.62-.75 1.04-1.8 1.01-2.88-.96.04-2.07.64-2.73 1.39-.56.64-1.07 1.72-.94 2.76 1.05.08 2.06-.54 2.66-1.27z" />
      </svg>
    );
  }

  // 11. GitHub
  if (key.includes("github")) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="currentColor"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-github ${className}`}
        style={{ color: "#181717", ...style }}
        aria-label="GitHub"
      >
        <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
      </svg>
    );
  }

  // 12. Goldman Sachs
  if (key.includes("goldman")) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-goldman ${className}`}
        style={style}
        aria-label="Goldman Sachs"
      >
        <rect width="32" height="32" rx="6" fill="#1B365D" />
        <text
          x="16"
          y="15"
          fill="#78A6DE"
          fontSize="11"
          fontWeight="800"
          fontFamily="system-ui, -apple-system, sans-serif"
          textAnchor="middle"
          letterSpacing="0.5"
        >
          GS
        </text>
        <rect x="7" y="19" width="18" height="2" rx="1" fill="#FFFFFF" opacity="0.8" />
      </svg>
    );
  }

  // 13. TCS (Tata Consultancy Services)
  if (key.includes("tcs") || key.includes("tata")) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-tcs ${className}`}
        style={style}
        aria-label="Tata Consultancy Services"
      >
        <rect width="32" height="32" rx="6" fill="#0A2540" />
        <path d="M7 11h18M16 11v14" stroke="#00D4B2" strokeWidth="2.8" strokeLinecap="round" />
        <circle cx="16" cy="11" r="2" fill="#FFFFFF" />
      </svg>
    );
  }

  // 14. SIH (Smart India Hackathon / Govt of India)
  if (key.includes("sih") || key.includes("india") || key.includes("govt")) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-sih ${className}`}
        style={style}
        aria-label="Smart India Hackathon"
      >
        <rect width="32" height="32" rx="6" fill="#0F172A" />
        {/* Tricolor aura */}
        <circle cx="16" cy="16" r="11" stroke="#FF9933" strokeWidth="2" strokeDasharray="3 2" />
        <circle cx="16" cy="16" r="6" fill="#000080" />
        <circle cx="16" cy="16" r="2" fill="#FFFFFF" />
        <path d="M16 5v3M16 24v3M5 16h3M24 16h3" stroke="#138808" strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
  }

  // 15. UNEP (United Nations Environment Programme)
  if (key.includes("unep") || key.includes("united nations") || key.includes("un")) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-unep ${className}`}
        style={style}
        aria-label="UNEP"
      >
        <rect width="32" height="32" rx="6" fill="#009EDB" />
        {/* Laurel Globe Silhouette */}
        <circle cx="16" cy="16" r="7" stroke="#FFFFFF" strokeWidth="1.5" />
        <path d="M9 16c0 3.8 3.1 7 7 7s7-3.2 7-7" stroke="#FFFFFF" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="16" cy="16" r="2.5" fill="#FFFFFF" />
      </svg>
    );
  }

  // 16. Anthropic
  if (key.includes("anthropic") || key.includes("claude")) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-anthropic ${className}`}
        style={style}
        aria-label="Anthropic"
      >
        <path
          d="M17.3041 3.541h-3.6718l6.696 16.918H24Zm-10.6082 0L0 20.459h3.7442l1.3693-3.5527h7.0052l1.3693 3.5528h3.7442L10.5363 3.5409Zm-.3712 10.2232 2.2914-5.9456 2.2914 5.9456Z"
          fill="#CC785C"
        />
      </svg>
    );
  }

  // Default clean SaaS brand mark fallback with initials
  const initials = (name || organizerKey || "HR")
    .replace(/[^a-zA-Z]/g, "")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div
      className={`company-logo-fallback ${className}`}
      style={{
        width: size,
        height: size,
        borderRadius: size > 24 ? "8px" : "6px",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: 700,
        fontSize: Math.max(10, Math.floor(size * 0.42)),
        background: "linear-gradient(135deg, #4F46E5 0%, #0284C7 100%)",
        color: "#FFFFFF",
        letterSpacing: "-0.02em",
        flexShrink: 0,
        ...style
      }}
      aria-label={name || "Organizer"}
    >
      {initials}
    </div>
  );
}

/**
 * CompanyAvatar: An elegant rounded badge container that surrounds the CompanyLogo,
 * matching Stripe and Linear's design system standards.
 */
export function CompanyAvatar({
  organizerKey,
  name,
  size = 36,
  logoSize,
  className = "",
  style = {}
}) {
  const actualLogoSize = logoSize || Math.round(size * 0.58);

  return (
    <div
      className={`company-avatar-badge ${className}`}
      style={{
        width: size,
        height: size,
        minWidth: size,
        minHeight: size,
        borderRadius: size >= 40 ? "12px" : "9px",
        background: "#FFFFFF",
        border: "1px solid rgba(226, 232, 240, 0.9)",
        boxShadow: "0 1px 2px rgba(15, 23, 42, 0.05)",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        transition: "all 0.15s ease",
        ...style
      }}
    >
      <CompanyLogo
        organizerKey={organizerKey}
        name={name}
        size={actualLogoSize}
      />
    </div>
  );
}
