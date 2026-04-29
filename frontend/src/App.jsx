import { lazy, Suspense, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { Analytics as VercelAnalytics } from "@vercel/analytics/react";
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
const NewRFP = lazy(() => import("./pages/NewRFP"));
const Editor = lazy(() => import("./pages/Editor"));
const NotFound = lazy(() => import("./pages/NotFound"));

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
    <ThemeProvider>
      <BrowserRouter>
        <Toaster position="top-right" />
        <VercelAnalytics />
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
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
              <Route path="rfps/new" element={<NewRFP />} />
              <Route path="proposals/:id" element={<Editor />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ThemeProvider>
  );
}
