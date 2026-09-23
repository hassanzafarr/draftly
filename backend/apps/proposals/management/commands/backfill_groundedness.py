import re
import time

from django.core.management.base import BaseCommand
from google.api_core.exceptions import ResourceExhausted

from apps.documents.models import Chunk
from apps.proposals.groundedness import score_groundedness
from apps.proposals.models import GenerationEvent

MAX_RATE_LIMIT_RETRIES = 6
DEFAULT_RETRY_DELAY_SECONDS = 60
RETRY_DELAY_RE = re.compile(r"retry in ([\d.]+)s")


class Command(BaseCommand):
    help = (
        "Score groundedness for existing successful GenerationEvents that predate the "
        "groundedness check (groundedness_sentence_total == 0). Re-fetches the chunks each "
        "proposal actually used (by id, from chunks_used) and re-scores its stored sections. "
        "Makes one embedding API call per proposal (batched across its sentences) — costs "
        "quota and shares the same free-tier rate limit as live traffic, so use --limit / "
        "--dry-run on a first pass. Safe to re-run: already-scored events are skipped unless "
        "--force is passed, so a run interrupted by rate limits just picks up where it left off."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=None, help="Max number of events to process"
        )
        parser.add_argument("--org", default=None, help="Only backfill events for this org id")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-score events that already have a groundedness score",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Compute and print scores without saving",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=1.5,
            help="Seconds to pause between events, to stay under the shared embedding quota",
        )

    def _score_with_backoff(self, sections, chunks):
        """Retry on free-tier rate limit (shared with live traffic) instead of dying mid-run."""
        for attempt in range(1, MAX_RATE_LIMIT_RETRIES + 1):
            try:
                return score_groundedness(sections, chunks)
            except ResourceExhausted as exc:
                if attempt == MAX_RATE_LIMIT_RETRIES:
                    raise
                match = RETRY_DELAY_RE.search(str(exc))
                delay = float(match.group(1)) + 5 if match else DEFAULT_RETRY_DELAY_SECONDS
                self.stdout.write(
                    self.style.WARNING(
                        f"Rate limited (attempt {attempt}/{MAX_RATE_LIMIT_RETRIES}), "
                        f"waiting {delay:.0f}s…"
                    )
                )
                time.sleep(delay)

    def handle(self, *args, **options):
        events = GenerationEvent.objects.filter(success=True).select_related("proposal")
        if not options["force"]:
            events = events.filter(groundedness_sentence_total=0)
        if options["org"]:
            events = events.filter(org_id=options["org"])
        if options["limit"]:
            events = events[: options["limit"]]

        processed = 0
        skipped_no_chunks = 0
        rate_sum = 0.0

        for event in events:
            chunk_ids = [c.get("chunk_id") for c in event.chunks_used if c.get("chunk_id")]
            if not chunk_ids:
                skipped_no_chunks += 1
                continue

            chunks = list(Chunk.objects.filter(id__in=chunk_ids))
            if not chunks:
                skipped_no_chunks += 1
                continue

            result = self._score_with_backoff(event.proposal.sections, chunks)
            if result["sentence_total"] == 0:
                skipped_no_chunks += 1
                continue

            processed += 1
            rate_sum += result["overall_rate"]
            self.stdout.write(
                f"{event.proposal_id}: {result['overall_rate']:.1%} "
                f"({result['sentence_grounded']}/{result['sentence_total']} sentences grounded)"
            )

            if not options["dry_run"]:
                event.groundedness_rate = result["overall_rate"]
                event.groundedness_sentence_total = result["sentence_total"]
                event.groundedness_sentence_grounded = result["sentence_grounded"]
                event.groundedness_sections = result["sections"]
                event.save(
                    update_fields=[
                        "groundedness_rate",
                        "groundedness_sentence_total",
                        "groundedness_sentence_grounded",
                        "groundedness_sections",
                    ]
                )

            if options["sleep"]:
                time.sleep(options["sleep"])

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {processed} events "
                f"({skipped_no_chunks} skipped — no matching chunks left in DB)."
            )
        )
        if processed:
            self.stdout.write(
                self.style.SUCCESS(f"Average groundedness rate: {rate_sum / processed:.1%}")
            )
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("--dry-run: nothing was saved."))
