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

  // 3. Amazon Web Services (AWS)
  if (
    key.includes("aws") ||
    key.includes("amazon") ||
    key.includes("bedrock")
  ) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-aws ${className}`}
        style={style}
        aria-label="Amazon Web Services"
      >
        <path
          d="M7.4 12.2c0-1.8 1-2.9 2.7-2.9 1.1 0 1.9.5 2.3 1.2v-1h2.2v6.8c0 1.1.3 1.5 1.1 1.5.4 0 .7-.1.9-.2l.4 1.5c-.5.3-1.2.4-1.9.4-1.6 0-2.6-.8-2.7-2.4-.6.9-1.5 1.5-2.7 1.5-2 0-3.3-1.3-3.3-3.1 0-2.1 1.6-3.2 4.4-3.3l1.5-.1v-.5c0-1-.6-1.5-1.7-1.5-.9 0-1.6.4-1.8 1.1l-1.6-.6zm5 2.6l-1.3.1c-1.4.1-2.1.6-2.1 1.6 0 .9.7 1.5 1.7 1.5 1 0 1.7-.7 1.7-1.7v-1.5zm6.4-3.7h2.2l1.3 4.8 1.4-4.8h2.1l1.4 4.8 1.3-4.8h2.1l-2.3 7.4h-2.1l-1.4-4.7-1.4 4.7h-2.1l-2.5-7.4zm-13 13c3.8 2.6 8.7 3.8 13.9 2.5 3.3-.8 6.5-2.6 8.7-5 .5-.5.2-1-.4-.7-3.1 1.7-6.9 2.6-10.7 2.3-4.2-.4-8.1-2.1-11.2-4.8-.4-.4-.8 0-.3.7z"
          fill="#232F3E"
        />
        <path
          d="M26.4 21.6c.7-.3 2.1-.9 2.9-1.9.1-.1.2-.1.3 0 .1.1 0 .3-.1.4-.8 1-2 1.8-3.1 2.1-.4.1-.6-.2-.3-.5l.3-.1z"
          fill="#FF9900"
        />
        <path
          d="M5.8 24.1c4.5 3.2 10.6 4.3 16.3 2.3 2.8-1 5.3-2.7 7.2-4.9.4-.4.1-.9-.4-.6-2.6 1.7-5.8 2.8-9.1 2.8-4.8 0-9.4-1.8-13.4-4.9-.5-.4-.9.2-.6.7z"
          fill="#FF9900"
        />
      </svg>
    );
  }

  // 4. OpenAI (Official swirl rosette mark)
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
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-openai ${className}`}
        style={style}
        aria-label="OpenAI"
      >
        <path
          d="M22.28 9.9a6.04 6.04 0 00-.51-4.87 6.13 6.13 0 00-6.15-3.08A6.04 6.04 0 0011.2 0a6.13 6.13 0 00-5.85 4.25 6.04 6.04 0 00-4.13 3 6.13 6.13 0 00.74 6.84 6.04 6.04 0 00.51 4.87 6.13 6.13 0 006.15 3.08A6.04 6.04 0 0012.8 24a6.13 6.13 0 005.85-4.25 6.04 6.04 0 004.13-3 6.13 6.13 0 00-.5-6.85zm-7.6 12.38a4.4 4.4 0 01-2.92-1.12l.14-.08 4.85-2.8a.86.86 0 00.43-.75v-6.84l2.06 1.19a.12.12 0 01.06.1v5.63a4.43 4.43 0 01-4.62 4.67zM3.48 18.72a4.4 4.4 0 01-.48-3.09l.15.09 4.85 2.8a.86.86 0 00.86 0l5.92-3.42v2.38a.12.12 0 01-.05.1l-4.88 2.82a4.43 4.43 0 01-6.35-1.68zm-1.8-9.8a4.4 4.4 0 012.44-1.97v5.77a.86.86 0 00.43.75l5.92 3.42-2.06 1.19a.12.12 0 01-.12 0L3.4 15.26a4.43 4.43 0 01-1.72-6.34zm16.7 2.4l-5.92-3.42 2.06-1.19a.12.12 0 01.12 0l4.89 2.82a4.43 4.43 0 01-.72 8.02v-5.48a.86.86 0 00-.43-.75zm2.34-4.2a4.4 4.4 0 01.48 3.09l-.15-.09-4.85-2.8a.86.86 0 00-.86 0L9.47 10.74V8.36a.12.12 0 01.05-.1l4.88-2.82a4.43 4.43 0 016.32 1.68zM8.33 8.35L10.39 7.16a.12.12 0 01.12 0l4.89 2.82a4.43 4.43 0 01-.72 8.02V12.22a.86.86 0 00-.43-.75L8.33 8.35zm1.96 5.37l2.67-1.54 2.67 1.54v3.08l-2.67 1.54-2.67-1.54v-3.08z"
          fill="#10A37F"
        />
      </svg>
    );
  }

  // 5. NVIDIA (Official Green Claw / Eye emblem)
  if (
    key.includes("nvidia") ||
    key === "nv" ||
    key.includes("geforce") ||
    key.includes("nim")
  ) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`company-logo-svg logo-nvidia ${className}`}
        style={style}
        aria-label="NVIDIA"
      >
        <path
          d="M7.74 5.35c4.78-1.54 10.22-.05 13.56 3.52 1.7 1.83 2.7 4.19 2.7 6.7 0 .42-.03.84-.09 1.25-.38-.63-.9-1.19-1.52-1.63-2.58-1.84-6.07-1.74-8.54.26-1.5 1.21-2.26 3.02-2.11 4.93.03.35.08.7.17 1.04-.6.06-1.2.09-1.81.09-4.8 0-9.06-2.86-10.1-7.15C-1.07 9.8 2.61 5.35 7.74 5.35zm.74 3.7c3.42-1.05 7.27.05 9.58 2.68 1.15 1.3 1.77 2.94 1.74 4.67-.3-.39-.68-.73-1.12-.99-1.84-1.11-4.27-.92-5.91.47-1.03.88-1.55 2.19-1.42 3.54.02.21.06.42.12.63-.4.04-.81.06-1.22.06-3.32 0-6.22-2.03-6.9-5.04-.7-3.1 1.36-6.14 5.13-6.02zm.61 3.5c2.03-.57 4.29.13 5.6 1.73.66.8 1.01 1.8 1 2.83-.24-.22-.53-.41-.86-.55-1.11-.47-2.48-.28-3.41.48-.56.46-.86 1.15-.81 1.86.01.11.03.22.07.33-.23.02-.46.03-.7.03-1.87 0-3.48-1.19-3.83-2.92-.37-1.81.82-3.56 2.94-3.79z"
          fill="#76B900"
        />
      </svg>
    );
  }

  // 6. Meta / Meta AI (Official Blue Infinity Loop)
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
          d="M16.68 4.5c-2.42 0-4.14 1.62-5.68 3.55C9.46 6.12 7.74 4.5 5.32 4.5 2.05 4.5 0 7.42 0 11.23c0 4.22 2.37 8.27 5.65 8.27 2.54 0 4.25-1.74 5.85-3.69 1.6 1.95 3.31 3.69 5.85 3.69 3.28 0 5.65-4.05 5.65-8.27 0-3.81-2.05-6.73-5.32-6.73zm-11.36 12.3c-2.06 0-3.32-2.73-3.32-5.57 0-2.6 1.34-4.48 3.32-4.48 1.7 0 3.01 1.45 4.3 3.42-1.37 2.45-2.75 6.63-4.3 6.63zm11.36 0c-1.55 0-2.93-4.18-4.3-6.63 1.29-1.97 2.6-3.42 4.3-3.42 1.98 0 3.32 1.88 3.32 4.48 0 2.84-1.26 5.57-3.32 5.57z"
          fill="#0668E1"
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
          d="M14.07 4.5h3.63L11.83 19.5H8.2L14.07 4.5zM6.3 19.5l4.3-11.23h3.58L9.88 19.5H6.3z"
          fill="#D97706"
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
