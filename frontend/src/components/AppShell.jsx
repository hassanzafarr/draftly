import { Outlet } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { Sidebar } from "./Sidebar";
import useAuthStore from "../store/auth";

export function AppShell() {
  const user = useAuthStore((s) => s.user);
  const isPastDue = user?.org?.subscription_status === "past_due";

  return (
    <div className="relative h-dvh overflow-hidden">
      <div className="app-backdrop" />
      <div className="stars pointer-events-none absolute inset-0 opacity-40" />
      <div className="relative z-10 flex h-full flex-col">
        {isPastDue && (
          <div className="flex shrink-0 items-center justify-center gap-2 bg-amber/15 px-4 py-2 text-xs font-medium text-amber ring-1 ring-inset ring-amber/30">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            Payment failed — please{" "}
            <a href="/settings" className="underline underline-offset-2 hover:text-amber/80">
              update your payment method
            </a>{" "}
            to avoid service interruption.
          </div>
        )}
        <div className="flex min-h-0 flex-1">
          <Sidebar />
          <main className="relative min-h-0 min-w-0 flex-1 overflow-y-auto overflow-x-hidden overscroll-contain">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
