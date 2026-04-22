import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { Zap } from "lucide-react";
import api from "../api/client";

export default function NewRFP() {
  const [title, setTitle] = useState("");
  const [rawText, setRawText] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!rawText.trim()) {
      toast.error("Please paste the RFP text.");
      return;
    }
    setLoading(true);
    try {
      const { data: rfp } = await api.post("/rfps/", { title, raw_text: rawText });
      toast.success("RFP saved — generating proposal...");
      const { data: proposal } = await api.post(`/rfps/${rfp.id}/generate/`);
      navigate(`/proposals/${proposal.id}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create RFP.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">New RFP</h1>
        <p className="text-gray-500 mt-1">Paste the project brief or RFP text and we'll generate a tailored proposal</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Proposal Title</label>
          <input
            type="text"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g. Website Redesign for TechCorp"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">RFP / Project Brief Text</label>
          <textarea
            required
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            rows={16}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono resize-none"
            placeholder="Paste the full RFP or project brief here..."
          />
          <p className="text-xs text-gray-400 mt-1">{rawText.length} characters</p>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-60 transition-colors"
        >
          <Zap size={16} />
          {loading ? "Generating proposal..." : "Generate Proposal"}
        </button>
      </form>
    </div>
  );
}
