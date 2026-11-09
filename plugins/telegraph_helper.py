import aiohttp
import asyncio
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

TELEGRAPH_API_URL = "https://api.telegra.ph"
_TELEGRAPH_TOKEN = None

async def get_or_create_telegraph_token() -> str:
    """Retrieves cached Telegraph access token or creates a new one via Telegraph API."""
    global _TELEGRAPH_TOKEN
    from database import db
    
    if not _TELEGRAPH_TOKEN:
        _TELEGRAPH_TOKEN = await db.get_telegraph_token()
        
    if _TELEGRAPH_TOKEN:
        return _TELEGRAPH_TOKEN

    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "short_name": "SkinetVerse",
                "author_name": "Skinet Verse Course Engine"
            }
            async with session.get(f"{TELEGRAPH_API_URL}/createAccount", params=payload, timeout=10) as resp:
                data = await resp.json()
                if data.get("ok"):
                    _TELEGRAPH_TOKEN = data["result"]["access_token"]
                    await db.save_telegraph_token(_TELEGRAPH_TOKEN, payload["author_name"])
                    return _TELEGRAPH_TOKEN
    except Exception as e:
        logger.warning(f"Failed to create Telegraph account: {e}")
    return _TELEGRAPH_TOKEN

async def create_telegraph_syllabus(title: str, from_title: str, course_items: list, missing_lectures: list = None, header_banner: str = None, footer_banner: str = None) -> str:
    """
    Creates an interactive Telegraph webpage with the full course syllabus,
    hyperlinked lecture items, gap reports, and branding.
    Returns the public Telegraph URL (e.g., https://telegra.ph/Course-Syllabus-09-18).
    """
    token = await get_or_create_telegraph_token()
    if not token:
        logger.warning("No Telegraph access token available")
        return None

    try:
        nodes = []

        # 1. Header Banner
        if header_banner:
            clean_hdr = re.sub(r'<[^>]+>', '', header_banner).strip()
            if clean_hdr:
                nodes.append({"tag": "blockquote", "children": [clean_hdr]})
                nodes.append({"tag": "hr"})

        # 2. Metadata details
        nodes.append({"tag": "h3", "children": [f"📚 {title}"]})
        meta_info = f"🎯 Source: {from_title} | 📦 Total Lectures: {len(course_items)} | 📅 {datetime.now().strftime('%d-%b-%Y')}"
        nodes.append({"tag": "p", "children": [{"tag": "em", "children": [meta_info]}]})

        # 3. Completeness Card
        if missing_lectures:
            gap_str = ", ".join(f"[{x:02d}]" for x in missing_lectures[:20])
            if len(missing_lectures) > 20:
                gap_str += f" (+{len(missing_lectures) - 20} more)"
            nodes.append({"tag": "p", "children": [
                {"tag": "strong", "children": ["⚠️ Missing Lecture Gaps Detected: "]},
                gap_str
            ]})
        else:
            nodes.append({"tag": "p", "children": [
                {"tag": "strong", "children": ["🎉 Course Completeness: "]},
                "100% Complete (No gaps detected)"
            ]})

        nodes.append({"tag": "hr"})

        # 4. Lecture Index List
        for it in course_items:
            num_str = f"[{it['num']:02d}]"
            lec_title = it.get('title', f"Lecture {it['num']:02d}")
            link = it.get('link')
            
            p_children = []
            p_children.append({"tag": "strong", "children": [f"{num_str} "]})
            if link:
                p_children.append({"tag": "a", "attrs": {"href": link}, "children": [lec_title]})
            else:
                p_children.append(lec_title)
            
            nodes.append({"tag": "p", "children": p_children})

        # 5. Footer Branding
        nodes.append({"tag": "hr"})
        if footer_banner:
            clean_ftr = re.sub(r'<[^>]+>', '', footer_banner).strip()
            if clean_ftr:
                nodes.append({"tag": "blockquote", "children": [clean_ftr]})
        else:
            nodes.append({"tag": "p", "children": [
                {"tag": "em", "children": ["⚡ Published by Skinet Verse Course Seller Engine"]}
            ]})

        # Send to Telegraph API
        async with aiohttp.ClientSession() as session:
            req_data = {
                "access_token": token,
                "title": f"🎓 {title[:60]}",
                "author_name": "Skinet Verse",
                "content": nodes,
                "return_content": False
            }
            async with session.post(f"{TELEGRAPH_API_URL}/createPage", json=req_data, timeout=15) as resp:
                res = await resp.json()
                if res.get("ok"):
                    url = res["result"].get("url")
                    return url
                else:
                    logger.warning(f"Telegraph createPage failed: {res.get('error')}")
    except Exception as e:
        logger.error(f"Error publishing to Telegraph: {e}")
    return None
