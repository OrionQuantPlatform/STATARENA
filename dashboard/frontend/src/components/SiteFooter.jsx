import Link from "next/link";
import Icon from "./Icon.jsx";
import OrionLogo from "./OrionLogo.jsx";

const repository = "https://github.com/OrionQuantPlatform/STATARENA";
const groups = [
  {
    title: "Explorer",
    links: [
      ["Vue d’ensemble", "/"],
      ["Compétitions", "/competitions/"],
      ["Clubs", "/clubs/"],
      ["Matchs", "/matchs/"],
    ],
  },
  {
    title: "Joueurs",
    links: [
      ["Performances", "/joueurs/"],
      ["Classement Ballon d’Or", "/classement-joueurs/"],
    ],
  },
  {
    title: "Méthode",
    links: [
      ["Données & méthode", "/methode/"],
      [
        "Modèle mathématique",
        `${repository}/blob/main/docs/METHODE_CLASSEMENT_BALLON_D_OR.md`,
      ],
      ["Base JSON", `${repository}/blob/main/docs/JSON_DATABASE.md`],
    ],
  },
  {
    title: "Projet",
    links: [
      ["GitHub", repository],
      ["Documentation", `${repository}/tree/main/docs`],
      ["Signaler un problème", `${repository}/issues`],
    ],
  },
];

export default function SiteFooter({ href, path }) {
  return (
    <footer className="site-footer orion-footer" aria-label="Pied de page">
      <div className="orion-footer-inner">
        <div className="orion-footer-heading">
          <Link
            className="orion-footer-home"
            href={href("/")}
            aria-label="Orion Tech Sport, vue d’ensemble"
          >
            <OrionLogo compact />
          </Link>
          <p>Un autre regard sur le jeu.</p>
        </div>
        <div className="orion-footer-groups">
          {groups.map((group) => (
            <nav
              className="orion-footer-group"
              aria-label={group.title}
              key={group.title}
            >
              <h2>{group.title}</h2>
              <ul>
                {group.links.map(([label, destination]) => {
                  const external = destination.startsWith("https:");
                  return (
                    <li key={destination}>
                      <Link
                        href={external ? destination : href(destination)}
                        aria-current={
                          !external &&
                          path?.replace(/\/$/, "") ===
                            destination.replace(/\/$/, "")
                            ? "page"
                            : undefined
                        }
                        {...(external
                          ? { target: "_blank", rel: "noreferrer" }
                          : {})}
                      >
                        {label}
                        {external && <Icon name="external" />}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </nav>
          ))}
        </div>
        <div className="orion-footer-bottom">
          <span>© {new Date().getFullYear()} Orion Tech Sport</span>
          <span>Football · Data · Analyse</span>
        </div>
      </div>
    </footer>
  );
}
