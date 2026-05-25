from integrations.repository_ingestion import RepositoryIngestionService


def test_repo_profile_cache_round_trips(tmp_path):
    service = object.__new__(RepositoryIngestionService)
    service.cache_path = tmp_path / "repo_profiles.json"
    cache = {
        RepositoryIngestionService._cache_key("https://github.com/org/repo.git", "main", "abc123"): {
            "analysis": {"framework": "playwright", "is_empty": False}
        }
    }

    service._save_cache(cache)

    assert service._load_cache() == cache


def test_cache_key_uses_repo_branch_and_sha():
    key = RepositoryIngestionService._cache_key("https://github.com/org/repo.git", "main", "abc123")

    assert key == "https://github.com/org/repo.git|main|abc123"
