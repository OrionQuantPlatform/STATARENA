"use client";
import React, { useId } from "react";
import Link from "next/link";
import {
  ArrowDown,
  ArrowUpRight,
  CircleHelp,
  LockKeyhole,
  Sparkles,
} from "lucide-react";
import Layout from "../components/Layout.jsx";
import Icon from "../components/Icon.jsx";
import { Media, Segments } from "../components/UI.jsx";
import { useFootball } from "../hooks/FootballContext.jsx";
import { number } from "../services/format.js";

// The model has not produced a ranking yet. Empty places are intentional,
// not a loading state. Keep this separate from the provider's player ratings.
// Future entries: { rank, name, imageUrl, team, teamImageUrl, position, score }.
const ranking = null;
const PODIUM = [
  { rank: 2, medal: "silver", label: "Deuxième place" },
  { rank: 1, medal: "gold", label: "Première place" },
  { rank: 3, medal: "bronze", label: "Troisième place" },
];
const STEPS = [
  {
    icon: "ball",
    title: "Chaque match compte",
    text: "La performance est comparée à celle attendue d’un joueur au même poste, dans le même match.",
  },
  {
    icon: "pitch",
    title: "Toutes les facettes du jeu",
    text: "Finition, création, progression, défense et conservation : des blocs pondérés selon le poste.",
  },
  {
    icon: "calendar",
    title: "La saison fait la différence",
    text: "Contribution cumulée et niveau par 90 minutes, avec une correction pour les temps de jeu courts.",
  },
  {
    icon: "trophy",
    title: "Une place parmi les meilleurs",
    text: "Les joueurs sont situés en centiles de leur poste, avant de réunir les 30 meilleurs.",
  },
];

/** A decorative, code-native award: no player imagery or synthetic statistics. */
function OrionAward() {
  const id = useId().replace(/:/g, "");
  return (
    <svg
      className="orion-award-art"
      viewBox="0 0 420 340"
      fill="none"
      aria-hidden="true"
    >
      <defs>
        <radialGradient id={`${id}-halo`}>
          <stop stopColor="#A9C77D" stopOpacity=".16" />
          <stop offset="1" stopColor="#A9C77D" stopOpacity="0" />
        </radialGradient>
        <linearGradient
          id={`${id}-metal`}
          x1="132"
          y1="80"
          x2="270"
          y2="211"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#F0EFBB" />
          <stop offset=".28" stopColor="#BEC687" />
          <stop offset=".6" stopColor="#637552" />
          <stop offset="1" stopColor="#27382D" />
        </linearGradient>
        <linearGradient
          id={`${id}-edge`}
          x1="172"
          y1="223"
          x2="246"
          y2="288"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#D6D9AB" />
          <stop offset=".55" stopColor="#859169" />
          <stop offset="1" stopColor="#344432" />
        </linearGradient>
      </defs>
      <circle cx="216" cy="163" r="155" fill={`url(#${id}-halo)`} />
      <g className="award-orbits" stroke="currentColor" strokeWidth=".7">
        <ellipse
          cx="216"
          cy="163"
          rx="169"
          ry="108"
          transform="rotate(-23 216 163)"
        />
        <ellipse
          cx="216"
          cy="163"
          rx="141"
          ry="139"
          transform="rotate(-23 216 163)"
          strokeDasharray="2 7"
        />
        <path d="M39 163h30m294 0h28M216 9v24m0 263v30" />
      </g>
      <g stroke="#D0F377">
        <path d="M350 78v12m-6-6h12" />
        <path d="M73 217v8m-4-4h8" opacity=".6" />
      </g>
      <circle cx="82" cy="102" r="3" fill="#D0F377" />
      <circle cx="359" cy="210" r="2" fill="#D0F377" opacity=".65" />
      <path
        d="m190 209-15 48h82l-16-48"
        fill={`url(#${id}-edge)`}
        stroke="#ABB685"
        strokeOpacity=".6"
      />
      <path d="m203 212-7 45h27l-2-45" fill="#E9E8B6" fillOpacity=".13" />
      <path d="m175 257-14 12v9h110v-9l-14-12Z" fill={`url(#${id}-edge)`} />
      <path d="M161 269h110M177 258h78" stroke="#D0D5A3" strokeOpacity=".6" />
      <path
        d="m216 62 45 15 29 38v47l-29 38-45 15-45-15-29-38v-47l29-38Z"
        fill={`url(#${id}-metal)`}
        stroke="#DEE1B1"
        strokeOpacity=".75"
      />
      <path
        d="m216 105 33 24-13 39h-40l-13-39Z"
        fill="#233829"
        stroke="#CCD49E"
        strokeOpacity=".7"
      />
      <path
        d="m216 62 0 43m-45-28 12 52-41-14m0 47 54 6-25 32m45 15 20-47 25 32m29-38-41-33 12-52"
        stroke="#E3E5B7"
        strokeOpacity=".6"
        strokeWidth="1.3"
      />
      <path
        d="m171 77 45 28 45-28m-90 123 25-32 20 47m74-100-41 14 41 33m-148 0 41-33-41-14m119 85-25-32"
        stroke="#334833"
        strokeOpacity=".65"
      />
      <path
        d="m216 62-45 15-29 38 41 14 33-24Z"
        fill="#F5F1C7"
        fillOpacity=".14"
      />
      <path d="M183 277h66" stroke="#CFD2A4" strokeOpacity=".7" />
      <ellipse
        cx="216"
        cy="294"
        rx="78"
        ry="5"
        fill="currentColor"
        opacity=".08"
      />
    </svg>
  );
}

