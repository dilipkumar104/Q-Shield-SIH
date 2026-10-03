"use client";

import { useState } from "react";
import "./globals.css";

const navItems = [
  "Command Center",
  "Simulation Lab",
  "Attack Lab",
  "Investigations",
  "Evidence Forensics",
  "Experiment Comparison",
  "Reproducibility Metadata",
  "Presentation Mode",
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [activeNav, setActiveNav] = useState("Simulation Lab");

  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Space+Mono:ital,wght@0,400;0,700;1,400;1,700&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
          rel="stylesheet"
        />
      </head>
      <body className="bg-surface text-on-surface font-body antialiased no-scrollbar overflow-x-hidden min-h-screen flex flex-col">
        {/* FIXED HEADER */}
        <header className="fixed top-0 left-0 right-0 h-16 bg-surface-container-highest border-b border-outline-variant flex items-center justify-between px-6 z-50">
          <div className="flex items-center gap-4">
            <h1 className="font-heading text-headline-lg font-bold text-primary tracking-widest uppercase">
              Q-SHIELD
            </h1>
            <span className="bg-surface-container-low border border-outline-variant px-2 py-1 text-label-md text-on-surface-variant uppercase tracking-widest rounded">
              SIH26141
            </span>
            <span className="text-label-md text-on-surface-variant uppercase tracking-wider ml-4">
              v2.4-PROD // QISKIT-AER BACKEND
            </span>
          </div>

          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-tertiary"></span>
              <span className="text-label-md text-tertiary uppercase tracking-widest">
                SIMULATOR: ONLINE
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-secondary"></span>
              <span className="text-label-md text-secondary uppercase tracking-widest">
                DETECTION: ONLINE
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-tertiary"></span>
              <span className="text-label-md text-tertiary uppercase tracking-widest">
                EVIDENCE: SYNC
              </span>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2 bg-error-container border border-error px-3 py-1.5 rounded">
              <span className="w-1.5 h-1.5 bg-error animate-pulse"></span>
              <span className="text-label-sm text-error uppercase tracking-widest font-bold">
                CRITICAL: COMPROMISED
              </span>
            </div>
            <span className="text-label-md text-on-surface-variant uppercase tracking-wider">
              {new Date().toISOString().split('T')[1].substring(0, 8)} UTC
            </span>
            <div className="w-8 h-8 bg-surface-container-low border border-outline-variant flex items-center justify-center rounded">
              <span className="material-symbols-outlined text-on-surface text-[18px]">
                person
              </span>
            </div>
          </div>
        </header>

        {/* FIXED LEFT SIDEBAR */}
        <aside className="fixed top-16 left-0 bottom-0 w-64 bg-surface-container-lowest border-r border-outline-variant flex flex-col z-40">
          <nav className="flex-1 py-4 overflow-y-auto no-scrollbar">
            <ul className="flex flex-col">
              {navItems.map((item) => (
                <li key={item}>
                  <button
                    onClick={() => setActiveNav(item)}
                    className={`w-full text-left px-6 py-3 text-label-md uppercase tracking-widest transition-colors flex items-center gap-3 ${
                      activeNav === item
                        ? "bg-surface-container-high text-primary border-l-2 border-primary"
                        : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface border-l-2 border-transparent"
                    }`}
                  >
                    <span className="material-symbols-outlined text-[16px]">
                      {item === "Simulation Lab" ? "science" : "terminal"}
                    </span>
                    {item}
                  </button>
                </li>
              ))}
            </ul>
          </nav>
          
          <div className="p-4 border-t border-outline-variant bg-surface-container-low">
            <div className="flex justify-between items-end mb-2">
              <span className="text-label-sm text-on-surface-variant uppercase tracking-widest">
                TELEMETRY BUS
              </span>
              <span className="text-label-sm text-tertiary uppercase tracking-widest">
                98.42%
              </span>
            </div>
            <div className="h-0.5 w-full bg-surface-container-high rounded">
              <div className="h-full bg-tertiary w-3/4 rounded"></div>
            </div>
            <div className="mt-2 text-label-sm text-on-surface-variant uppercase tracking-widest">
              ENTANGLEMENT FIDELITY
            </div>
          </div>
        </aside>

        {/* MAIN CONTENT AREA */}
        <main className="flex-1 pl-64 pt-16">
          {children}
        </main>
      </body>
    </html>
  );
}
