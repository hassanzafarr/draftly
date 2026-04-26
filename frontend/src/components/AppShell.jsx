import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";

export function AppShell() {
  return (
    <div className="relative min-h-dvh overflow-hidden">
      <div className="app-backdrop" />
      <div className="stars pointer-events-none absolute inset-0 opacity-40" />
      <div className="relative z-10 flex min-h-dvh">
        <Sidebar />
        <main className="relative flex-1 overflow-x-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