function PodiumPlace({ rank, medal, label, entry }) {
  return (
    <li
      className={`orion-podium-place orion-podium-${medal}`}
      value={rank}
      aria-label={
        entry
          ? `Rang ${rank} : ${entry.name}, ${entry.team}`
          : `Rang ${rank}, à révéler`
      }
    >
      <div className="orion-podium-top">
        <span>{label}</span>
        {rank === 1 && (
          <span className="orion-winner-tag">
            <Sparkles size={12} /> Distinction Orion
          </span>
        )}
      </div>
      <span className="orion-podium-numeral" aria-hidden="true">
        {String(rank).padStart(2, "0")}
      </span>
      <div className="orion-podium-person">
        {entry ? (
          <Media
            name={entry.name}
            url={entry.imageUrl}
            className="orion-podium-avatar"
          />
        ) : (
          <span className="orion-podium-emblem" aria-hidden="true">
            <span />
            <LockKeyhole size={24} strokeWidth={1.2} />
          </span>
        )}
        <div className="orion-podium-identity">
          <h3>{entry?.name || "À révéler"}</h3>
          <p>
            {entry
              ? `${entry.team} · ${entry.position}`
              : "Une saison pour se distinguer."}
          </p>
        </div>
      </div>
      <div className="orion-podium-score">
        <span>
          Score Orion <CircleHelp size={12} aria-hidden="true" />
        </span>
        <strong>{entry ? number(entry.score, 1) : "—"}</strong>
      </div>
    </li>
  );
}

function RankTable({ from, to }) {
  return (
    <div className="orion-rank-table-wrap">
      <table className="orion-rank-table">
        <caption className="sr-only">
          Classement, places {from} à {to}
        </caption>
        <thead>
          <tr>
            <th scope="col">Rang</th>
            <th scope="col">Joueur / Club</th>
            <th scope="col">Poste</th>
            <th scope="col">Score</th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: to - from + 1 }, (_, i) => from + i).map(
            (rank) => {
              const entry = ranking?.find((e) => e.rank === rank);
              return (
                <tr key={rank}>
                  <th scope="row">
                    <span className="orion-rank-number">
                      {String(rank).padStart(2, "0")}
                    </span>
                  </th>
                  <td>
                    <div className="orion-rank-person">
                      {entry ? (
                        <Media
                          name={entry.name}
                          url={entry.imageUrl}
                          className="orion-rank-avatar"
                        />
                      ) : (
                        <span
                          className="orion-rank-avatar orion-rank-unrevealed"
                          aria-hidden="true"
                        >
                          <Icon name="players" />
                        </span>
                      )}
                      <div>
                        <strong>{entry?.name || "À révéler"}</strong>
                        {entry?.team && <span>{entry.team}</span>}
                      </div>
                    </div>
                  </td>
                  <td className="orion-rank-position">
                    {entry?.position || "—"}
                  </td>
                  <td className="orion-rank-value">
                    {entry ? number(entry.score, 1) : "—"}
                  </td>
                </tr>
              );
            },
          )}
        </tbody>
      </table>
    </div>
  );
}

