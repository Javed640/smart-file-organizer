"""Content-aware planning helpers."""

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from smart_file_organizer.config import DEFAULT_FALLBACK_FOLDER
from smart_file_organizer.core import (
    PlannedMove,
    RulePrecedence,
    SemanticFolderRule,
    TaxonomyProfileName,
    build_organization_plan_with_document_texts,
)
from smart_file_organizer.document_text import (
    DocumentInspectionResult,
    DocumentInspectionStatus,
    extract_document_text,
    inspect_document_text as _inspect_document_text,
)


logger = logging.getLogger(__name__)
DocumentTextExtractor = Callable[[Path], str]


@dataclass(frozen=True)
class PlanningOptions:
    """Configuration options for content-aware planning."""

    semantic_rules: Iterable[SemanticFolderRule] | None = None
    fallback_folder: str | None = DEFAULT_FALLBACK_FOLDER
    rule_precedence: RulePrecedence = "builtins-first"
    disabled_builtin_rules: Iterable[str] = ()
    taxonomy_profile: TaxonomyProfileName = TaxonomyProfileName.PERSONAL_IT


def inspect_document_text(
    path: Path,
    *,
    max_pages: int = 3,
    verbose: bool = False,
) -> DocumentInspectionResult:
    """Inspect content through the module-level extraction seam."""
    return _inspect_document_text(
        path,
        max_pages=max_pages,
        verbose=verbose,
        extract_text=extract_document_text,
    )


def build_organization_plan_with_extracted_text(
    sources: Iterable[Path],
    target_root: Path,
    *,
    extract_text: DocumentTextExtractor,
    options: PlanningOptions | None = None,
) -> list[PlannedMove]:
    """Build move plans using an injected text extractor."""
    options = options or PlanningOptions()
    source_list = list(sources)
    document_texts = {source: extract_text(source) for source in source_list}

    return build_organization_plan_with_document_texts(
        source_list,
        target_root,
        document_texts,
        semantic_rules=options.semantic_rules,
        fallback_folder=options.fallback_folder,
        rule_precedence=options.rule_precedence,
        disabled_builtin_rules=options.disabled_builtin_rules,
        taxonomy_profile=options.taxonomy_profile,
    )


def build_organization_plan_inspecting_content(
    sources: Iterable[Path],
    target_root: Path,
    *,
    options: PlanningOptions | None = None,
    verbose: bool = False,
) -> list[PlannedMove]:
    """Build plans with safe inspection and filename fallback."""
    options = options or PlanningOptions()
    source_list = list(sources)
    document_texts: dict[Path, str] = {}

    for source in source_list:
        result = inspect_document_text(
            source,
            verbose=verbose,
        )
        document_texts[source] = result.text

        if result.status == DocumentInspectionStatus.FAILED:
            logger.warning(
                "content inspection failed; using filename fallback: %s",
                source,
            )

            if verbose:
                logger.info(
                    "event=content_inspection_failed path=%s error_type=%s",
                    source,
                    result.error_type or "UnknownError",
                )

        elif (
            result.status == DocumentInspectionStatus.NO_TEXT
            and source.suffix.lower() == ".pdf"
        ):
            logger.warning(
                "content inspection found no text; using filename fallback: %s",
                source,
            )

            if verbose:
                logger.info(
                    "event=content_inspection_no_text path=%s",
                    source,
                )

    return build_organization_plan_with_document_texts(
        source_list,
        target_root,
        document_texts,
        semantic_rules=options.semantic_rules,
        fallback_folder=options.fallback_folder,
        rule_precedence=options.rule_precedence,
        disabled_builtin_rules=options.disabled_builtin_rules,
        taxonomy_profile=options.taxonomy_profile,
    )
