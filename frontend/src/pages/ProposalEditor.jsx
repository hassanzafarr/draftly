import { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import { toast } from "react-hot-toast";
import { Save, CheckCircle, Loader, AlertCircle } from "lucide-react";
import api from "../api/client";
import ProposalSection from "../components/ProposalSection";

const SECTION_ORDER = [
  "executive_summary",
  "understanding_requirements",
  "proposed_solution",
  "relevant_experience",
  "team_qualifications",
  "project_timeline",
  "methodology",
  "pricing",
  "why_us",
  "appendix",
];

export default function ProposalEditor() {
  const { id } = useParams();
  const [proposal, setProposal] = useState(null);
  const [sections, setSections] = useState({});
  const [saving, setSaving] = useState(false);
  const [polling, setPolling] = useState(false);

  const fetchProposal = useCallback(async () => {
    const { data } = await api.get(`/proposals/${id}/`);
    setProposal(data);
    if (data.sections) setSections(data.sections);
    return data;
  }, [id]);

  useEffect(() => {
    let interval;
    fetchProposal().then((data) => {
      if (data.status === "generating") {
        setPolling(true);
        interval = setInterval(async () => {
          const updated = await fetchProposal();
          if (updated.status !== "generating") {
            clearInterval(interval);
            setPolling(false);
          }
        }, 3000);
      }
    });
    return () => clearInterval(interval);
  }, [fetchProposal]);

  const handleSectionChange = (key, content) => {
    setSections((s) => ({ ...s, [key]: content }));
  };

  const handleSave = async (finalize = false) => {
    setSaving(true);
    try {
      await api.patch(`/proposals/${id}/`, {
        sections,
        ...(finalize ? { status: "final" } : {}),
      });
      toast.success(finalize ? "Proposal finalized!" : "Changes saved.");
      if (finalize) fetchProposal();
    } catch {
      toast.error("Failed to save.");
    } finally {
      setSaving(false);
    }
  };

  if (!proposal) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <Loader size={24} className="animate-spin mr-2" /> Loading proposal...
      </div>
    );
  }

  if (proposal.status === "generating" || polling) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4 text-gray-500">
        <Loader size={32} className="animate-spin text-blue-600" />
        <p className="font-medium">Generating your proposal...</p>
        <p className="text-sm">This takes 30–60 seconds. Hang tight.</p>
      </div>
    );
  }

  if (proposal.status === "failed") {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-red-500">
        <AlertCircle size={32} />
        <p className="font-medium">Generation failed</p>
        <p className="text-sm text-gray-400">{proposal.error_message}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{proposal.rfp_title}</h1>
          <p className="text-gray-400 text-sm mt-0.5">
            {proposal.status === "final" ? (
              <span className="flex items-center gap-1 text-green-600"><CheckCircle size={13} /> Finalized</span>
            ) : "Draft"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => handleSave(false)}
            disabled={saving}
            className="flex items-center gap-2 border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-60"
          >
            <Save size={14} />
            {saving ? "Saving..." : "Save Draft"}
          </button>
          {proposal.status !== "final" && (
            <button
              onClick={() => handleSave(true)}
              disabled={saving}
              className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60"
            >
              <CheckCircle size={14} />
              Finalize
            </button>
          )}
        </div>
      </div>

      <div className="space-y-5">
        {SECTION_ORDER.map((key) => (
          <ProposalSection
            key={key}
            sectionKey={key}
            content={sections[key] || ""}
            onChange={handleSectionChange}
          />
        ))}
      </div>

      <div className="mt-8 flex justify-end gap-3">
        <button
          onClick={() => handleSave(false)}
          disabled={saving}
          className="flex items-center gap-2 border border-gray-300 text-gray-700 px-5 py-2.5 rounded-lg font-medium hover:bg-gray-50 disabled:opacity-60"
        >
          <Save size={15} />
          {saving ? "Saving..." : "Save Draft"}
        </button>
      </div>
    </div>
  );
}
