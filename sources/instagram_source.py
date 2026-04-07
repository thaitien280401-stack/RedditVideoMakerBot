"""
Instagram content source module.
Scrapes public Instagram posts/reels captions and comments using Playwright.
No Instagram API or login required for public posts.
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


def get_instagram_posts(POST_URL: str = None) -> dict:
    """
    Scrapes Instagram post captions and comments.
    Works with public posts/reels.
    
    Returns:
        dict: Content object compatible with the video creation pipeline
    """
    print_step("Getting Instagram content...")
    
    content = {}
    ig_config = settings.config.get("instagram", {})
    
    specific_url = POST_URL or ig_config.get("thread", {}).get("post_url", "")
    
    if not specific_url:
        print_substep("No Instagram URL provided. Please provide a post URL.", style="bold red")
        specific_url = input("Enter Instagram post/reel URL: ").strip()
    
    if not specific_url:
        print_substep("No URL provided. Falling back to manual input.", style="bold yellow")
        return _manual_input_mode()
    
    with sync_playwright() as p:
        print_substep("Launching browser for Instagram...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 430, "height": 932},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            locale=settings.config.get("reddit", {}).get("thread", {}).get("post_lang", "") or "en-US",
        )
        page = context.new_page()
        
        content = _scrape_instagram_post(page, specific_url)
        
        browser.close()
    
    if not content or not content.get("thread_title"):
        print_substep("Could not fetch Instagram content. Falling back to manual input.", style="bold red")
        content = _manual_input_mode()
    
    print_substep("Instagram content retrieved successfully!", style="bold green")
    return content


def _scrape_instagram_post(page, url: str) -> dict:
    """Scrape an Instagram post/reel for caption and comments."""
    print_substep(f"Scraping Instagram: {url}")
    
    content = {
        "thread_url": url,
        "thread_title": "",
        "thread_id": "",
        "is_nsfw": False,
        "comments": [],
    }
    
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        
        # Handle login popups - dismiss them
        _dismiss_login_popup(page)
        
        # Extract post ID
        post_id = _extract_post_id(url)
        content["thread_id"] = post_id
        
        # Extract caption (main post text)
        caption = _extract_caption(page)
        if caption:
            content["thread_title"] = caption[:200]
            if len(caption) > 200:
                content["thread_post"] = caption
        
        # Extract author
        author = _extract_author(page)
        if author and content["thread_title"]:
            content["thread_title"] = f"@{author}: {content['thread_title']}"
        
        # Extract comments
        ig_config = settings.config.get("instagram", {})
        max_comments = int(ig_config.get("thread", {}).get("max_comments", 10))
        comments = _extract_comments(page, max_comments)
        content["comments"] = comments
        
    except PlaywrightTimeout:
        print_substep("Timeout loading Instagram page.", style="bold yellow")
    except Exception as e:
        print_substep(f"Error scraping Instagram: {str(e)}", style="bold red")
    
    return content


def _dismiss_login_popup(page):
    """Try to dismiss Instagram login popup."""
    try:
        # Close "Log in" or "Not Now" popups
        close_btns = page.locator('button:has-text("Not Now"), button:has-text("Decline"), [aria-label="Close"]').all()
        for btn in close_btns:
            try:
                if btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(500)
            except:
                pass
    except:
        pass


def _extract_post_id(url: str) -> str:
    """Extract post ID from Instagram URL."""
    # URLs: https://www.instagram.com/p/ABC123/ or /reel/ABC123/
    match = re.search(r'/(p|reel|reels)/([A-Za-z0-9_-]+)', url)
    if match:
        return f"ig_{match.group(2)}"
    return f"ig_{uuid.uuid4().hex[:10]}"


def _extract_caption(page) -> str:
    """Extract post caption."""
    selectors = [
        'article span[dir="auto"]',
        'div[class*="Caption"] span',
        'ul li span[dir="auto"]',
        'article h1',
        'meta[property="og:description"]',
    ]
    
    for selector in selectors:
        try:
            if selector.startswith('meta'):
                el = page.locator(selector).first
                desc = el.get_attribute('content')
                if desc and len(desc) > 10:
                    return desc
            else:
                elements = page.locator(selector).all()
                for el in elements[:5]:
                    text = el.inner_text().strip()
                    if text and len(text) > 20:
                        # Clean up hashtags at the end
                        return text
        except:
            continue
    
    # Fallback: try meta description
    try:
        desc = page.locator('meta[name="description"]').first.get_attribute("content")
        if desc:
            return desc
    except:
        pass
    
    return ""


def _extract_author(page) -> str:
    """Extract post author."""
    try:
        # Try og:title or header username
        selectors = [
            'header a[href*="/"] span',
            'a[class*="ProfileLink"] span',
            'meta[property="og:title"]',
        ]
        for sel in selectors:
            try:
                if sel.startswith('meta'):
                    el = page.locator(sel).first
                    title = el.get_attribute('content')
                    if title:
                        # "username on Instagram: ..."
                        match = re.match(r'^(.+?) on Instagram', title)
                        if match:
                            return match.group(1).strip()
                else:
                    el = page.locator(sel).first
                    if el.is_visible():
                        text = el.inner_text().strip()
                        if text and len(text) < 30:
                            return text
            except:
                continue
    except:
        pass
    return ""


def _extract_comments(page, max_comments: int) -> list:
    """Extract comments from Instagram post."""
    comments = []
    
    try:
        # Scroll to load comments
        page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
        page.wait_for_timeout(2000)
        
        # Try to find comment elements
        comment_selectors = [
            'ul ul li span[dir="auto"]',
            'div[class*="Comment"] span[dir="auto"]',
            'ul > li span',
        ]
        
        seen_texts = set()
        for selector in comment_selectors:
            try:
                elements = page.locator(selector).all()
                for i, el in enumerate(elements):
                    if len(comments) >= max_comments:
                        break
                    text = el.inner_text().strip()
                    if (text and len(text) > 5 and text not in seen_texts 
                            and not text.startswith("View") and not text.startswith("Load")):
                        seen_texts.add(text)
                        sanitised = sanitize_text(text)
                        if sanitised and sanitised.strip():
                            comments.append({
                                "comment_body": text,
                                "comment_url": "",
                                "comment_id": f"ig_comment_{len(comments)}",
                            })
                if comments:
                    break
            except:
                continue
    except Exception as e:
        print_substep(f"Error extracting comments: {str(e)}", style="bold yellow")
    
    return comments


def _manual_input_mode() -> dict:
    """Fallback mode for manual content input."""
    print_step("Manual Input Mode - Enter your content:")
    
    title = input("Enter the title/caption: ").strip()
    if not title:
        title = "Interesting story from Instagram"
    
    print("Enter comments (one per line, empty line to finish):")
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
    
    thread_id = f"ig_manual_{uuid.uuid4().hex[:10]}"
    
    content = {
        "thread_url": "",
        "thread_title": title,
        "thread_id": thread_id,
        "is_nsfw": False,
        "comments": comments,
    }
    
    if not comments:
        post_text = input("Enter story/post body text (or Enter to skip): ").strip()
        if post_text:
            content["thread_post"] = post_text
    
    return content
