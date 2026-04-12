"""
High-Performance Parallel Profile Scraping (Anonymous + Rotating IP)
====================================================================

This example demonstrates how to configure `instaharvest_v2` for highly
aggressive parallel scraping using Rotating IPv4/IPv6 Residential Proxies.

Instagram blocks Anonymous GraphQL requests with HTTP 400 when IPs rotate rapidly.
To bypass this limitation, we use the `get_user_feed_mobile` method. This hooks directly
into the Mobile API, which is naturally resilient to IP rotation, allowing seamless
unlimited pagination through thousands of posts without login.

Architecture Best Practices:
1. ProxyType Auto-Detection -> pm.detect_proxy_type() correctly disables static chain-fallbacks.
2. Max Concurrency limits to prevent "503 Tunnel Failed" errors from proxy providers.
3. Mobile API Extraction -> bypasses GraphQL "400 Bad Request" blocks.
"""
import asyncio
import time
from instaharvest_v2.proxy_manager import ProxyManager
from instaharvest_v2.async_anon_client import AsyncAnonClient

# WARNING: Replace with your actual proxy.
PROXY_URL = "http://username:password@res.proxy-seller.com:10000"

TARGETS = ["cristiano", "leomessi", "therock", "selenagomez", "kyliejenner"]
MAX_POSTS_PER_TARGET = 60

async def scrape_target(client: AsyncAnonClient, username: str) -> dict:
    start_time = time.time()
    
    # 1. Start fetching profile info safely (WEB_API)
    profile = await client.get_profile_chain(username)
    if not profile or not profile.get("id"):
        return {"username": username, "error": "Not Found or Blocked"}
        
    user_id = profile["id"]
    posts = []
    has_next = True
    next_max_id = None
    
    # 2. Seamlessly paginate using Mobile API (Bypasses GraphQL blocks)
    while has_next and len(posts) < MAX_POSTS_PER_TARGET:
        feed = await client.get_user_feed_mobile(str(user_id), count=12, max_id=next_max_id)
        if not feed:
            break
            
        has_next = feed.get("more_available", False)
        next_max_id = feed.get("next_max_id")
        
        for item in feed.get("items", []):
            if len(posts) >= MAX_POSTS_PER_TARGET:
                break
            
            # Media_type mapped strictly to post_type ('image', 'video', 'carousel')
            posts.append({
                "shortcode": item.get("code"),
                "post_type": item.get("post_type", "image"), 
                "likes": item.get("like_count", 0),
                "comments": item.get("comment_count", 0),
            })
            
    elapsed = time.time() - start_time
    return {
        "username": username,
        "scraped": len(posts),
        "followers": profile.get("followers", 0),
        "time_sec": round(elapsed, 2)
    }

async def main():
    print("=> Booting Parallel Architecture...")
    
    pm = ProxyManager()
    pm.add_proxy(PROXY_URL)
    
    # Auto-detect if Proxy is STICKY or ROTATING. Extremely important!
    await pm.detect_proxy_type() 
    
    # Limit max_concurrency (e.g. 5) so proxy service doesn't timeout!
    client = AsyncAnonClient(proxy_manager=pm, unlimited=True, max_concurrency=5)
    
    print(f"=> Executing concurrent tasks for {len(TARGETS)} targets...")
    tasks = [scrape_target(client, u) for u in TARGETS]
    results = await asyncio.gather(*tasks)
    
    print("\nRESULTS:")
    for res in results:
        if "error" in res:
            print(f" [XX] @{res['username']}: {res['error']}")
        else:
            print(f" [OK] @{res['username']:15s} | Extracted: {res['scraped']} items | Time: {res['time_sec']}s")

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
