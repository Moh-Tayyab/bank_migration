"use client";

import { useState, useEffect } from "react";
import Icon from "./Icon";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard" },
  { id: "migrate", label: "Migration", icon: "migration" },
  { id: "audit", label: "Audit Trail", icon: "audit" },
  { id: "banks", label: "Banks", icon: "banks" },
];

export default function Sidebar({
  activeSection,
  onNavigate,
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
}: {
  activeSection: string;
  onNavigate: (id: string) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}) {
  const [apiStatus, setApiStatus] = useState<"online" | "offline" | "checking">("checking");

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch("/api/health", { signal: AbortSignal.timeout(3000) });
        setApiStatus(res.ok ? "online" : "offline");
      } catch {
        setApiStatus("offline");
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-30 lg:hidden animate-fade-in"
          onClick={onCloseMobile}
        />
      )}

      <aside
        className={`sidebar ${collapsed ? "collapsed" : ""} ${mobileOpen ? "mobile-open" : ""}`}
        id="sidebar-nav"
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 h-16 border-b border-[var(--sidebar-border)] shrink-0">
          <div
            className="w-9 h-9 rounded-xl gradient-bg flex items-center justify-center text-white font-bold text-sm shadow-md shrink-0 animate-gradient-shift"
            style={{ backgroundSize: "200% 200%" }}
          >
            UW
          </div>
          {!collapsed && (
            <div className="overflow-hidden animate-fade-in">
              <h1 className="text-sm font-bold leading-tight" style={{ color: "var(--foreground)" }}>
                UN Wallet
              </h1>
              <p className="text-[10px] font-medium leading-tight tracking-widest uppercase" style={{ color: "var(--muted-foreground)" }}>
                Migration
              </p>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {!collapsed && (
            <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
              Platform
            </p>
          )}
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => { onNavigate(item.id); onCloseMobile(); }}
              className={`sidebar-link w-full ${activeSection === item.id ? "active" : ""}`}
              title={collapsed ? item.label : undefined}
              id={`nav-${item.id}`}
            >
              <Icon name={item.icon} className="w-[18px] h-[18px] shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </button>
          ))}

          {!collapsed && (
            <>
              <div className="my-4 mx-3 border-t" style={{ borderColor: "var(--sidebar-border)" }} />
              <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
                System
              </p>
            </>
          )}
          <button
            onClick={() => { onNavigate("settings"); onCloseMobile(); }}
            className={`sidebar-link w-full ${activeSection === "settings" ? "active" : ""}`}
            title={collapsed ? "Settings" : undefined}
            id="nav-settings"
          >
            <Icon name="settings" className="w-[18px] h-[18px] shrink-0" />
            {!collapsed && <span>Settings</span>}
          </button>
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t shrink-0" style={{ borderColor: "var(--sidebar-border)" }}>
          {!collapsed ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full shrink-0 ${
                    apiStatus === "online"
                      ? "bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.4)]"
                      : apiStatus === "offline"
                        ? "bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.4)]"
                        : "bg-amber-500 animate-pulse"
                  }`}
                />
                <span className="text-[11px] font-medium" style={{ color: "var(--muted-foreground)" }}>
                  API {apiStatus === "online" ? "Connected" : apiStatus === "offline" ? "Offline" : "Checking..."}
                </span>
              </div>
              <button
                onClick={onToggleCollapse}
                className="p-1 rounded-md hover:bg-[var(--sidebar-hover)] transition-colors hidden lg:block"
                style={{ color: "var(--muted-foreground)" }}
                aria-label="Collapse sidebar"
              >
                <Icon name="chevron-down" className="w-3.5 h-3.5 -rotate-90" />
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${
                  apiStatus === "online" ? "bg-emerald-500" : apiStatus === "offline" ? "bg-red-500" : "bg-amber-500 animate-pulse"
                }`}
              />
              <button
                onClick={onToggleCollapse}
                className="p-1 rounded-md hover:bg-[var(--sidebar-hover)] transition-colors hidden lg:block"
                style={{ color: "var(--muted-foreground)" }}
                aria-label="Expand sidebar"
              >
                <Icon name="chevron-down" className="w-3.5 h-3.5 rotate-90" />
              </button>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
