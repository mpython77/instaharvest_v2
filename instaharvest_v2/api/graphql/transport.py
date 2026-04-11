"""
GraphQL Transport Layer
=======================
Base class with GET (query_hash) and POST (doc_id) transport methods.
Includes automatic detection of expired hashes/doc_ids.
"""

import json
import logging
from typing import Any, Dict

from .hash_validator import check_response_for_expired_hash

logger = logging.getLogger("instaharvest_v2")


class GraphQLTransport:
    """
    Low-level GraphQL transport.

    Two transport modes:
        - query_hash GET  → old style, still works for some queries
        - doc_id POST     → new style (2024+), required for newer endpoints

    Both methods automatically detect expired hashes/doc_ids and
    raise GraphQLHashExpired when Instagram rejects an identifier.
    """

    def __init__(self, client):
        """
        Init.

        Args:
            client: Parameter client
        """
        self._client = client

    # ═══════════════════════════════════════════════════════════
    # TRANSPORT: query_hash GET (legacy)
    # ═══════════════════════════════════════════════════════════

    def _graphql_query(
        self,
        query_hash: str,
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send GraphQL query (GET /graphql/query/).
        Legacy transport — still works for some endpoints.

        Args:
            query_hash: GraphQL query hash
            variables: Query parameters

        Returns:
            GraphQL response (inside data key)

        Raises:
            GraphQLHashExpired: If the query_hash is no longer accepted
        """
        data = self._client.get(
            "/graphql/query/",
            params={
                "query_hash": query_hash,
                "variables": json.dumps(variables),
            },
            rate_category="get_default",
            full_url="https://www.instagram.com/graphql/query/",
        )

        # Check for expired hash
        check_response_for_expired_hash(
            data,
            identifier_name="query_hash",
            identifier_value=query_hash,
        )

        return data

    # ═══════════════════════════════════════════════════════════
    # TRANSPORT: doc_id POST (modern, 2024+)
    # ═══════════════════════════════════════════════════════════

    def _graphql_doc_query(
        self,
        doc_id: str,
        variables: Dict[str, Any],
        friendly_name: str = "",
    ) -> Dict[str, Any]:
        """
        Send GraphQL query via doc_id (POST /graphql/query).
        Modern transport — required for newer endpoints.

        Args:
            doc_id: Document ID (from DOC_IDS registry or custom)
            variables: Query variables
            friendly_name: API request name (for logging)

        Returns:
            GraphQL response

        Raises:
            GraphQLHashExpired: If the doc_id is no longer accepted
        """
        payload = {
            "variables": json.dumps(variables),
            "doc_id": doc_id,
            "fb_api_caller_class": "RelayModern",
            "server_timestamps": "true",
        }
        if friendly_name:
            payload["fb_api_req_friendly_name"] = friendly_name

        data = self._client.post(
            "/graphql/query",
            data=payload,
            rate_category="get_default",
            full_url="https://www.instagram.com/graphql/query",
        )

        # Check for expired doc_id
        check_response_for_expired_hash(
            data,
            identifier_name="doc_id",
            identifier_value=doc_id,
        )

        return data
