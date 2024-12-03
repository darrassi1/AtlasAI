"""
Vector Search for Code Docs + Docs Loading
"""
import requests

from bs4 import BeautifulSoup


def scrape_website(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for failed requests
        return clean_and_preprocess_text(response.content)
    except requests.exceptions.RequestException as e:
        print(f"Error scraping website: {e}")
        return ""


def clean_and_preprocess_text(text):
    """
    Clean and preprocess HTML text by extracting code snippets.

    Args:
        text (str): HTML text to be processed.

    Returns:
        str: Cleaned code snippets extracted from the HTML text.
    """
    try:
        # Parse HTML content using 'lxml' parser for better performance
        soup = BeautifulSoup(text, 'lxml')

        # Find all code tags and extract text from them
        code_tags = soup.find_all(['pre', 'code'])


        # Extract code text and join them without any separator, removing whitespace and newlines
        code_text = ''.join(tag.get_text(separator='').strip() for tag in code_tags)

        # Remove any remaining whitespace and newlines
        cleaned_text = code_text.replace(' ', '').replace('\n', '')

    except Exception as e:
        # Handle any exceptions that may occur during processing
        print(f"Error cleaning and preprocessing text: {e}")
        cleaned_text = ""

    return cleaned_text
