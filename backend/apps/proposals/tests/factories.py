import factory
from factory.django import DjangoModelFactory

from apps.accounts.tests.factories import OrganizationFactory, UserFactory
from apps.proposals.models import RFP, Proposal

# Passes both serializer minimums (200 chars / 30 words) and the intent
# classifier's keyword heuristics.
VALID_RFP_TEXT = (
    "Request for proposal: our client needs a vendor to design, build, and "
    "deploy a patient scheduling platform for a regional healthcare network. "
    "Scope includes requirements discovery, system integration with the "
    "existing EHR, HIPAA compliance review, project timeline with milestones, "
    "budget breakdown, and a dedicated implementation team. Deliverables must "
    "cover design, development, deployment, and training."
)


class RFPFactory(DjangoModelFactory):
    class Meta:
        model = RFP

    org = factory.SubFactory(OrganizationFactory)
    created_by = factory.SubFactory(UserFactory, org=factory.SelfAttribute("..org"))
    title = factory.Sequence(lambda n: f"RFP {n}")
    raw_text = VALID_RFP_TEXT


class ProposalFactory(DjangoModelFactory):
    class Meta:
        model = Proposal

    rfp = factory.SubFactory(RFPFactory)
    org = factory.SelfAttribute("rfp.org")
    status = Proposal.Status.DRAFT
    sections = factory.LazyFunction(
        lambda: {key: f"{key} content" for key in Proposal.SECTION_KEYS}
    )
