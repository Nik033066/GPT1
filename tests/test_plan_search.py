from ag.plan import Planner
from ag.sch import Obs


class _LLM:
    def gen(self, sys: str, user: str) -> str:
        _ = sys
        _ = user
        return '{"action":"done","text":"x"}'


def test_google_search_rule_types_query():
    p = Planner(llm=_LLM())
    act = p.next("apri google.com e cerca mars news today", Obs(url="https://www.google.com/", step=1), "")
    assert act.action == "navigate"
    assert act.url is not None
    assert "q=mars+news+today" in act.url


def test_google_search_rule_presses_enter_after_type():
    p = Planner(llm=_LLM())
    mem = "type textarea[name='q']=mars news today"
    act = p.next("apri google.com e cerca mars news today", Obs(url="https://www.google.com/search?q=mars+news+today", step=2), mem)
    assert act.action == "done"
