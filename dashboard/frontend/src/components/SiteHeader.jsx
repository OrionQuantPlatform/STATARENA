"use client";

import React, { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import ThemeToggle from "./ThemeToggle.jsx";
import OrionLogo from "./OrionLogo.jsx";
import Icon from "./Icon.jsx";
import { pages } from "../../../shared/pages.js";

const icons = {
  "/": "pitch",
  "/competitions/": "globe",
  "/clubs/": "shield",
  "/joueurs/": "players",
  "/classement-joueurs/": "trophy",
  "/matchs/": "calendar",
};
const navigation = pages.filter((page) => page.navigation !== false);
const normalizedPath = (value) => value?.replace(/\/$/, "") || "/";

export default function SiteHeader({ path, href }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuId = useId();
  const headerRef = useRef(null);
  const navigationRef = useRef(null);
  const toggleRef = useRef(null);

  useEffect(() => {
    setMenuOpen(false);
  }, [path]);

  useEffect(() => {
    if (!menuOpen) return;
    const frame = requestAnimationFrame(() => {
      navigationRef.current?.querySelector("a")?.focus();
    });
    const onKeyDown = (event) => {
      if (event.key !== "Escape") return;
      setMenuOpen(false);
      toggleRef.current?.focus();
    };
    const onPointerDown = (event) => {
      if (!headerRef.current?.contains(event.target)) setMenuOpen(false);
    };
    const onResize = () => {
      if (window.matchMedia("(min-width: 1101px)").matches) setMenuOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("resize", onResize);
    };
  }, [menuOpen]);

  const closeMenu = () => setMenuOpen(false);

  return (
    <header
      ref={headerRef}
      className={`orion-header${menuOpen ? " is-menu-open" : ""}`}
    >
      <div className="orion-brand-row">
        <Link
          className="orion-brand"
          aria-label="Orion Tech Sport, vue d’ensemble"
          href={href("/")}
          onClick={closeMenu}
        >
          <OrionLogo />
        </Link>
        <button
          ref={toggleRef}
          className="orion-menu-toggle"
          type="button"
          aria-expanded={menuOpen}
          aria-controls={menuId}
          aria-label={
            menuOpen ? "Fermer la navigation" : "Ouvrir la navigation"
          }
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? (
            <X size={21} strokeWidth={1.7} aria-hidden="true" />
          ) : (
            <Menu size={21} strokeWidth={1.7} aria-hidden="true" />
          )}
        </button>
      </div>
      <div id={menuId} className="orion-rail-content">
        <nav
          className="orion-navigation"
          aria-label="Navigation principale"
          ref={navigationRef}
        >
          <p className="orion-nav-caption">Explorer</p>
          {navigation.map(({ path: url, title }) => (
            <Link
              key={url}
              className="orion-nav-link"
              aria-current={
                normalizedPath(path) === normalizedPath(url)
                  ? "page"
                  : undefined
              }
              href={href(url)}
              onClick={closeMenu}
            >
              <Icon name={icons[url] || icons[`${url}/`] || "ball"} />
              <span>{title}</span>
              <span className="orion-nav-current" aria-hidden="true" />
            </Link>
          ))}
        </nav>
        <div className="orion-rail-bottom">
          <Link
            className="orion-nav-link orion-method-link"
            href={href("/methode/")}
            onClick={closeMenu}
            aria-current={
              normalizedPath(path) === "/methode" ? "page" : undefined
            }
          >
            <Icon name="info" />
            <span>Données & méthode</span>
            <Icon name="external" className="orion-method-arrow" />
          </Link>
          <div className="orion-perspective">
            <span className="orion-perspective-star" aria-hidden="true">
              ✳
            </span>
            <p>
              Le football,
              <br />
              sous un autre angle.
            </p>
          </div>
          <div className="orion-appearance">
            <span>Apparence</span>
            <ThemeToggle />
          </div>
        </div>
      </div>
    </header>
  );
}
