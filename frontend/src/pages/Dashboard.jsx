import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileText, Upload, Plus, ChevronRight } from "lucide-react";
import api from "../api/client";
import useAuthStore from "../store/auth";

export default function Dashboard() {
  const { user } = useAuthStore();
  const [proposals, setProposals] = useState([]);
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.get("/proposals/"), api.get("/documents/")])
      .then(([p, d]) => {
        setProposals(p.data.results || p.data);
        setDocs(d.data.results || d.data);
      })
      .finally(() => setLoading(false));
  }, []);

  const stats = [
    { label: "Documents", value: docs.length, icon: Upload, href: "/documents" },
    { label: "Proposals", value: proposals.length, icon: FileText, href: "/proposals" },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">{user?.org?.name} · {user?.org?.subscription_tier} plan</p>
        </div>
        <Link
          to="/rfps/new"
          className="flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors"
        >
          <Plus size={16} />
          New RFP
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-8">
        {stats.map(({ label, value, icon: Icon, href }) => (
          <Link key={label} to={href} className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-sm transition-shadow">
            <div className="flex items-center gap-3 mb-2">
              <Icon size={18} className="text-blue-600" />
              <span className="text-sm font-medium text-gray-500">{label}</span>
            </div>
            <p className="text-3xl font-bold text-gray-900">{loading ? "—" : value}</p>
          </Link>
        ))}
      </div>

      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-700">Recent Proposals</h2>
        </div>
        {loading ? (
          <p className="text-gray-400 text-sm">Loading...</p>
        ) : proposals.length === 0 ? (
          <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
            <FileText size={32} className="mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500 font-medium">No proposals yet</p>
            <p className="text-sm text-gray-400 mt-1">Submit an RFP to generate your first proposal</p>
            <Link to="/rfps/new" className="inline-flex items-center gap-2 mt-4 text-blue-600 text-sm font-medium hover:underline">
              Get started <ChevronRight size={14} />
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {proposals.slice(0, 5).map((p) => (
              <Link
                key={p.id}
                to={`/proposals/${p.id}`}
                className="flex items-center justify-between bg-white rounded-xl border border-gray-200 px-5 py-4 hover:shadow-sm transition-shadow"
              >
                <div>
                  <p className="font-medium text-gray-900">{p.rfp_title}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{new Date(p.created_at).toLocaleDateString()}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs font-medium px-2.5 py-1 rounded-full
                    ${p.status === "final" ? "bg-green-100 text-green-700" :
                      p.status === "generating" ? "bg-blue-100 text-blue-700" :
                      p.status === "failed" ? "bg-red-100 text-red-700" :
                      "bg-yellow-100 text-yellow-700"}`}>
                    {p.status}
                  </span>
                  <ChevronRight size={16} className="text-gray-400" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
