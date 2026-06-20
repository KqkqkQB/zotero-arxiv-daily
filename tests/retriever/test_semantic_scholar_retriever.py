"""Tests for SemanticScholarRetriever."""

from omegaconf import open_dict

from zotero_arxiv_daily.retriever.semantic_scholar_retriever import (
    SemanticScholarRetriever,
)


def _add_semantic_scholar_config(config):
    """Add semantic_scholar source config for tests."""
    with open_dict(config.source):
        config.source.semantic_scholar = {
            "query": "medical image segmentation",
            "queries": None,
            "year_from": 2025,
            "year_to": 2026,
            "limit": 5,
            "publication_types": ["JournalArticle", "Conference"],
            "require_abstract": True,
            "require_venue": True,
            "venue_filter": None,
            "api_key": None,
        }


def test_semantic_scholar_convert_journal_article(config):
    _add_semantic_scholar_config(config)

    retriever = SemanticScholarRetriever(config)

    raw_paper = {
        "paperId": "paper-1",
        "title": "Semi-supervised Medical Image Segmentation with Copy-Paste",
        "abstract": "This paper studies semi-supervised medical image segmentation.",
        "authors": [
            {"name": "Alice Wang"},
            {"name": "Bob Li"},
        ],
        "year": 2025,
        "venue": "Medical Image Analysis",
        "publicationVenue": {"name": "Medical Image Analysis"},
        "publicationTypes": ["JournalArticle"],
        "publicationDate": "2025-05-01",
        "externalIds": {
            "DOI": "10.1234/test.2025.001",
        },
        "url": "https://www.semanticscholar.org/paper/test",
        "openAccessPdf": {
            "url": "https://example.com/test.pdf",
        },
    }

    paper = retriever.convert_to_paper(raw_paper)

    assert paper is not None
    assert paper.source == "semantic_scholar"
    assert paper.title == "Semi-supervised Medical Image Segmentation with Copy-Paste"
    assert paper.abstract == "This paper studies semi-supervised medical image segmentation."
    assert paper.authors == ["Alice Wang", "Bob Li"]
    assert paper.venue == "Medical Image Analysis"
    assert paper.year == 2025
    assert paper.publication_date == "2025-05-01"
    assert paper.publication_types == ["JournalArticle"]
    assert paper.doi == "10.1234/test.2025.001"
    assert paper.url == "https://www.semanticscholar.org/paper/test"
    assert paper.pdf_url == "https://example.com/test.pdf"


def test_semantic_scholar_convert_conference_paper(config):
    _add_semantic_scholar_config(config)

    retriever = SemanticScholarRetriever(config)

    raw_paper = {
        "paperId": "paper-2",
        "title": "PET/MRI Multimodal Tumor Segmentation",
        "abstract": "This paper studies PET/MRI multimodal tumor segmentation.",
        "authors": [
            {"name": "Chen Zhang"},
        ],
        "year": 2026,
        "venue": "MICCAI",
        "publicationVenue": {"name": "MICCAI"},
        "publicationTypes": ["Conference"],
        "publicationDate": "2026-01-10",
        "externalIds": {},
        "url": "https://www.semanticscholar.org/paper/test2",
        "openAccessPdf": None,
    }

    paper = retriever.convert_to_paper(raw_paper)

    assert paper is not None
    assert paper.title == "PET/MRI Multimodal Tumor Segmentation"
    assert paper.venue == "MICCAI"
    assert paper.publication_types == ["Conference"]
    assert paper.pdf_url is None


def test_semantic_scholar_skip_without_abstract(config):
    _add_semantic_scholar_config(config)

    retriever = SemanticScholarRetriever(config)

    raw_paper = {
        "title": "Paper without abstract",
        "abstract": None,
        "authors": [{"name": "A"}],
        "year": 2025,
        "venue": "Medical Image Analysis",
        "publicationTypes": ["JournalArticle"],
        "url": "https://example.com",
    }

    paper = retriever.convert_to_paper(raw_paper)

    assert paper is None


def test_semantic_scholar_skip_without_venue(config):
    _add_semantic_scholar_config(config)

    retriever = SemanticScholarRetriever(config)

    raw_paper = {
        "title": "Paper without venue",
        "abstract": "abstract",
        "authors": [{"name": "A"}],
        "year": 2025,
        "venue": "",
        "publicationTypes": ["JournalArticle"],
        "url": "https://example.com",
    }

    paper = retriever.convert_to_paper(raw_paper)

    assert paper is None


def test_semantic_scholar_skip_unwanted_publication_type(config):
    _add_semantic_scholar_config(config)

    retriever = SemanticScholarRetriever(config)

    raw_paper = {
        "title": "Book Chapter Paper",
        "abstract": "abstract",
        "authors": [{"name": "A"}],
        "year": 2025,
        "venue": "Some Book",
        "publicationTypes": ["Book"],
        "url": "https://example.com",
    }

    paper = retriever.convert_to_paper(raw_paper)

    assert paper is None


