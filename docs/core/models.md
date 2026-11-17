# Data Models

InstaHarvest v2 uses Pydantic models for structured, validated data.

## Available Models

| Model | Description |
|---|---|
| `User` | Full user profile |
| `UserShort` | Minimal user info (pk, username) |
| `Media` | Post/reel/IGTV data |
| `Caption` | Media caption |
| `Comment` | Post comment |
| `Story` | Story item |
| `StorySticker` | Story sticker data |
| `Highlight` | Story highlight |
| `DirectThread` | DM thread |
| `DirectMessage` | Single DM message |
| `Location` | Location data |
| `Notification` | Notification item |

## User Model

```python
from instaharvest_v2.models import User

user = ig.users.get_by_username("cristiano")
```

| Field | Type | Description |
|---|---|---|
| `pk` | `int` | Unique user ID |
| `username` | `str` | Username |
| `full_name` | `str` | Display name |
| `biography` | `str` | Bio text |
| `bio` | `BioParsed` | Parsed bio mentions, hashtags, URLs, `bio_links` |
| `profile_pic_url` | `str` | Profile picture URL |
| `profile_pic_url_hd` | `str` | HD profile picture |
| `followers` | `int` | Follower count |
| `following` | `int` | Following count |
| `posts_count` | `int` | Total posts |
| `is_private` | `bool` | Private account |
| `is_verified` | `bool` | Verified badge |
| `is_business` | `bool` | Business account |
| `category` | `str` | Business category |
| `external_url` | `str` | Website URL |
| `contact` | `Contact` | Phone/email (business) |

## Media Model

```python
from instaharvest_v2.models import Media

media = ig.media.get_by_shortcode("ABC123")
```

| Field | Type | Description |
|---|---|---|
| `pk` | `int` | Media ID |
| `code` | `str` | URL shortcode (`media.url` builds full URL) |
| `media_type` | `int` | 1=photo, 2=video, 8=carousel |
| `caption` | `Caption` | Caption object (`caption_text` for raw text) |
| `like_count` | `int` | Number of likes |
| `comment_count` | `int` | Number of comments |
| `play_count` | `int` | Play count (video/reel) |
| `view_count` | `int` | View count |
| `taken_at` | `datetime` | Post timestamp |
| `image_versions` | `list[ImageVersion]` | Image URLs + sizes (`media.best_image_url` helper) |
| `video_versions` | `list[ImageVersion]` | Video URLs + sizes (`media.best_video_url` helper) |
| `carousel_media` | `list[Media]` | Child media items |
| `location` | `dict` | Tagged location |
| `tagged_users` | `list[UserShort]` | Tagged users |

## Dict-Like Access

All models support dict-like access for backward compatibility:

```python
user = ig.users.get_by_username("nike")

# Attribute access (recommended)
print(user.username)
print(user.followers)

# Dict-like access (backward compat)
print(user["username"])
print(user.get("followers", 0))

# Convert to dict
data = user.to_dict()
```

## Import

```python
from instaharvest_v2.models import (
    User, UserShort, Contact, BioParsed,
    Media, Caption,
    Comment,
    Story, StorySticker, Highlight,
    DirectThread, DirectMessage,
    Location,
    Notification,
)
```
