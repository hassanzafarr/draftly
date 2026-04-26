import { Link } from "react-router-dom";
import { AuthShell } from "../components/AuthShell";
import { AuthForm } from "../components/AuthForm";

export default function Register() {
  return (
    <AuthShell
      title="Create your workspace"
      subtitle="Start drafting on-brand proposals in minutes"
      footer={
        <>
          Already have an account?{" "}
          <Link
            to="/login"
            className="font-medium text-foreground transition hover:text-violet"
          >
            Sign in
          </Link>
        </>
      }
    >
      <AuthForm mode="signup" />
    </AuthShell>
  );
}
