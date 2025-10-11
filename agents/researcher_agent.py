import logging
import requests
from urllib.parse import urlparse
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError as e:
    TRAFILATURA_AVAILABLE = False
    logger.warning(f"Trafilatura not available: {e}")

class ResearcherAgent(BaseAgent):
    
    def __init__(self):
        super().__init__(
            name="ResearcherAgent",
            description="Specialized in web scraping and document summarization."
        )
    
    def get_commands(self):
        return {
            "scrape": {
                "description": "Extract text content from a website",
                "usage": "scrape <url>",
                "examples": [
                    "scrape https://news.ycombinator.com",
                    "scrape https://en.wikipedia.org/wiki/Python_(programming_language)"
                ]
            },
            "summarize": {
                "description": "Generate a brief summary of a text",
                "usage": "summarize <text_or_url>",
                "examples": [
                    "summarize https://news.ycombinator.com",
                    "summarize 'Long text that needs to be summarized...'"
                ]
            },
            "extract-links": {
                "description": "Extract links from a webpage",
                "usage": "extract-links <url>",
                "examples": [
                    "extract-links https://news.ycombinator.com"
                ]
            },
            "analyze": {
                "description": "Analyze text content (word count, readability, etc.)",
                "usage": "analyze <text_or_url>",
                "examples": [
                    "analyze https://en.wikipedia.org/wiki/Python_(programming_language)",
                    "analyze 'This is a sample text to analyze...'"
                ]
            }
        }
    
    def execute(self, command, args):
        try:
            if not args and command != "help":
                return f"Error: Missing arguments for '{command}' command. Use 'help researcher' for usage information."
            
            if command == "scrape":
                url = args[0]
                return self._scrape_website(url)
                
            elif command == "summarize":
                text_or_url = args[0]
                return self._summarize_text(text_or_url)
                
            elif command == "extract-links":
                url = args[0]
                return self._extract_links(url)
                
            elif command == "analyze":
                text_or_url = args[0]
                return self._analyze_text(text_or_url)
                
            else:
                return f"Unknown command: '{command}'"
                
        except Exception as e:
            logger.error(f"Error in ResearcherAgent: {str(e)}")
            return f"Error executing command: {str(e)}"
    
    def _is_url(self, text):
        try:
            result = urlparse(text)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _scrape_website(self, url):
        try:
            logger.debug(f"Scraping website: {url}")
            
            if not self._is_url(url):
                return f"Error: '{url}' is not a valid URL."
            
            downloaded = trafilatura.fetch_url(url)
            if downloaded is None:
                return f"Error: Could not download content from {url}"
            
            text = trafilatura.extract(downloaded)
            if text is None or text.strip() == "":
                return f"Error: Could not extract content from {url}"
            
            if len(text) > 2000:
                text = text[:2000] + "...\n[Content truncated due to size]"
            
            return f"Content extracted from {url}:\n\n{text}"
            
        except Exception as e:
            logger.error(f"Error scraping website {url}: {str(e)}")
            return f"Error scraping website: {str(e)}"
    
    def _summarize_text(self, text_or_url):
        try:
            logger.debug(f"Summarizing: {text_or_url[:50]}...")
            
            if self._is_url(text_or_url):
                content = self._scrape_website(text_or_url)
                text = content.split('\n\n', 1)[1] if '\n\n' in content else content
            else:
                text = text_or_url
            
            sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
            
            if len(sentences) <= 3:
                return f"Summary:\n\n{text}"
            
            summary_sentences = [
                sentences[0],
                sentences[len(sentences) // 2],
                sentences[-1]
            ]
            
            summary = '. '.join(summary_sentences) + '.'
            
            return f"Summary:\n\n{summary}"
            
        except Exception as e:
            logger.error(f"Error summarizing text: {str(e)}")
            return f"Error summarizing text: {str(e)}"
    
    def _extract_links(self, url):
        try:
            logger.debug(f"Extracting links from: {url}")
            
            if not self._is_url(url):
                return f"Error: '{url}' is not a valid URL."
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            links = trafilatura.extract_metadata(response.text, url=url)
            
            if links and hasattr(links, 'links') and links.links:
                result = f"Links extracted from {url}:\n\n"
                for i, link in enumerate(links.links[:20], 1):
                    result += f"{i}. {link}\n"
                
                if len(links.links) > 20:
                    result += f"\n... and {len(links.links) - 20} more links."
                
                return result
            else:
                import re
                link_pattern = re.compile(r'href=[\'"]?([^\'" >]+)')
                found_links = link_pattern.findall(response.text)
                
                if found_links:
                    clean_links = []
                    for link in found_links:
                        if link.startswith('/'):
                            parsed_base = urlparse(url)
                            link = f"{parsed_base.scheme}://{parsed_base.netloc}{link}"
                        if not link.startswith(('#', 'javascript:', 'mailto:')):
                            clean_links.append(link)
                    
                    result = f"Links extracted from {url}:\n\n"
                    for i, link in enumerate(clean_links[:20], 1):
                        result += f"{i}. {link}\n"
                    
                    if len(clean_links) > 20:
                        result += f"\n... and {len(clean_links) - 20} more links."
                    
                    return result
                else:
                    return f"No links found on {url}"
            
        except Exception as e:
            logger.error(f"Error extracting links from {url}: {str(e)}")
            return f"Error extracting links: {str(e)}"
    
    def _analyze_text(self, text_or_url):
        try:
            logger.debug(f"Analyzing: {text_or_url[:50]}...")
            
            if self._is_url(text_or_url):
                content = self._scrape_website(text_or_url)
                text = content.split('\n\n', 1)[1] if '\n\n' in content else content
            else:
                text = text_or_url
            
            words = text.split()
            word_count = len(words)
            
            char_count = len(text)
            char_count_no_spaces = len(text.replace(" ", ""))
            
            sentences = [s for s in text.replace('\n', ' ').split('.') if s.strip()]
            sentence_count = len(sentences)
            
            avg_word_length = sum(len(word) for word in words) / max(word_count, 1)
            
            avg_sentence_length = word_count / max(sentence_count, 1)
            
            readability_score = 0.39 * (word_count / max(sentence_count, 1)) + 11.8 * (char_count_no_spaces / max(word_count, 1)) - 15.59
            
            readability_level = min(10, max(1, int(readability_score / 10)))
            readability_desc = ["Very Easy", "Easy", "Fairly Easy", "Standard", "Fairly Difficult", 
                               "Difficult", "Very Difficult", "Extremely Difficult", "Academic", "Technical"][readability_level-1]
            
            from collections import Counter
            stop_words = {"the", "to", "and", "a", "in", "it", "is", "of", "that", "for", 
                         "on", "with", "as", "was", "be", "this", "by", "are", "you", "from"}
            filtered_words = [word.lower() for word in words if word.lower() not in stop_words and len(word) > 2]
            common_words = Counter(filtered_words).most_common(5)
            
            result = "Text Analysis:\n\n"
            result += f"Word Count: {word_count}\n"
            result += f"Character Count: {char_count} (without spaces: {char_count_no_spaces})\n"
            result += f"Sentence Count: {sentence_count}\n"
            result += f"Average Word Length: {avg_word_length:.2f} characters\n"
            result += f"Average Sentence Length: {avg_sentence_length:.2f} words\n"
            result += f"Readability Level: {readability_level}/10 ({readability_desc})\n\n"
            
            if common_words:
                result += "Most Common Words:\n"
                for word, count in common_words:
                    result += f"- {word}: {count} occurrences\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing text: {str(e)}")
            return f"Error analyzing text: {str(e)}"
