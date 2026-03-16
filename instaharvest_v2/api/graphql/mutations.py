"""
GraphQL Mutations
=================
Write operations: like, save, unsave media.
"""

import logging
from typing import Any, Dict

from .registries import DOC_IDS
from .transport import GraphQLTransport

logger = logging.getLogger("instaharvest_v2")


class GraphQLMutations(GraphQLTransport):
    """GraphQL mutation (write) operations."""

    # ═══════════════════════════════════════════════════════════
    # LIKE MEDIA — Like/unlike a post (mutation)
    # ═══════════════════════════════════════════════════════════

    def like_media(
        self,
        media_id: str | int,
        container_module: str = "single_post",
    ) -> Dict[str, Any]:
        """
        Like a post via GraphQL mutation.

        Uses doc_id: usePolarisLikeMediaLikeMutation

        Args:
            media_id: Media PK (numeric)
            container_module: Context where like happened
                - "single_post" — from post detail page
                - "feed_timeline" — from home feed
                - "profile" — from profile page

        Returns:
            dict:
                - success: bool
                - media_id: str
                - raw: dict
        """
        variables = {
            "media_id": str(media_id),
            "container_module": container_module,
        }

        try:
            data = self._graphql_doc_query(
                doc_id=DOC_IDS["like_media"],
                variables=variables,
                friendly_name="usePolarisLikeMediaLikeMutation",
            )

            raw_data = data.get("data", {}) if isinstance(data, dict) else {}

            # Check for success — mutation returns the liked media info
            success = False
            for key, val in raw_data.items():
                if isinstance(val, dict):
                    # Look for liked status
                    if val.get("status") == "ok" or "media" in val:
                        success = True
                        break
                elif val is not None:
                    success = True

            # Also check if no errors
            errors = data.get("errors", []) if isinstance(data, dict) else []
            if not errors and raw_data:
                success = True

            return {
                "success": success,
                "media_id": str(media_id),
                "raw": raw_data,
            }

        except Exception as e:
            logger.error(f"[GraphQL] like_media failed: {e}")
            return {
                "success": False,
                "media_id": str(media_id),
                "error": str(e),
            }

    # ═══════════════════════════════════════════════════════════
    # SAVE / UNSAVE MEDIA — Bookmark posts
    # ═══════════════════════════════════════════════════════════

    def save_media(self, media_id: str | int) -> Dict[str, Any]:
        """
        Save (bookmark) a post.

        Args:
            media_id: Media PK (numeric)

        Returns:
            dict: {success: bool, media_id: str}
        """
        try:
            result = self._client.post(
                f"/web/save/{media_id}/save/",
                rate_category="post_default",
            )
            return {
                "success": result.get("status") == "ok",
                "media_id": str(media_id),
                "raw": result,
            }
        except Exception as e:
            logger.error(f"[GraphQL] save_media failed: {e}")
            return {"success": False, "media_id": str(media_id), "error": str(e)}

    def unsave_media(self, media_id: str | int) -> Dict[str, Any]:
        """
        Unsave (remove bookmark) a post.

        Args:
            media_id: Media PK (numeric)

        Returns:
            dict: {success: bool, media_id: str}
        """
        try:
            result = self._client.post(
                f"/web/save/{media_id}/unsave/",
                rate_category="post_default",
            )
            return {
                "success": result.get("status") == "ok",
                "media_id": str(media_id),
                "raw": result,
            }
        except Exception as e:
            logger.error(f"[GraphQL] unsave_media failed: {e}")
            return {"success": False, "media_id": str(media_id), "error": str(e)}
