"""
Threads (by Meta) content source module.
Scrapes public Threads posts using Playwright headless browser.
"""

import json
import re
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from rich.console import Console

from utils import settings
from utils.console import print_step, print_substep
from utils.voice import sanitize_text

console = Console()


def get_threads_posts(POST_URL: str = None) -> dict:
    """
    Scrapes Threads posts and returns content in the same format as Reddit module.
    
    Can work in two modes:
    1. Specific URL mode: scrape a specific Threads post URL
    2. Search mode: search for threads by keyword/topic
    
    Returns:
        dict: Content object compatible with the video creation pipeline
    """
    print_step("Getting Threads content...")
    
    content = {}
    threads_config = settings.config.get("threads", {})
    
    specific_url = POST_URL or threads_config.get("thread", {}).get("post_url", "")
    search_query = threads_config.get("thread", {}).get("search_query", "")
    max_comments = int(threads_config.get("thread", {}).get("max_comments", 10))
    
    with sync_playwright() as p:
        print_substep("Launching browser for Threads...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 430, "height": 932},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            locale=settings.config.get("reddit", {}).get("thread", {}).get("post_lang", "") or "en-US",
        )
        page = context.new_page()
        
        if specific_url:
            content = _scrape_specific_thread(page, specific_url, max_comments)
        elif search_query:
            content = _scrape_search_threads(page, search_query, max_comments)
        else:
            # Default: scrape trending/popular threads
            content = _scrape_trending_threads(page, max_comments)
        
        browser.close()
    
    if not content or not content.get("thread_title"):
        print_substep("Could not fetch Threads content. Falling back to manual input.", style="bold red")
        content = _manual_input_mode()
    
    print_substep("Threads content retrieved successfully!", style="bold green")
    return content


def _scrape_specific_thread(page, url: str, max_comments: int) -> dict:
    """Scrape a specific Threads post by URL."""
    print_substep(f"Scraping thread: {url}")
    content = {
        "thread_url": url,
        "thread_title": "",
        "thread_id": "",
        "is_nsfw": False,
        "comments": [],
    }
    
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        
        # Try to extract thread content
        # Threads uses dynamic class names, so we use multiple selectors
        thread_id = _extract_thread_id(url)
        content["thread_id"] = thread_id or str(uuid.uuid4())[:12]
        
        # Get main post text
        post_text = _extract_post_text(page)
        if post_text:
            content["thread_title"] = post_text[:200]  # Title is first 200 chars
            if len(post_text) > 200:
                content["thread_post"] = post_text
        
        # Get author name
        author = _extract_author(page)
        if author:
            content["thread_title"] = f"{author}: {content['thread_title']}"
        
        # Get replies/comments
        replies = _extract_replies(page, max_comments)
        content["comments"] = replies
        
    except PlaywrightTimeout:
        print_substep("Timeout loading Threads page. Using manual input.", style="bold yellow")
    except Exception as e:
        print_substep(f"Error scraping thread: {str(e)}", style="bold red")
    
    return content


def _scrape_search_threads(page, query: str, max_comments: int) -> dict:
    """Search Threads for content matching a query."""
    print_substep(f"Searching Threads for: {query}")
    
    search_url = f"https://www.threads.net/search?q={query}&serp_type=default"
    
    try:
        page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        
        # Find first good post from search results
        posts = page.locator('[data-pressable-container="true"]').all()
        
        if posts:
            # Click on the first post to get full content
            first_post_text = ""
            for post in posts[:5]:
                text = post.inner_text()
                if len(text) > 50:  # Skip very short posts
                    first_post_text = text
                    try:
                        post.click()
                        page.wait_for_timeout(3000)
                    except:
                        pass
                    break
            
            if first_post_text:
                return _scrape_specific_thread(page, page.url, max_comments)
        
    except Exception as e:
        print_substep(f"Search failed: {str(e)}", style="bold red")
    
    return {}


