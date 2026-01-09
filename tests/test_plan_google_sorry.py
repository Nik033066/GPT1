from ag.plan import Planner
from ag.sch import Obs


class _LLM:
    def gen(self, sys: str, user: str) -> str:
        _ = sys
        _ = user
        return '{"action":"done","text":"x"}'


def test_fallback_when_google_blocks():
    p = Planner(llm=_LLM())
    obs = Obs(url="https://www.google.com/sorry/index?x=1", step=2)
    act = p.next("apri google.com e cerca mars news today", obs, "")
    assert act.action == "navigate"
    assert act.url is not None
    assert "news.google.com/rss/search" in act.url
