import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import useAuthStore from "./store/auth";
import { ThemeProvider } from "./components/ThemeProvider";
import { AppShell } from "./components/AppShell";
import { Generator } from "./components/Generator";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Templates from "./pages/Templates";
import Knowledge from "./pages/knowledge";
import Analytics from "./pages/Analytics";
import NewRFP from "./pages/NewRFP";
import Editor from "./pages/editor";
import NotFound from "./pages/NotFound";

function PrivateRoute({ children }) {
  const { user, loading } = useAuthStore();
  if (loading) return (
    <div className="flex h-screen items-center justify-center text-muted-foreground">
      Loading…
    </div>
  );
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
      </BrowserRouter>
    </ThemeProvider>
  );
}
