from ag.plan import Planner
from ag.sch import Obs


class _LLM:
    def gen(self, sys: str, user: str) -> str:
        _ = sys
        _ = user
        return '{"action":"type","selector":"input","text":"x"}'


def test_duckduckgo_done_overrides_llm():
    p = Planner(llm=_LLM())
    act = p.next("apri google.com e cerca mars news today", Obs(url="https://duckduckgo.com/?q=mars+news+today", step=3), "goto x")
    assert act.action == "type"
