# AudienceAPI

> `ig.audience` — Find lookalike audiences, analyze audience overlap, and get audience insights.

## Quick Example

```python
ig = Instagram.from_env()

# Find users similar to a competitor's audience
result = ig.audience.find_lookalike("competitor", count=50)
for user in result["users"]:
    print(f"@{user['username']} — score: {user.get('relevance_score')}")
```

---

## Methods

### find_lookalike(source_username, count=50, min_followers=100, max_followers=50000, filter_private=True, method="mixed")

Find users similar to a source account's audience.

| Param | Type | Default | Description |
|---|---|---|---|
| `source_username` | `str` | — | Source account |
| `count` | `int` | 50 | Number of results |
| `min_followers` | `int` | 100 | Minimum follower count |
| `max_followers` | `int` | 50000 | Maximum follower count |
| `filter_private` | `bool` | `True` | Skip private accounts |
| `method` | `str` | `"mixed"` | `'followers'`, `'hashtag'`, or `'mixed'` |

**Returns:** `dict` — `{users, source, method, count, duration_seconds}`

---

### overlap(username_a, username_b, max_followers=2000)

Analyze audience overlap between two accounts.

```python
result = ig.audience.overlap("nike", "adidas")
print(f"Overlap rate: {result['overlap_rate']:.1f}%")
print(f"Common followers: {result['common_followers']:,}")
```

---

### insights(username, sample_size=100)

Get detailed audience insights for an account.

```python
insights = ig.audience.insights("my_account")
print(f"Quality: {insights['audience_quality']}")
print(f"Verified rate: {insights['verified_rate']}%")
print(f"Private rate: {insights['private_rate']}%")
```

---

## Async Version

```python
async with AsyncInstagram.from_env() as ig:
    lookalike = await ig.audience.find_lookalike("competitor", count=100)
    overlap = await ig.audience.overlap("nike", "adidas")
```
