import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";

export function AppShell() {
  return (
    <div className="relative h-dvh overflow-hidden">
      <div className="app-backdrop" />
      <div className="stars pointer-events-none absolute inset-0 opacity-40" />
      <div className="relative z-10 flex h-full">
        <Sidebar />
        <main className="relative h-dvh min-w-0 flex-1 overflow-y-auto overflow-x-hidden overscroll-contain">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
