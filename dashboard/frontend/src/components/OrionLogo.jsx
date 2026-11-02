import React from "react";

export default function OrionLogo({ compact = false, className = "" }) {
  return (
    <span
      className={`orion-logo${compact ? " orion-logo-compact" : ""} ${className}`}
    >
      <svg
        className="orion-logo-mark"
        width="44"
        height="44"
        viewBox="0 0 48 48"
        fill="none"
        aria-hidden="true"
      >
        <circle cx="24" cy="24" r="14" stroke="currentColor" strokeWidth="2" />
        <ellipse
          cx="24"
          cy="24"
          rx="22"
          ry="9.5"
          transform="rotate(-35 24 24)"
          stroke="currentColor"
          strokeWidth="1.2"
          opacity=".6"
        />
        <circle cx="10.5" cy="31.5" r="2.6" fill="currentColor" />
        <circle cx="24" cy="24" r="2.3" fill="currentColor" />
        <circle cx="37.5" cy="16.5" r="2.6" fill="currentColor" />
      </svg>
      <span className="orion-logo-type">
        <span className="orion-logo-name">ORION</span>
        <span className="orion-logo-descriptor">TECH SPORT</span>
      </span>
    </span>
  );
}
