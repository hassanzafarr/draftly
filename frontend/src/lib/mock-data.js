export const suggestionChips = [
  "Web platform redesign for a fintech startup",
  "Mobile app for a healthcare provider",
  "Custom CRM for a growing agency",
  "E-commerce integration & migration",
  "Data analytics dashboard build-out",
];

export const coreFeatures = [
  { id: "1", title: "RAG-Powered", caption: "Learns from your past proposals" },
  { id: "2", title: "10-Section Draft", caption: "Structured output, every time" },
  { id: "3", title: "Brand-Aligned", caption: "Matches your tone and style" },
];

export const tones = ["Persuasive", "Professional", "Formal", "Friendly", "Technical"];

export const sampleProposalSections = [
  { id: "executive_summary", title: "Executive Summary" },
  { id: "understanding_requirements", title: "Understanding Requirements" },
  { id: "proposed_solution", title: "Proposed Solution" },
  { id: "relevant_experience", title: "Relevant Experience" },
  { id: "team_qualifications", title: "Team Qualifications" },
  { id: "project_timeline", title: "Project Timeline" },
  { id: "methodology", title: "Methodology" },
  { id: "pricing", title: "Pricing" },
  { id: "why_us", title: "Why Us" },
  { id: "appendix", title: "Appendix" },
];

export const analyticsStats = {
  totalProposals: 148,
  successRate: 67,
  avgResponse: 2.4,
  revenueWon: 312000,
};

export const monthlyPerformance = [
  { month: "Jan", drafted: 10, won: 6 },
  { month: "Feb", drafted: 14, won: 8 },
  { month: "Mar", drafted: 12, won: 9 },
  { month: "Apr", drafted: 18, won: 11 },
  { month: "May", drafted: 16, won: 12 },
  { month: "Jun", drafted: 22, won: 15 },
  { month: "Jul", drafted: 20, won: 14 },
  { month: "Aug", drafted: 25, won: 18 },
  { month: "Sep", drafted: 23, won: 16 },
  { month: "Oct", drafted: 28, won: 20 },
  { month: "Nov", drafted: 30, won: 22 },
  { month: "Dec", drafted: 26, won: 19 },
];

export const winRateTrend = [
  { month: "Jan", value: 60 },
  { month: "Feb", value: 57 },
  { month: "Mar", value: 75 },
  { month: "Apr", value: 61 },
  { month: "May", value: 75 },
  { month: "Jun", value: 68 },
  { month: "Jul", value: 70 },
  { month: "Aug", value: 72 },
  { month: "Sep", value: 70 },
  { month: "Oct", value: 71 },
  { month: "Nov", value: 73 },
  { month: "Dec", value: 73 },
];

export const proposalsByCategory = [
  { name: "Web & Apps", value: 52, percentage: 35, color: "violet" },
  { name: "Data & AI", value: 37, percentage: 25, color: "cyan" },
  { name: "Design", value: 22, percentage: 15, color: "magenta" },
  { name: "Infrastructure", value: 22, percentage: 15, color: "emerald" },
  { name: "Other", value: 15, percentage: 10, color: "amber" },
];

// Templates now come from the backend: GET /api/templates/ (see pages/Templates.jsx).
