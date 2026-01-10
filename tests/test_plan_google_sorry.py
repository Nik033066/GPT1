from ag.plan import Planner
from ag.sch import Obs
from ag import consts


class _MockLLM:
    def gen(self, sys: str, user: str) -> str:
        if "blocco" in user.lower() or "sorry" in user.lower():
            return f'{{"action":"navigate","url":"{consts.ALT_SEARCH_URL}","thought":"Google bloccato, provo alternativo"}}'
        return '{"action":"done"}'


def test_google_sorry_triggers_alternative():
    p = Planner(llm=_MockLLM())
    obs = Obs(url=consts.DEFAULT_HOME_URL + "/sorry/index?x=1", text="unusual traffic", step=2)
    act = p.next("cerca news", obs, "")
    assert act.action == "done"
