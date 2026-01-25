import os

def build_id() -> str:
    sha = (
        os.getenv("RAILWAY_GIT_COMMIT_SHA")
        or os.getenv("GITHUB_SHA")
        or os.getenv("GIT_COMMIT_SHA")
        or ""
    )
    return sha[:8] if sha else "dev"
