import pytest

from github_stars_contrib_mcp.utils.models import APIResult


def test_apiresult_dict_like_get_and_item():
    res = APIResult(ok=True, data={"ids": ["1", "2"]}, error=None)
    # __getitem__ proxies to attributes for backward compatibility
    assert res["ok"] is True
    assert res["data"] == {"ids": ["1", "2"]}
    assert res.get("ok") is True
    # default
    assert res.get("missing", 123) == 123


def test_apiresult_attr_proxy_and_missing():
    res = APIResult(ok=True, data={"ids": ["a", "b"]}, error=None)
    # attribute proxy
    assert res.ids == ["a", "b"]
    # explicit attributes still work
    assert res.ok is True
    assert res.data == {"ids": ["a", "b"]}
    assert res.error is None
    # missing attribute raises
    with pytest.raises(AttributeError):
        _ = res.nonexistent
