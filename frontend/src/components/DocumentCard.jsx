import { FileText, Trash2, Clock, CheckCircle, AlertCircle, Loader } from "lucide-react";

const STATUS_CONFIG = {
  pending:    { icon: Clock,        color: "text-yellow-500", label: "Pending" },
  processing: { icon: Loader,       color: "text-blue-500",   label: "Processing" },
  processed:  { icon: CheckCircle,  color: "text-green-500",  label: "Processed" },
  failed:     { icon: AlertCircle,  color: "text-red-500",    label: "Failed" },
};

export default function DocumentCard({ doc, onDelete }) {
  const { icon: Icon, color, label } = STATUS_CONFIG[doc.status] || STATUS_CONFIG.pending;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-start gap-4 hover:shadow-sm transition-shadow">
      <div className="p-2 bg-blue-50 rounded-lg">
        <FileText size={20} className="text-blue-600" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 truncate">{doc.title}</p>
        <p className="text-xs text-gray-400 mt-0.5">
          {doc.file_type?.toUpperCase()} · {doc.chunk_count} chunks · {new Date(doc.created_at).toLocaleDateString()}
        </p>
        <div className={`flex items-center gap-1 mt-1 text-xs font-medium ${color}`}>
          <Icon size={12} className={doc.status === "processing" ? "animate-spin" : ""} />
          {label}
        </div>
      </div>
      <button
        onClick={() => onDelete(doc.id)}
        className="text-gray-300 hover:text-red-500 transition-colors shrink-0"
        title="Delete document"
      >
        <Trash2 size={16} />
      </button>
    </div>
  );
}
