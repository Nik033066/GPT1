from ag.plan import Planner
from ag.sch import Obs


class _LLM:
    def gen(self, sys: str, user: str) -> str:
        _ = sys
        _ = user
        return '{"action":"done","text":"x"}'


def test_ddg_captcha_falls_back_to_lite():
    p = Planner(llm=_LLM())
    obs = Obs(
        url="https://duckduckgo.com/?q=mars+news+today",
        text="Unfortunately, bots use DuckDuckGo too. Please complete the following challenge.",
        step=3,
    )
    act = p.next("apri google.com e cerca mars news today", obs, "")
    assert act.action == "navigate"
    assert act.url is not None
    assert "news.google.com/rss/search" in act.url
