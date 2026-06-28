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

  const MIN_CHARS = 200;
  const MIN_WORDS = 30;

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = rawText.trim();
    if (!trimmed) {
      toast.error("Please paste the RFP text.");
      return;
    }
    if (trimmed.length < MIN_CHARS) {
      toast.error(
        `RFP too short. Need at least ${MIN_CHARS} characters describing scope and requirements.`
      );
      return;
    }
    if (trimmed.split(/\s+/).length < MIN_WORDS) {
      toast.error(
        `RFP too short. Need at least ${MIN_WORDS} words describing scope and requirements.`
      );
      return;
    }
    setLoading(true);
    try {
      const { data: rfp } = await api.post("/rfps/", { title, raw_text: rawText });
      toast.success("RFP saved — generating proposal...");
      const { data: proposal } = await api.post(`/rfps/${rfp.id}/generate/`);
      navigate(`/proposals/${proposal.id}`);
    } catch (err) {
      // Log full error so it's visible in browser DevTools (Network + Console tabs)
      console.error("[NewRFP] RFP creation failed:", {
        status: err.response?.status,
        data: err.response?.data,
        message: err.message,
      });

      const httpStatus = err.response?.status;
      const data = err.response?.data;
      let message = "Failed to create RFP. Please try again.";

      if (typeof data === "string" && data.trim().startsWith("<")) {
        // Server returned HTML (e.g. Django's debug 500 page) — don't show raw HTML
        message =
          httpStatus === 500
            ? "A server error occurred. Please try again or contact support."
            : `Unexpected server response (HTTP ${httpStatus}).`;
      } else if (data) {
        if (typeof data.detail === "string") {
          // Standard DRF error: { detail: "..." }
          message = data.detail;
        } else if (typeof data === "object") {
          // DRF field/validation errors: { raw_text: ["too short"], title: ["required"] }
          const parts = Object.entries(data)
            .map(([field, errs]) => {
              const errList = Array.isArray(errs) ? errs.join(" ") : String(errs);
              return field === "non_field_errors" ? errList : `${field}: ${errList}`;
            })
            .filter(Boolean);
          if (parts.length) message = parts.join(" · ");
        }
      } else if (!err.response) {
        message = "Network error — check your connection and try again.";
      }

      if (httpStatus === 403 && message.toLowerCase().includes("quota")) {
        toast.error(message);
        navigate("/pricing");
      } else {
        toast.error(message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">New RFP</h1>
        <p className="text-gray-500 mt-1">
          Paste the project brief or RFP text and we&apos;ll generate a tailored proposal
        </p>
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
          <label className="block text-sm font-medium text-gray-700 mb-1">
            RFP / Project Brief Text
          </label>
          <textarea
            required
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            rows={16}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono resize-none"
            placeholder="Paste the full RFP or project brief here..."
          />
          <p
            className={`text-xs mt-1 ${rawText.trim().length < MIN_CHARS ? "text-red-500" : "text-gray-400"}`}
          >
            {rawText.length} characters {rawText.trim().length < MIN_CHARS && `(min ${MIN_CHARS})`}
          </p>
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
