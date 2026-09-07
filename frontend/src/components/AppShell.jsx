import { useEffect, useCallback } from "react";
import { Outlet, Link, useNavigate } from "react-router-dom";
import { AlertTriangle, PlayCircle } from "lucide-react";
import { Sidebar } from "./Sidebar";
import useAuthStore from "../store/auth";
import useDemoTourStore, { DEMO_TOUR_STORAGE_KEY } from "../store/demoTour";
import { DemoOnboardingModal } from "./DemoOnboardingModal";

export function AppShell() {
  const user = useAuthStore((s) => s.user);
  const isPastDue = user?.org?.subscription_status === "past_due";
  const isDemo = user?.org?.subscription_tier === "demo" || user?.email === "demo@draftly.software";
  const { isOpen, openTour, closeTour } = useDemoTourStore();
  const navigate = useNavigate();

  useEffect(() => {
    if (isDemo && typeof window !== "undefined") {
      const hasSeenTour = localStorage.getItem(DEMO_TOUR_STORAGE_KEY);
      if (!hasSeenTour) {
        openTour();
      }
    }
  }, [isDemo, openTour]);

  const handleTourAction = useCallback(
    (action) => {
      if (action === "generate") {
        navigate("/");
      }
    },
    [navigate]
  );

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

        {isDemo && (
          <div className="flex shrink-0 items-center justify-between gap-2 border-b border-hairline bg-surface-2/70 px-4 py-1.5 text-xs backdrop-blur-md">
            <div className="flex items-center gap-2.5">
              <span className="flex h-2 w-2 rounded-full bg-cyan shadow-sm shadow-cyan/50" />
              <span className="font-semibold text-foreground">Draftly Demo Sandbox</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={openTour}
                className="flex items-center gap-1.5 rounded-lg border border-violet/40 bg-violet/15 px-2.5 py-1 text-xs font-medium text-violet transition hover:bg-violet/25 hover:text-white active:scale-95"
              >
                <PlayCircle className="h-3 w-3" />
                <span>Demo Tutorial</span>
              </button>
              <Link
                to="/pricing"
                className="hidden sm:inline-flex items-center gap-1 rounded-lg border border-hairline bg-surface px-2.5 py-1 text-xs text-muted-foreground transition hover:border-violet/40 hover:text-foreground"
              >
                View Plans
              </Link>
            </div>
          </div>
        )}

        <div className="flex min-h-0 flex-1">
          <Sidebar />
          <main className="relative min-h-0 min-w-0 flex-1 overflow-y-auto overflow-x-hidden overscroll-contain">
            <Outlet />
          </main>
        </div>
      </div>

      {/* Demo Onboarding Slideshow Tutorial */}
      {isDemo && (
        <DemoOnboardingModal open={isOpen} onClose={closeTour} onAction={handleTourAction} />
      )}
    </div>
  );
}
