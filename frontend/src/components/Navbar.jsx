import { Link, useNavigate } from "react-router-dom";
import { FileText, LogOut, Upload, LayoutDashboard } from "lucide-react";
import useAuthStore from "../store/auth";

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav className="bg-white border-b border-gray-200 px-4 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 font-bold text-lg text-blue-600">
          <FileText size={22} />
          ProposalAI
        </Link>

        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-blue-600">
            <LayoutDashboard size={16} />
            Dashboard
          </Link>
          <Link to="/documents" className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-blue-600">
            <Upload size={16} />
            Documents
          </Link>
          <Link to="/rfps/new" className="bg-blue-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
            New RFP
          </Link>
          <div className="flex items-center gap-3 border-l pl-4">
            <span className="text-sm text-gray-500">{user?.email}</span>
            <button onClick={handleLogout} className="text-gray-400 hover:text-red-500">
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