def test_semantic_scholar_keep_venue_paper_without_publication_types(config):
    _add_semantic_scholar_config(config)

    retriever = SemanticScholarRetriever(config)

    raw_paper = {
        "title": "Venue Paper Without Publication Types",
        "abstract": "abstract",
        "authors": [{"name": "A"}],
        "year": 2025,
        "venue": "Medical Image Analysis",
        "publicationTypes": None,
        "url": "https://example.com",
    }

    paper = retriever.convert_to_paper(raw_paper)

    assert paper is not None
    assert paper.venue == "Medical Image Analysis"


def test_semantic_scholar_retrieve_raw_papers_mocked(config, monkeypatch):
    _add_semantic_scholar_config(config)

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": [
                    {
                        "paperId": "paper-1",
                        "title": "Medical Image Segmentation Paper",
                        "abstract": "abstract",
                        "authors": [{"name": "A"}],
                        "year": 2025,
                        "venue": "Medical Image Analysis",
                        "publicationVenue": {"name": "Medical Image Analysis"},
                        "publicationTypes": ["JournalArticle"],
                        "publicationDate": "2025-01-01",
                        "externalIds": {"DOI": "10.0000/test"},
                        "url": "https://example.com",
                        "openAccessPdf": {"url": "https://example.com/test.pdf"},
                    }
                ]
            }

    def fake_get(url, params=None, headers=None, timeout=None):
        assert "semanticscholar.org" in url
        assert params["query"] == "medical image segmentation"
        assert params["limit"] == 5
        assert params["year"] == "2025-2026"
        assert headers == {}
        return FakeResponse()

    monkeypatch.setattr(
        "zotero_arxiv_daily.retriever.semantic_scholar_retriever.requests.get",
        fake_get,
    )
    monkeypatch.setattr(
        "zotero_arxiv_daily.retriever.semantic_scholar_retriever.time.sleep",
        lambda _: None,
    )

    retriever = SemanticScholarRetriever(config)
    raw_papers = retriever._retrieve_raw_papers()

    assert len(raw_papers) == 1
    assert raw_papers[0]["title"] == "Medical Image Segmentation Paper"


def test_semantic_scholar_multiple_queries_are_deduplicated(config, monkeypatch):
    _add_semantic_scholar_config(config)
    config.source.semantic_scholar.query = None
    config.source.semantic_scholar.queries = [
        "medical image segmentation",
        "semi supervised segmentation",
    ]

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": [
                    {
                        "paperId": "same-paper",
                        "title": "Duplicate Paper",
                        "abstract": "abstract",
                        "authors": [{"name": "A"}],
                        "year": 2025,
                        "venue": "Medical Image Analysis",
                        "publicationTypes": ["JournalArticle"],
                        "url": "https://example.com",
                    }
                ]
            }

    seen_queries = []

    def fake_get(url, params=None, headers=None, timeout=None):
        seen_queries.append(params["query"])
        return FakeResponse()

    monkeypatch.setattr(
        "zotero_arxiv_daily.retriever.semantic_scholar_retriever.requests.get",
        fake_get,
    )
    monkeypatch.setattr(
        "zotero_arxiv_daily.retriever.semantic_scholar_retriever.time.sleep",
        lambda _: None,
    )

    retriever = SemanticScholarRetriever(config)
    raw_papers = retriever._retrieve_raw_papers()

    assert seen_queries == [
        "medical image segmentation",
        "semi supervised segmentation",
    ]
    assert len(raw_papers) == 1


def test_semantic_scholar_uses_api_key_header(config, monkeypatch):
    _add_semantic_scholar_config(config)
    config.source.semantic_scholar.api_key = "test-semantic-scholar-key"

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"data": []}

    def fake_get(url, params=None, headers=None, timeout=None):
        assert headers == {"x-api-key": "test-semantic-scholar-key"}
        return FakeResponse()

    monkeypatch.setattr(
        "zotero_arxiv_daily.retriever.semantic_scholar_retriever.requests.get",
        fake_get,
    )
    monkeypatch.setattr(
        "zotero_arxiv_daily.retriever.semantic_scholar_retriever.time.sleep",
        lambda _: None,
    )

    retriever = SemanticScholarRetriever(config)
    assert retriever._retrieve_raw_papers() == []


def test_semantic_scholar_null_query_uses_default(config):
    _add_semantic_scholar_config(config)
    config.source.semantic_scholar.query = None

    retriever = SemanticScholarRetriever(config)

    assert "medical image segmentation" in retriever.query


def test_semantic_scholar_429_returns_empty_after_retries(config, monkeypatch):
    _add_semantic_scholar_config(config)

    class FakeRateLimitResponse:
        status_code = 429

        def raise_for_status(self):
            return None

    monkeypatch.setattr(
        "zotero_arxiv_daily.retriever.semantic_scholar_retriever.requests.get",
        lambda *args, **kwargs: FakeRateLimitResponse(),
    )
    monkeypatch.setattr(
        "zotero_arxiv_daily.retriever.semantic_scholar_retriever.time.sleep",
        lambda _: None,
    )

    retriever = SemanticScholarRetriever(config)
    raw_papers = retriever._retrieve_raw_papers()

    assert raw_papers == []
