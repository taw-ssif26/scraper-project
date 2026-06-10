import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(BASE_DIR, "cache", "structure_cache.json")

def _load_cache() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r") as f:
        return json.load(f)


def _save_cache(cache: dict):
    os.makedirs("cache", exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def get_structure(domain: str) -> dict | None:
    cache = _load_cache()
    print(f"[Cache] Keys in cache: {list(cache.keys())}")
    return cache.get(domain)

    cache = _load_cache()
    return cache.get(domain)


def save_structure(domain: str, structure: dict):
    cache = _load_cache()
    cache[domain] = structure
    _save_cache(cache)
    print(f"[Cache] Saved structure for {domain}")


def clear_structure(domain: str):
    cache = _load_cache()
    if domain in cache:
        del cache[domain]
        _save_cache(cache)
        print(f"[Cache] Cleared structure for {domain}")
