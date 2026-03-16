"""
GraphQL Hash Validator
======================
Validates that Instagram GraphQL doc_ids and query_hashes are still
accepted by the server. Logs warnings for expired/changed hashes.

Usage:
    from instaharvest_v2.api.graphql.hash_validator import HashValidator

    validator = HashValidator(client)
    report = validator.validate_critical_doc_ids()
    # report → {"profile_info": True, "media_detail": False, ...}
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("instaharvest_v2")


class GraphQLHashExpired(Exception):
    """Raised when a GraphQL doc_id or query_hash is rejected by Instagram."""

    def __init__(self, identifier: str, id_value: str, response: Any = None):
        self.identifier = identifier
        self.id_value = id_value
        self.response = response
        super().__init__(
            f"GraphQL hash/doc_id expired: {identifier}={id_value}. "
            f"Instagram may have updated this endpoint."
        )


# Doc IDs that must work for core functionality
CRITICAL_DOC_IDS = [
    "profile_info",
    "profile_posts",
    "media_detail",
    "media_comments",
    "feed_timeline",
]

# Common error patterns that indicate an expired hash
_EXPIRED_INDICATORS = [
    "Document not found",
    "Unsupported get request",
    "Unknown query",
    "This endpoint has been retired",
]


class HashValidator:
    """
    Validates GraphQL hashes and doc_ids against Instagram's API.

    Sends lightweight probe requests and checks whether the server
    accepts or rejects each identifier.
    """

    def __init__(self, client):
        self._client = client

    def validate_doc_id(self, doc_id: str, name: str = "") -> bool:
        """
        Validate a single doc_id by sending a minimal probe request.

        Returns True if the doc_id is still accepted, False otherwise.
        """
        try:
            payload = {
                "variables": json.dumps({}),
                "doc_id": doc_id,
                "fb_api_caller_class": "RelayModern",
                "server_timestamps": "true",
            }

            data = self._client.post(
                "/graphql/query",
                data=payload,
                rate_category="get_default",
                full_url="https://www.instagram.com/graphql/query",
            )

            if data is None:
                logger.warning(
                    f"GraphQL doc_id '{name}' ({doc_id}): no response"
                )
                return False

            # Check for explicit "not found" errors
            if isinstance(data, dict):
                # A valid doc_id with missing variables usually returns
                # errors about missing variables — that still means the
                # doc_id itself is recognised.
                errors = data.get("errors", [])
                for err in errors:
                    msg = err.get("message", "") if isinstance(err, dict) else str(err)
                    for indicator in _EXPIRED_INDICATORS:
                        if indicator.lower() in msg.lower():
                            logger.warning(
                                f"⚠️ GraphQL doc_id EXPIRED: '{name}' ({doc_id}) → {msg}"
                            )
                            return False

                # If we got "data" key at all, the doc_id is valid
                if "data" in data or "extensions" in data:
                    return True

                # Unknown response shape — treat cautiously
                logger.debug(
                    f"GraphQL doc_id '{name}' ({doc_id}): unexpected response shape"
                )
                return True  # Assume valid if no explicit rejection

            return True

        except Exception as e:
            error_str = str(e).lower()
            for indicator in _EXPIRED_INDICATORS:
                if indicator.lower() in error_str:
                    logger.warning(
                        f"⚠️ GraphQL doc_id EXPIRED: '{name}' ({doc_id}) → {e}"
                    )
                    return False

            # Network errors don't mean the hash is expired
            logger.debug(f"doc_id validation error for '{name}' ({doc_id}): {e}")
            return True  # Benefit of the doubt

    def validate_critical_doc_ids(
        self,
        doc_ids: Optional[Dict[str, str]] = None,
        critical_only: bool = True,
    ) -> Dict[str, bool]:
        """
        Validate multiple doc_ids and return a report.

        Args:
            doc_ids: Full doc_id registry. If None, imports from registries.
            critical_only: If True, only validate CRITICAL_DOC_IDS.
                           If False, validate all.

        Returns:
            Dict mapping name → validity (True/False).
        """
        if doc_ids is None:
            from .registries import DOC_IDS
            doc_ids = DOC_IDS

        names = CRITICAL_DOC_IDS if critical_only else list(doc_ids.keys())
        report = {}

        for name in names:
            if name not in doc_ids:
                logger.warning(f"Unknown doc_id name: '{name}'")
                report[name] = False
                continue

            valid = self.validate_doc_id(doc_ids[name], name=name)
            report[name] = valid

            if not valid:
                logger.warning(
                    f"🔴 CRITICAL doc_id failed: '{name}' = {doc_ids[name]}"
                )

        # Summary log
        passed = sum(1 for v in report.values() if v)
        total = len(report)
        if passed == total:
            logger.info(f"✅ All {total} GraphQL doc_ids validated successfully")
        else:
            failed_names = [n for n, v in report.items() if not v]
            logger.warning(
                f"⚠️ {total - passed}/{total} GraphQL doc_ids FAILED: "
                f"{', '.join(failed_names)}"
            )

        return report


def check_response_for_expired_hash(
    response: Any,
    identifier_name: str = "",
    identifier_value: str = "",
) -> None:
    """
    Check a GraphQL response for signs that the hash/doc_id is expired.
    Raises GraphQLHashExpired if detected.

    Call this from transport methods after receiving a response.
    """
    if not isinstance(response, dict):
        return

    errors = response.get("errors", [])
    for err in errors:
        msg = err.get("message", "") if isinstance(err, dict) else str(err)
        for indicator in _EXPIRED_INDICATORS:
            if indicator.lower() in msg.lower():
                raise GraphQLHashExpired(
                    identifier=identifier_name,
                    id_value=identifier_value,
                    response=response,
                )
