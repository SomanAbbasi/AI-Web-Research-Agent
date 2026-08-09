from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())

    scheme = parts.scheme.lower()
    hostname = (parts.hostname or "").lower()

    if scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported URL scheme: {scheme}")

    if not hostname:
        raise ValueError(f"Invalid URL: {url}")

    port = parts.port

    if port is None:
        netloc = hostname
    elif (scheme == "http" and port == 80) or (
        scheme == "https" and port == 443
    ):
        netloc = hostname
    else:
        netloc = f"{hostname}:{port}"

    path = parts.path or "/"

    if path != "/":
        path = path.rstrip("/")

    return urlunsplit(
        (
            scheme,
            netloc,
            path,
            parts.query,
            "",
        )
    )