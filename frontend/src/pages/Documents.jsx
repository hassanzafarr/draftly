import { useEffect, useState, useCallback } from "react";
import { toast } from "react-hot-toast";
import { Upload } from "lucide-react";
import api from "../api/client";
import DocumentCard from "../components/DocumentCard";
import UploadZone from "../components/UploadZone";
import ConfirmModal from "../components/ConfirmModal";

function isIndexing(doc) {
  return doc.status === "pending" || doc.status === "processing";
}

export default function Documents() {
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const fetchDocs = useCallback(() => {
    api
      .get("/documents/")
      .then((r) => setDocs(r.data.results || r.data))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  useEffect(() => {
    if (!docs.some(isIndexing)) return undefined;
    const interval = setInterval(fetchDocs, 5000);
    return () => clearInterval(interval);
  }, [docs, fetchDocs]);

  const handleDrop = async ([file]) => {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", file.name.replace(/\.[^/.]+$/, ""));
    setUploading(true);
    try {
      await api.post("/documents/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("Document uploaded — processing started.");
      fetchDocs();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = (id, title) => {
    setDeleteTarget({ id, title });
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.delete(`/documents/${deleteTarget.id}/`);
      setDocs((d) => d.filter((doc) => doc.id !== deleteTarget.id));
      toast.success("Document deleted.");
    } catch {
      toast.error("Failed to delete document.");
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
        <p className="text-gray-500 mt-1">
          Upload past proposals, case studies, and company profiles
        </p>
      </div>

      <div className="mb-6">
        <UploadZone onDrop={handleDrop} />
        {uploading && <p className="text-sm text-blue-600 mt-2 text-center">Uploading...</p>}
      </div>

      {loading ? (
        <p className="text-gray-400 text-sm">Loading documents...</p>
      ) : docs.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <Upload size={32} className="mx-auto mb-3" />
          <p>No documents yet. Upload your first one above.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {docs.map((doc) => (
            <DocumentCard key={doc.id} doc={doc} onDelete={handleDelete} />
          ))}
        </div>
      )}

      <ConfirmModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDeleteConfirm}
        title="Delete Document"
        description={`Are you sure you want to delete "${deleteTarget?.title || ""}" and all its indexed data? This action cannot be undone.`}
        confirmText="Delete"
        variant="destructive"
        loading={deleting}
      />
    </div>
  );
}
