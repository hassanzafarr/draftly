"""Specs for the built-in (org=None) proposal templates.

Seeded into the DB by migration 0011_seed_builtin_templates; also imported by
tests (which run with --no-migrations) to create the same fixtures.
"""

BUILTIN_TEMPLATES = [
    {
        "title": "Web Platform Redesign",
        "snippet": (
            "Full-stack redesign proposal covering UX, architecture, and delivery "
            "milestones for modern web platforms."
        ),
        "category": "web",
        "accent": "violet",
        "sort_order": 1,
        "sections": [
            "Executive Summary",
            "Discovery & Research",
            "UX Strategy",
            "Information Architecture",
            "Technical Architecture",
            "Tech Stack",
            "Delivery Milestones",
            "Project Timeline",
            "Investment",
            "Why Us",
        ],
    },
    {
        "title": "Mobile App Development",
        "snippet": (
            "End-to-end native or cross-platform mobile proposal with sprint "
            "planning and release roadmap."
        ),
        "category": "mobile",
        "accent": "cyan",
        "sort_order": 2,
        "sections": [
            "Overview",
            "Requirements Analysis",
            "Product Architecture",
            "UX & Design Approach",
            "Development Sprints",
            "QA & Testing Plan",
            "Release Roadmap",
            "Team",
            "Pricing",
            "Next Steps",
        ],
    },
    {
        "title": "Data Analytics Dashboard",
        "snippet": (
            "Business intelligence proposal with KPI definition, data pipeline "
            "design, and visualisation plan."
        ),
        "category": "data",
        "accent": "emerald",
        "sort_order": 3,
        "sections": [
            "Executive Summary",
            "Business Goals & KPIs",
            "Data Sources & Integration",
            "Data Pipeline Design",
            "Dashboard & Visualisation Plan",
            "Governance & Security",
            "Delivery Timeline",
            "Team",
            "Investment",
            "Appendix",
        ],
    },
    {
        "title": "Brand & Design System",
        "snippet": (
            "Comprehensive design system proposal: tokens, component library, "
            "documentation, and hand-off."
        ),
        "category": "design",
        "accent": "magenta",
        "sort_order": 4,
        "sections": [
            "Brief & Objectives",
            "Brand Audit",
            "Design Principles",
            "Design Tokens",
            "Component Library",
            "Documentation & Guidelines",
            "Adoption & Hand-off",
            "Timeline",
            "Pricing",
            "Why Us",
        ],
    },
    {
        "title": "Cloud Infrastructure Migration",
        "snippet": (
            "Step-by-step cloud migration proposal with risk assessment, cost "
            "modelling, and cutover plan."
        ),
        "category": "infrastructure",
        "accent": "amber",
        "sort_order": 5,
        "sections": [
            "Current State Assessment",
            "Target Architecture",
            "Migration Strategy",
            "Risk Assessment & Mitigation",
            "Security & Compliance",
            "Cutover Plan",
            "Cost Model",
            "Timeline",
            "Team",
            "Appendix",
        ],
    },
    {
        "title": "AI Integration Proposal",
        "snippet": (
            "LLM and ML integration proposal with use-case mapping, model "
            "selection, and evaluation criteria."
        ),
        "category": "data",
        "accent": "violet",
        "sort_order": 6,
        "sections": [
            "Executive Summary",
            "Use Case Mapping",
            "Model Selection",
            "Data & Integration Plan",
            "Evaluation Criteria",
            "Risk & Compliance",
            "Implementation Roadmap",
            "Team",
            "Pricing",
            "Next Steps",
        ],
    },
]


def seed_builtin_templates(template_model):
    """Idempotently create/refresh the built-in templates via the given model class."""
    for spec in BUILTIN_TEMPLATES:
        template_model.objects.update_or_create(
            org=None, title=spec["title"], defaults={**spec, "is_active": True}
        )
