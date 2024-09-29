import json
import re
import requests


def fetch_articles(api_url):
    """Fetch articles from the given API URL."""
    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an error for bad responses
        return response.json().get("articles", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching articles: {e}")
        return []


def clean_html_content(html_content):
    """Remove HTML tags from the content."""
    return re.sub(r"<.*?>", "", html_content) if html_content else ""


def format_links_to_markdown(content):
    """Convert HTML links to Markdown format."""
    return re.sub(r'<a href="(.*?)">(.*?)</a>', r"[\2](\1)", content) if content else ""


def sanitize_text(text):
    """Remove non-ASCII characters from the text."""
    return "".join(char for char in text if ord(char) < 128) if text else ""


def extract_and_clean_article(article):
    """Extract and clean the article body."""
    raw_body = article.get("body", "")
    formatted_body = format_links_to_markdown(raw_body)
    clean_body = clean_html_content(formatted_body).strip()
    clean_body = sanitize_text(clean_body).replace("\n", " ").replace("\r", "")
    return clean_body if clean_body else ""


# API URL to fetch articles
api_url = "https://stackuphelpcentre.zendesk.com/api/v2/help_center/en-us/articles?per_page=100"

# Fetch articles from the API
articles = fetch_articles(api_url)

# Clean articles and prepare output
cleaned_articles = []
for article in articles:
    title = article.get("title", "Untitled")
    url = article.get("html_url", "No URL")
    cleaned_body = extract_and_clean_article(article)
    # cleaned_articles.append(f"Title: {title}\nURL: {url}\nBody: {cleaned_body}\n")
    if cleaned_body:
        cleaned_articles.append(f"{cleaned_body}\n")

# Write cleaned articles to a text file
with open("cleaned_data.txt", "w", encoding="utf-8") as output_file:
    for entry in cleaned_articles:
        output_file.write(entry + "\n\n")
