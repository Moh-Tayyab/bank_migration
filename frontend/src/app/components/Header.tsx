"use client";

import { useState, useEffect } from "react";
import Icon from "./Icon";

export default function Header({
  title,
  subtitle,
  collapsed,
  onMenuToggle,
}: {
  title: string;
  subtitle?: string;
  collapsed: boolean;
  onMenuToggle: () => void;
}) {
  const [dark, setDark] = useState(false);
  const [time, setTime] = useState("");

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
    const updateTime = () => {
      setTime(
        new Date().toLocaleTimeString(undefined, {
          hour: "2-digit",
          minute: "2-digit",
        })
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 30000);
    return () => clearInterval(interval);
  }, []);

  const toggleTheme = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  return (
    <header
      className="glass sticky top-0 z-30 h-16 flex items-center justify-between px-4 lg:px-6"
      id="main-header"
      style={{ borderBottom: "1px solid var(--border)" }}
    >
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="p-2 rounded-lg lg:hidden transition-colors hover:bg-[var(--accent)]"
          style={{ color: "var(--muted-foreground)" }}
          aria-label="Toggle menu"
          id="mobile-menu-toggle"
        >
          <Icon name="menu" className="w-5 h-5" />
        </button>

        <div>
          <h2 className="text-base font-semibold" style={{ color: "var(--foreground)" }}>
            {title}
          </h2>
          {subtitle && (
            <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
              {subtitle}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Time */}
        <div
          className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium"
          style={{ color: "var(--muted-foreground)", background: "var(--secondary)" }}
        >
          <Icon name="clock" className="w-3.5 h-3.5" />
          {time}
        </div>

        {/* API Docs */}
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all hover:bg-[var(--accent)]"
          style={{ color: "var(--muted-foreground)", border: "1px solid var(--border)" }}
          id="api-docs-link"
        >
          <Icon name="external" className="w-3.5 h-3.5" />
          API Docs
        </a>

        {/* Divider */}
        <div className="w-px h-5" style={{ background: "var(--border)" }} />

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg transition-all hover:bg-[var(--accent)]"
          style={{ color: "var(--muted-foreground)" }}
          aria-label="Toggle theme"
          id="theme-toggle"
        >
          <div className={`transition-transform duration-300 ${dark ? "rotate-180" : "rotate-0"}`}>
            {dark ? <Icon name="sun" className="w-4 h-4" /> : <Icon name="moon" className="w-4 h-4" />}
          </div>
        </button>
      </div>
    </header>
  );
}
