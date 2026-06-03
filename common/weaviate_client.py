from __future__ import annotations

from common.settings import Settings


def connect_weaviate(settings: Settings):
    try:
        import weaviate
        from weaviate.auth import AuthApiKey
    except ImportError as exc:
        raise RuntimeError("weaviate-client is not installed") from exc

    parsed = settings.parsed_weaviate_url()
    auth = AuthApiKey(settings.weaviate_api_key) if settings.weaviate_api_key else None
    return weaviate.connect_to_custom(
        http_host=parsed.hostname,
        http_port=parsed.port or (443 if parsed.scheme == "https" else 80),
        http_secure=parsed.scheme == "https",
        grpc_host=settings.weaviate_grpc_host or parsed.hostname,
        grpc_port=settings.weaviate_grpc_port,
        grpc_secure=settings.weaviate_grpc_secure,
        auth_credentials=auth,
    )