def _scrape_trending_threads(page, max_comments: int) -> dict:
    """Try to get trending/popular content from Threads."""
    print_substep("Looking for trending Threads content...")
    
    try:
        page.goto("https://www.threads.net/", timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        
        # Try to find posts on the feed
        posts = page.locator('article, [role="article"]').all()
        
        best_post = None
        best_length = 0
        
        for post in posts[:10]:
            try:
                text = post.inner_text()
                if len(text) > best_length and len(text) > 100:
                    best_length = len(text)
                    best_post = post
            except:
                continue
        
        if best_post:
            # Try to click and get the full thread
            try:
                best_post.click()
                page.wait_for_timeout(3000)
                return _scrape_specific_thread(page, page.url, max_comments)
            except:
                # If click fails, extract text directly
                text = best_post.inner_text()
                return {
                    "thread_url": "https://www.threads.net/",
                    "thread_title": text[:200],
                    "thread_id": str(uuid.uuid4())[:12],
                    "is_nsfw": False,
                    "comments": [],
                    "thread_post": text if len(text) > 200 else "",
                }
    except Exception as e:
        print_substep(f"Error loading trending threads: {str(e)}", style="bold red")
    
    return {}


def _extract_thread_id(url: str) -> str:
    """Extract thread ID from Threads URL."""
    # URLs like: https://www.threads.net/@user/post/ABC123
    match = re.search(r'/post/([A-Za-z0-9_-]+)', url)
    if match:
        return f"threads_{match.group(1)}"
    # Fallback
    return f"threads_{uuid.uuid4().hex[:10]}"


def _extract_post_text(page) -> str:
    """Extract main post text from a Threads page."""
    selectors = [
        'div[data-text="true"]',
        'article span',
        '[class*="BodyTextContainer"] span',
        'main span[dir="auto"]',
    ]
    
    for selector in selectors:
        try:
            elements = page.locator(selector).all()
            texts = []
            for el in elements[:5]:  # First 5 matching elements
                t = el.inner_text().strip()
                if t and len(t) > 10:
                    texts.append(t)
            if texts:
                return " ".join(texts[:3])  # Combine first few text blocks
        except:
            continue
    
    # Fallback: try getting all visible text
    try:
        body_text = page.locator('main').inner_text()
        lines = [l.strip() for l in body_text.split('\n') if len(l.strip()) > 20]
        if lines:
            return lines[0]
    except:
        pass
    
    return ""


def _extract_author(page) -> str:
    """Extract the post author username."""
    try:
        # Try multiple selectors for username
        selectors = [
            'a[href*="/@"] span',
            'header a span',
            '[class*="UserName"]',
        ]
        for sel in selectors:
            el = page.locator(sel).first
            if el.is_visible():
                text = el.inner_text().strip()
                if text and text.startswith("@") or len(text) < 30:
                    return text
    except:
        pass
    return ""


def _extract_replies(page, max_replies: int) -> list:
    """Extract replies/comments from a Threads post."""
    replies = []
    
    try:
        # Scroll down to load replies
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        page.wait_for_timeout(2000)
        
        # Try to find reply elements
        reply_elements = page.locator('div[data-text="true"]').all()
        
        seen_texts = set()
        for i, el in enumerate(reply_elements[1:]):  # Skip first (main post)
            if i >= max_replies:
                break
            try:
                text = el.inner_text().strip()
                if text and len(text) > 5 and text not in seen_texts:
                    seen_texts.add(text)
                    sanitised = sanitize_text(text)
                    if sanitised and sanitised.strip():
                        replies.append({
                            "comment_body": text,
                            "comment_url": "",
                            "comment_id": f"threads_reply_{i}",
                        })
            except:
                continue
    except Exception as e:
        print_substep(f"Error extracting replies: {str(e)}", style="bold yellow")
    
    return replies


def _manual_input_mode() -> dict:
    """Fallback: let user manually input content."""
    print_step("Manual Input Mode - Enter your content:")
    
    title = input("Enter the title/question: ").strip()
    if not title:
        title = "Interesting story from the internet"
    
    print("Enter comments/replies (one per line, empty line to finish):")
    comments = []
    while True:
        line = input("> ").strip()
        if not line:
            break
        comments.append({
            "comment_body": line,
            "comment_url": "",
            "comment_id": f"manual_{len(comments)}",
        })
    
    thread_id = f"manual_{uuid.uuid4().hex[:10]}"
    
    content = {
        "thread_url": "",
        "thread_title": title,
        "thread_id": thread_id,
        "is_nsfw": False,
        "comments": comments,
    }
    
    # Check if user wants story mode
    if not comments:
        post_text = input("Enter story/post body text (or press Enter to skip): ").strip()
        if post_text:
            content["thread_post"] = post_text
    
    return content
