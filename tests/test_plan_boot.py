from ag.plan import Planner
from ag.sch import Obs


class _LLM:
    def gen(self, sys: str, user: str) -> str:
        _ = sys
        _ = user
        return '{"action":"extract"}'


def test_bootstrap_navigate_from_goal_url():
    p = Planner(llm=_LLM())
    act = p.next("apri google.com e cerca mars news today", Obs(url="about:blank", step=0), "")
    assert act.action == "navigate"
    assert act.url is not None

