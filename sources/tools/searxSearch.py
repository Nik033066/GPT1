import requests
from bs4 import BeautifulSoup
import os

if __name__ == "__main__": # if running as a script for individual testing
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sources.tools.tools import Tools

class searxSearch(Tools):
    def __init__(self, base_url: str = None):
        """
        A tool for searching a SearxNG instance and extracting URLs and titles.
        """
        super().__init__()
        self.tag = "web_search"
        self.name = "searxSearch"
        self.description = "A tool for searching a SearxNG for web search"
        self.base_url = os.getenv("SEARXNG_BASE_URL")  # Requires a SearxNG base URL
        self.user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        self.paywall_keywords = [
            "Member-only", "access denied", "restricted content", "404", "this page is not working"
        ]
        if not self.base_url:
            raise ValueError("SearxNG base URL must be provided either as an argument or via the SEARXNG_BASE_URL environment variable.")

    def link_valid(self, link):
        """check if a link is valid."""
        # TODO find a better way
        if not link.startswith("http"):
            return "Status: Invalid URL"
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            response = requests.get(link, headers=headers, timeout=5)
            status = response.status_code
            if status == 200:
                content = response.text.lower()
                if any(keyword in content for keyword in self.paywall_keywords):
                    return "Status: Possible Paywall"
                return "Status: OK"
            elif status == 404:
                return "Status: 404 Not Found"
            elif status == 403:
                return "Status: 403 Forbidden"
            else:
                return f"Status: {status} {response.reason}"
        except requests.exceptions.RequestException as e:
            return f"Error: {str(e)}"

    def check_all_links(self, links):
        """Check all links, one by one."""
        # TODO Make it asyncromous or smth
        statuses = []
        for i, link in enumerate(links):
            status = self.link_valid(link)
            statuses.append(status)
        return statuses
    
    def execute(self, blocks: list, safety: bool = False) -> str:
        """Executes a search query against a SearxNG instance using POST and extracts URLs and titles."""
        if not blocks:
            return "Error: No search query provided."

        query = blocks[0].strip()
        if not query:
            return "Error: Empty search query provided."

        search_url = f"{self.base_url}/search"
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Pragma': 'no-cache',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': self.user_agent
        }
        data = f"q={query}&categories=general&language=auto&time_range=&safesearch=0&theme=simple".encode('utf-8')
        try:
            response = requests.post(search_url, headers=headers, data=data, verify=False)
            response.raise_for_status()
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            results = []
            for article in soup.find_all('article', class_='result'):
                url_header = article.find('a', class_='url_header')
                if url_header:
                    url = url_header['href']
                    title = article.find('h3').text.strip() if article.find('h3') else "No Title"
                    description = article.find('p', class_='content').text.strip() if article.find('p', class_='content') else "No Description"
                    results.append(f"Title:{title}\nSnippet:{description}\nLink:{url}")
            if len(results) == 0:
                return "No search results, web search failed."
            return "\n\n".join(results)  # Return results as a single string, separated by newlines
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if "403" in error_msg:
                return f"Error: SearxNG instance returned 403 Forbidden. This usually means:\n" \
                       f"1. The SearxNG instance is blocking requests (rate limiting/bot protection)\n" \
                       f"2. The instance requires authentication\n" \
                       f"3. The instance is misconfigured\n\n" \
                       f"Solutions:\n" \
                       f"1. Use the local SearxNG instance: run './start_with_searxng.sh'\n" \
                       f"2. Find another public SearxNG instance\n" \
                       f"3. Set up your own SearxNG instance\n\n" \
                       f"Current URL: {self.base_url}"
            elif "Connection refused" in error_msg or "ConnectionError" in error_msg:
                return f"Error: Cannot connect to SearxNG at {self.base_url}.\n" \
                       f"Make sure SearxNG is running. Try:\n" \
                       f"1. Run './start_with_searxng.sh' to start with local SearxNG\n" \
                       f"2. Check if Docker is running: 'docker ps'\n" \
                       f"3. Check the SearxNG URL in your .env file"
            else:
                return f"Error: SearxNG search failed - {error_msg}\n" \
                       f"Current SearxNG URL: {self.base_url}\n" \
                       f"Try running './start_with_searxng.sh' for local setup"

    def execution_failure_check(self, output: str) -> bool:
        """
        Checks if the execution failed based on the output.
        """
        return "Error" in output

    def interpreter_feedback(self, output: str) -> str:
        """
        Feedback of web search to agent.
        """
        if self.execution_failure_check(output):
            return f"Web search failed: {output}"
        return f"Web search result:\n{output}"

if __name__ == "__main__":
    search_tool = searxSearch(base_url="http://127.0.0.1:8080")
    result = search_tool.execute(["are dog better than cat?"])
    print(result)
