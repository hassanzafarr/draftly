import { Link } from "react-router-dom";
import { AuthShell } from "../components/AuthShell";
import { AuthForm } from "../components/AuthForm";

export default function Login() {
  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to continue drafting proposals"
      footer={
        <>
          New to PropoAI?{" "}
          <Link
            to="/register"
            className="font-medium text-foreground transition hover:text-violet"
          >
            Create an account
          </Link>
        </>
      }
    >
      <AuthForm mode="login" />
    </AuthShell>
  );
}
