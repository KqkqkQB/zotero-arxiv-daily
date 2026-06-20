from .protocol import Paper
import math


framework = """
<!DOCTYPE HTML>
<html>
<head>
  <style>
    .star-wrapper {
      font-size: 1.3em;
      line-height: 1;
      display: inline-flex;
      align-items: center;
    }
    .half-star {
      display: inline-block;
      width: 0.5em;
      overflow: hidden;
      white-space: nowrap;
      vertical-align: middle;
    }
    .full-star {
      vertical-align: middle;
    }
  </style>
</head>
<body>

<div>
    __CONTENT__
</div>

<br><br>
<div>
To unsubscribe, remove your email in your Github Action setting.
</div>

</body>
</html>
"""


def get_empty_html():
    block_template = """
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
  <tr>
    <td style="font-size: 20px; font-weight: bold; color: #333;">
        No Papers Today. Take a Rest!
    </td>
  </tr>
  </table>
  """
    return block_template


def get_block_html(
    title: str,
    authors: str,
    rate: str,
    tldr: str,
    pdf_url: str = None,
    paper_url: str = None,
    affiliations: str = None,
    metadata: str = None,
):
    """
    metadata 用来显示期刊/会议名、论文类型、年份、DOI 等信息。
    比如：
    Medical Image Analysis | JournalArticle | 2025 | DOI: xxx
    """

    if affiliations is None:
        affiliations = "Unknown Affiliation"

    if metadata is None:
        metadata = "Unknown Venue"

    if tldr is None:
        tldr = "No TLDR or abstract available."

    # 如果没有 paper_url，就优先用 pdf_url
    if not paper_url:
        paper_url = pdf_url

    # 标题可点击
    if paper_url:
        title_html = f'<a href="{paper_url}" style="color: #333; text-decoration: none;">{title}</a>'
    else:
        title_html = title

    # PDF 按钮
    if pdf_url:
        pdf_button = f"""
            <a href="{pdf_url}" style="display: inline-block; text-decoration: none; font-size: 14px; font-weight: bold; color: #fff; background-color: #d9534f; padding: 8px 16px; border-radius: 4px; margin-right: 8px;">PDF</a>
        """
    else:
        pdf_button = ""

    # Paper Page 按钮
    if paper_url:
        page_button = f"""
            <a href="{paper_url}" style="display: inline-block; text-decoration: none; font-size: 14px; font-weight: bold; color: #fff; background-color: #337ab7; padding: 8px 16px; border-radius: 4px;">Paper Page</a>
        """
    else:
        page_button = ""

    block_template = """
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
    <tr>
        <td style="font-size: 20px; font-weight: bold; color: #333;">
            {title_html}
        </td>
    </tr>

    <tr>
        <td style="font-size: 14px; color: #666; padding: 8px 0;">
            {authors}
            <br>
            <i>{affiliations}</i>
        </td>
    </tr>

    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>Venue/Type:</strong> {metadata}
        </td>
    </tr>

    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>Relevance:</strong> {rate}
        </td>
    </tr>

    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>TLDR:</strong> {tldr}
        </td>
    </tr>

    <tr>
        <td style="padding: 8px 0;">
            {pdf_button}
            {page_button}
        </td>
    </tr>
</table>
"""
    return block_template.format(
        title_html=title_html,
        authors=authors,
        affiliations=affiliations,
        metadata=metadata,
        rate=rate,
        tldr=tldr,
        pdf_button=pdf_button,
        page_button=page_button,
    )


def get_stars(score: float):
    full_star = '<span class="full-star">⭐</span>'
    half_star = '<span class="half-star">⭐</span>'
    low = 6
    high = 8
    if score <= low:
        return ''
    elif score >= high:
        return full_star * 5
    else:
        interval = (high - low) / 10
        star_num = math.ceil((score - low) / interval)
        full_star_num = int(star_num / 2)
        half_star_num = star_num - full_star_num * 2
        return '<div class="star-wrapper">' + full_star * full_star_num + half_star * half_star_num + '</div>'


def build_metadata(p: Paper) -> str:
    """
    把 Semantic Scholar / Crossref 等来源抓到的字段拼成一行。
    如果是 arXiv，也不会报错，因为使用 getattr 安全读取。
    """

    metadata_parts = []

    venue = getattr(p, "venue", None)
    if venue:
        metadata_parts.append(str(venue))

    publication_types = getattr(p, "publication_types", None)
    if publication_types:
        if isinstance(publication_types, list):
            metadata_parts.append(", ".join(publication_types))
        else:
            metadata_parts.append(str(publication_types))

    year = getattr(p, "year", None)
    if year:
        metadata_parts.append(str(year))

    publication_date = getattr(p, "publication_date", None)
    if publication_date:
        metadata_parts.append(str(publication_date))

    doi = getattr(p, "doi", None)
    if doi:
        metadata_parts.append(f"DOI: {doi}")

    if len(metadata_parts) == 0:
        source = getattr(p, "source", None)
        if source:
            metadata_parts.append(str(source))
        else:
            metadata_parts.append("Unknown Source")

    return " | ".join(metadata_parts)


def render_email(papers: list[Paper]) -> str:
    parts = []

    if len(papers) == 0:
        return framework.replace('__CONTENT__', get_empty_html())

    for p in papers:
        rate = round(p.score, 1) if p.score is not None else 'Unknown'

        author_list = [a for a in p.authors]
        num_authors = len(author_list)

        if num_authors <= 5:
            authors = ', '.join(author_list)
        else:
            authors = ', '.join(author_list[:3] + ['...'] + author_list[-2:])

        if not authors:
            authors = "Unknown Authors"

        if p.affiliations is not None:
            affiliations = p.affiliations[:5]
            affiliations = ', '.join(affiliations)
            if len(p.affiliations) > 5:
                affiliations += ', ...'
        else:
            affiliations = 'Unknown Affiliation'

        metadata = build_metadata(p)

        paper_url = getattr(p, "url", None)
        pdf_url = getattr(p, "pdf_url", None)

        parts.append(
            get_block_html(
                title=p.title,
                authors=authors,
                rate=rate,
                tldr=p.tldr,
                pdf_url=pdf_url,
                paper_url=paper_url,
                affiliations=affiliations,
                metadata=metadata,
            )
        )

    content = '<br>' + '</br><br>'.join(parts) + '</br>'
    return framework.replace('__CONTENT__', content)