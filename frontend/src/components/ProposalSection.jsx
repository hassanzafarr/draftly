import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useEffect } from "react";

const SECTION_LABELS = {
  executive_summary: "Executive Summary",
  understanding_requirements: "Understanding of Requirements",
  proposed_solution: "Proposed Solution / Technical Approach",
  relevant_experience: "Relevant Experience & Case Studies",
  team_qualifications: "Team & Qualifications",
  project_timeline: "Project Timeline",
  methodology: "Methodology",
  pricing: "Pricing / Commercial Proposal",
  why_us: "Why Us",
  appendix: "Appendix / Supporting Materials",
};

export default function ProposalSection({ sectionKey, content, onChange }) {
  const editor = useEditor({
    extensions: [StarterKit],
    content: content || "",
    onUpdate: ({ editor }) => {
      onChange(sectionKey, editor.getText());
    },
  });

  useEffect(() => {
    if (editor && content && editor.getText() !== content) {
      editor.commands.setContent(content);
    }
  }, [content]);

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-100 bg-gray-50">
        <h3 className="font-semibold text-gray-700 text-sm uppercase tracking-wide">
          {SECTION_LABELS[sectionKey] || sectionKey}
        </h3>
      </div>
      <div className="p-5 prose prose-sm max-w-none min-h-[120px]">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}
