import os
import time

import requests
from loguru import logger

from .base import BaseRetriever, register_retriever
from ..protocol import Paper


@register_retriever("semantic_scholar")
class SemanticScholarRetriever(BaseRetriever):
    """
    Retrieve recent journal and conference papers from Semantic Scholar.

    This source complements arXiv with peer-reviewed publication venues. It is
    query-based because Semantic Scholar does not expose arXiv-like category
    feeds for every field.
    """

    API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    def __init__(self, config):
        super().__init__(config)

        self.query = self.retriever_config.get("query") or (
            '("medical image segmentation" OR "PET/MRI" OR "PET MRI" OR "semi-supervised segmentation")'
        )
        self.limit = int(self.retriever_config.get("limit", 100))
        self.year_from = int(self.retriever_config.get("year_from", 2024))
        self.year_to = self.retriever_config.get("year_to", None)
        self.venue_filter = self.retriever_config.get("venue_filter", None)
        self.api_key = self.retriever_config.get("api_key", None) or os.getenv(
            "SEMANTIC_SCHOLAR_API_KEY"
        )
        self.publication_types = self.retriever_config.get(
            "publication_types",
            ["JournalArticle", "Conference"],
        )

        # Papers without abstracts are poor reranking candidates.
        self.require_abstract = bool(self.retriever_config.get("require_abstract", True))

        # Venue presence is the main signal that this is a journal/conference paper.
        self.require_venue = bool(self.retriever_config.get("require_venue", True))

    def _retrieve_raw_papers(self) -> list[dict]:
        fields = ",".join(
            [
                "paperId",
                "title",
                "abstract",
                "authors",
                "year",
                "venue",
                "publicationVenue",
                "publicationTypes",
                "publicationDate",
                "externalIds",
                "url",
                "openAccessPdf",
            ]
        )

        params = {
            "query": self.query,
            "limit": self.limit,
            "fields": fields,
            "year": self._build_year_param(),
        }

        logger.info(f"Semantic Scholar query: {self.query}")
        logger.info(f"Semantic Scholar year: {params['year']}")
        headers = self._build_headers()

        response = None

        for attempt in range(3):
            response = requests.get(
                self.API_URL,
                params=params,
                headers=headers,
                timeout=30,
            )

            if response.status_code != 429:
                break

            wait_seconds = 10 * (attempt + 1)
            logger.warning(
                f"Semantic Scholar API rate limited: 429. "
                f"Retrying in {wait_seconds} seconds... "
                f"attempt={attempt + 1}/3"
            )
            time.sleep(wait_seconds)

        if response is None:
            return []

        if response.status_code == 429:
            logger.error(
                "Semantic Scholar API is still rate limited after retries. "
                "Returning empty result instead of failing the workflow."
            )
            return []

        response.raise_for_status()
        data = response.json()
        raw_papers = data.get("data", [])

        logger.info(f"Semantic Scholar returned {len(raw_papers)} raw papers")
        time.sleep(1)
        return raw_papers

    def _build_headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"x-api-key": str(self.api_key)}

    def _build_year_param(self) -> str:
        if self.year_to is None:
            return f"{self.year_from}-"
        return f"{self.year_from}-{int(self.year_to)}"

    def convert_to_paper(self, raw_paper: dict) -> Paper | None:
        title = raw_paper.get("title") or ""
        abstract = raw_paper.get("abstract") or ""

        if not title:
            return None

        if self.require_abstract and not abstract:
            return None

        venue = self._extract_venue(raw_paper)

        if self.require_venue and not venue:
            return None

        publication_types = raw_paper.get("publicationTypes") or []

        # Keep only the requested publication types, usually journals/conferences.
        if self.publication_types:
            if not any(t in publication_types for t in self.publication_types):
                return None

        # Optional allowlist for target journals/conferences.
        if self.venue_filter:
            venue_lower = venue.lower() if venue else ""
            if not any(v.lower() in venue_lower for v in self.venue_filter):
                return None

        authors = [
            a.get("name", "")
            for a in raw_paper.get("authors", [])
            if a.get("name")
        ]

        external_ids = raw_paper.get("externalIds") or {}
        doi = external_ids.get("DOI")

        url = raw_paper.get("url") or ""
        if not url and doi:
            url = f"https://doi.org/{doi}"

        open_access_pdf = raw_paper.get("openAccessPdf") or {}
        pdf_url = open_access_pdf.get("url")

        return Paper(
            source=self.name,
            title=title,
            authors=authors,
            abstract=abstract,
            url=url,
            pdf_url=pdf_url,
            full_text=None,
            doi=doi,
            venue=venue,
            year=raw_paper.get("year"),
            publication_date=raw_paper.get("publicationDate"),
            publication_types=publication_types,
        )

    def _extract_venue(self, raw_paper: dict) -> str | None:
        pub_venue = raw_paper.get("publicationVenue") or {}

        if isinstance(pub_venue, dict):
            name = pub_venue.get("name")
            if name:
                return name

        venue = raw_paper.get("venue")
        if venue:
            return venue

        return None
