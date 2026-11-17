# Batch Operations

> `ig.batch` (on `AsyncInstagram`) — Concurrent semaphore-controlled bulk operations.

!!! info "Async-Only & Distinct from Anonymous Bulk"
    `BatchAPI` is exposed lazily on **`AsyncInstagram`** (for **authenticated** operations). For scraping hundreds of public profiles without login, use `ig.public.bulk_profiles()` or `AsyncPublicAPI`.

## Quick Example

```python
import asyncio
from instaharvest_v2 import AsyncInstagram

async def main():
    async with AsyncInstagram.from_env(mode="fast") as ig:
        # Quickly verify a list of usernames concurrently
        results = await ig.batch.check_profiles(
            ["nike", "adidas", "fake_user_123"],
            concurrency=10,
        )

        for username, user in results.items():
            if user:
                print(f"@{username} exists! (PK: {user.pk})")
            else:
                print(f"@{username} failed or does not exist.")

asyncio.run(main())
```

## Why BatchAPI?

Running sequential `await` calls inside a loop over hundreds of items wastes wall-clock time, while unthrottled `asyncio.gather()` can burst too hard:

```python
# Controlled concurrency with progress tracking and error isolation
medias = await ig.batch.get_media_infos(media_id_list, concurrency=10)
```

## Supported Operations

- `check_profiles(usernames, concurrency=10) -> Dict[str, Optional[Any]]`: Fetch multiple profiles in parallel (`{username: User | None}`).
- `get_media_infos(media_ids, concurrency=10) -> Dict[str, Optional[Any]]`: Fetch multiple media items in parallel.
- `check_follow_backs(user_ids, concurrency=10) -> Dict[str, Dict]`: Parallel friendship status checks (`following`, `followed_by`, etc.).
- `bulk_follow(user_ids, concurrency=3, delay=2.0) -> Dict[str, bool]`: Paced parallel follows.
- `bulk_like(media_ids, concurrency=3, delay=2.0) -> Dict[str, bool]`: Paced parallel likes.
- `_run_batch(items, fn, concurrency=10, fail_silently=True, on_progress=None)`: Shared semaphore runner powering batch calls (also exposed publicly via `run(...)`).
