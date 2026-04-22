import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center text-center px-4">
      <p className="text-6xl font-bold text-gray-200 mb-4">404</p>
      <p className="text-lg font-medium text-gray-700 mb-2">Page not found</p>
      <p className="text-gray-400 mb-6">The page you're looking for doesn't exist.</p>
      <Link to="/" className="text-blue-600 hover:underline font-medium">Go to Dashboard</Link>
    </div>
  );
}
