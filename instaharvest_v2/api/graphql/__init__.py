"""
GraphQL API Package
===================
Unified GraphQL API combining queries, mutations, and feed operations.
"""

from .queries import GraphQLQueries
from .mutations import GraphQLMutations
from .feeds import GraphQLFeeds
from .transport import GraphQLTransport
from .parsers import GraphQLParsers
from .registries import QUERY_HASHES, DOC_IDS
from .hash_validator import check_response_for_expired_hash


class GraphQLAPI(GraphQLQueries, GraphQLMutations, GraphQLFeeds):
    """Unified GraphQL API — queries, mutations, and feed operations."""
    pass


__all__ = [
    "GraphQLAPI",
    "GraphQLTransport",
    "GraphQLParsers",
    "GraphQLQueries",
    "GraphQLMutations",
    "GraphQLFeeds",
    "QUERY_HASHES",
    "DOC_IDS",
    "check_response_for_expired_hash",
]
