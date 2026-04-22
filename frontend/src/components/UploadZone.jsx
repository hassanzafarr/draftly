import { useDropzone } from "react-dropzone";
import { Upload, File } from "lucide-react";

export default function UploadZone({ onDrop, accept = { "application/pdf": [], "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [], "text/plain": [] } }) {
  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    onDrop,
    accept,
    multiple: false,
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors
        ${isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-blue-400 bg-white"}`}
    >
      <input {...getInputProps()} />
      {acceptedFiles.length > 0 ? (
        <div className="flex items-center justify-center gap-2 text-blue-600">
          <File size={20} />
          <span className="font-medium">{acceptedFiles[0].name}</span>
        </div>
      ) : (
        <div className="text-gray-500">
          <Upload size={32} className="mx-auto mb-3 text-gray-400" />
          <p className="font-medium">{isDragActive ? "Drop file here" : "Drag & drop or click to upload"}</p>
          <p className="text-sm mt-1">PDF, DOCX, or TXT</p>
        </div>
      )}
    </div>
  );
}
