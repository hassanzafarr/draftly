import { lazy, Suspense, useEffect } from "react";
import * as Sentry from "@sentry/react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { GoogleOAuthProvider } from "@react-oauth/google";
import useAuthStore from "./store/auth";
import { ThemeProvider } from "./components/ThemeProvider";
import { AppShell } from "./components/AppShell";

const Generator = lazy(() =>
  import("./components/Generator").then((m) => ({ default: m.Generator }))
);
const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));
const Templates = lazy(() => import("./pages/Templates"));
const Knowledge = lazy(() => import("./pages/knowledge"));
const Analytics = lazy(() => import("./pages/Analytics"));
const Proposals = lazy(() => import("./pages/Proposals"));
const Settings = lazy(() => import("./pages/Settings"));
const NewRFP = lazy(() => import("./pages/NewRFP"));
const Editor = lazy(() => import("./pages/Editor"));
const NotFound = lazy(() => import("./pages/NotFound"));
const Pricing = lazy(() => import("./pages/Pricing"));
const ForgotPassword = lazy(() => import("./pages/ForgotPassword"));
const ResetPassword = lazy(() => import("./pages/ResetPassword"));
const VerifyEmail = lazy(() => import("./pages/VerifyEmail"));

function PageFallback() {
  return (
    <div className="flex h-screen items-center justify-center text-muted-foreground">
      Loading…
    </div>
  );
}

function PrivateRoute({ children }) {
  const { user, loading } = useAuthStore();
  if (loading) return <PageFallback />;
  return user ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const fetchMe = useAuthStore((s) => s.fetchMe);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  return (
    <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID ?? ""}>
    <Sentry.ErrorBoundary fallback={<PageFallback />}>
      <ThemeProvider>
        <BrowserRouter>
          <Toaster position="top-right" />
          <Suspense fallback={<PageFallback />}>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/verify-email" element={<VerifyEmail />} />
              <Route
                path="/"
                element={
                  <PrivateRoute>
                    <AppShell />
                  </PrivateRoute>
                }
              >
                <Route index element={<Generator />} />
                <Route path="templates" element={<Templates />} />
                <Route path="knowledge" element={<Knowledge />} />
                <Route path="analytics" element={<Analytics />} />
                <Route path="proposals" element={<Proposals />} />
                <Route path="settings" element={<Settings />} />
                <Route path="rfps/new" element={<NewRFP />} />
                <Route path="proposals/:id" element={<Editor />} />
                <Route path="pricing" element={<Pricing />} />
              </Route>
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </ThemeProvider>
    </Sentry.ErrorBoundary>
    </GoogleOAuthProvider>
  );
}

