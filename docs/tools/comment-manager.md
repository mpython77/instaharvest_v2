# CommentManagerAPI

> `ig.comment_manager` — Filter comments, auto-reply, delete spam, and analyze sentiment.

## Quick Example

```python
ig = Instagram.from_env()

# Get and analyze comments
comments = ig.comment_manager.get_comments(media_pk, sort="top")
sentiment = ig.comment_manager.sentiment(media_pk)
print(f"Positive: {sentiment['positive']}%, Negative: {sentiment['negative']}%")
```

---

## Methods

### get_comments(media_id, count=50, sort="newest")

Get filtered comments for a post.

| Param | Type | Default | Description |
|---|---|---|---|
| `media_id` | `str/int` | — | Post media ID / PK |
| `count` | `int` | 50 | Max comments to fetch |
| `sort` | `str` | `"newest"` | Sort: `"newest"`, `"top"`, `"oldest"` |

---

### auto_reply(media_id, keyword="", reply="", max_count=20, skip_own=True, delay=(3, 8))

Auto-reply to comments containing a keyword.

```python
ig.comment_manager.auto_reply(
    media_id,
    keyword="price?",
    reply="Check our bio for pricing! 💰"
)
```

---

### delete_spam(media_id, max_delete=50, custom_patterns=None)

Detect and delete spam comments.

```python
result = ig.comment_manager.delete_spam(media_id)
print(f"Deleted {result['deleted']} spam comments")
```

**Spam detection includes:**

- "follow for follow" / "f4f" patterns
- Excessive emojis
- URL spam
- Money/promotion spam
- Repeated characters

---

### sentiment(media_id, count=100)

Analyze comment sentiment distribution.

```python
result = ig.comment_manager.sentiment(media_id)
# {
#     "total": 150,
#     "positive": 65,    # percentage
#     "negative": 10,
#     "neutral": 25,
#     "top_positive": [...],
#     "top_negative": [...]
# }
```

---

## Async Version

```python
async with AsyncInstagram.from_env() as ig:
    comments = await ig.comment_manager.get_comments(media_pk)
    sentiment = await ig.comment_manager.sentiment(media_pk)
    await ig.comment_manager.delete_spam(media_pk)
```