export default function PlayerRankingPage() {
  const f = useFootball(),
    seasons = f.manifest?.seasons || [];
  return (
    <Layout
      path="/classement-joueurs/"
      hideHeading
      showSeasonContext={false}
      className="orion-ranking-page"
    >
      <div className="orion-page-topline">
        <div className="orion-breadcrumb">
          <span>Football</span>
          <span aria-hidden="true">/</span>
          <strong>Classement Ballon d’Or</strong>
        </div>
        <a className="orion-method-shortcut" href="#orion-method">
          Notre approche <ArrowUpRight size={15} />
        </a>
      </div>
      <section
        className="orion-ranking-hero"
        aria-labelledby="orion-ranking-title"
      >
        <div className="orion-hero-copy">
          <div className="orion-eyebrow">
            <span className="orion-small-star" aria-hidden="true">
              ✳
            </span>{" "}
            La performance, sous un autre angle
          </div>
          <h1 id="orion-ranking-title">
            Classement
            <br />
            <span>Ballon d’Or.</span>
          </h1>
          <p>
            Le talent se voit. La performance se mesure.
            <br className="orion-desktop-break" /> Une autre lecture du
            football, portée par la donnée.
          </p>
          <a className="orion-hero-link" href="#orion-podium">
            Découvrir la sélection <ArrowDown size={15} />
          </a>
        </div>
        <div className="orion-hero-art">
          <OrionAward />
          <span className="orion-art-caption">
            ORION TECH SPORT <span>—</span> FOOTBALL INTELLIGENCE
          </span>
        </div>
      </section>
      <div className="orion-ranking-toolbar">
        <div className="orion-ranking-status">
          <span className="orion-status-dot" aria-hidden="true" />
          <div>
            <strong>
              {ranking ? "Le classement Orion" : "Classement en préparation"}
            </strong>
            <span>
              {ranking
                ? "30 places · Tous les postes"
                : "Les places sont prêtes. Les performances feront la différence."}
            </span>
          </div>
        </div>
        {seasons.length > 1 && (
          <div className="orion-season-control">
            <span>Saison</span>
            <Segments
              label="Saison du classement"
              value={f.season}
              items={seasons.map((s) => [s.id, s.id])}
              onChange={f.changeSeason}
            />
          </div>
        )}
      </div>
      <section
        id="orion-podium"
        className="orion-podium-section"
        aria-labelledby="orion-podium-title"
      >
        <div className="orion-section-heading">
          <h2 id="orion-podium-title">
            <span>01</span> Le podium
          </h2>
          <p>Trois places. Une distinction.</p>
        </div>
        <ol className="orion-podium" aria-label="Podium" role="list">
          {PODIUM.map((place) => (
            <PodiumPlace
              key={place.rank}
              {...place}
              entry={ranking?.find((e) => e.rank === place.rank)}
            />
          ))}
        </ol>
      </section>
      <section
        className="orion-selection"
        aria-labelledby="orion-selection-title"
      >
        <div className="orion-section-heading">
          <h2 id="orion-selection-title">
            <span>02</span> Le classement complet
          </h2>
          <span className="orion-count-tag">30 places</span>
        </div>
        <div className="orion-rank-board">
          <RankTable from={4} to={17} />
          <RankTable from={18} to={30} />
        </div>
        {!ranking && (
          <p className="orion-ranking-note">
            <CircleHelp size={14} /> Les scores et les joueurs seront affichés
            après le calcul du modèle pour la saison sélectionnée.
          </p>
        )}
      </section>
      <section
        id="orion-method"
        className="orion-ranking-method"
        aria-labelledby="orion-method-title"
      >
        <div className="orion-method-heading">
          <div>
            <div className="orion-eyebrow">L’approche Orion</div>
            <h2 id="orion-method-title">
              Du jeu. Des données.
              <br />
              Une perspective.
            </h2>
          </div>
          <div>
            <p>
              Un cadre commun, attentif à ce qui rend chaque poste différent.
            </p>
            <Link className="orion-text-link" href={f.href("/methode/")}>
              Comprendre la méthode <ArrowUpRight size={16} />
            </Link>
          </div>
        </div>
        <ol className="orion-method-steps" role="list">
          {STEPS.map((step, index) => (
            <li key={step.title}>
              <div className="orion-step-top">
                <span className="orion-step-icon">
                  <Icon name={step.icon} />
                </span>
                <span>{String(index + 1).padStart(2, "0")}</span>
              </div>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </li>
          ))}
        </ol>
      </section>
    </Layout>
  );
}
