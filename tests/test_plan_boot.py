from ag.plan import Planner
from ag.sch import Obs
from ag import consts


class _MockLLM:
    def gen(self, sys: str, user: str) -> str:
        u = user.lower()
        # Se l'obiettivo contiene un URL, navigaci
        if "github.com/test" in u:
            return f'{{"action":"navigate","url":"{consts.BOOT_GITHUB_URL}","thought":"URL nel goal"}}'
        if "about:blank" in u:
            return f'{{"action":"navigate","url":"{consts.DEFAULT_HOME_URL}","thought":"Inizio"}}'
        return '{"action":"done"}'


def test_bootstrap_navigate_from_goal_url():
    p = Planner(llm=_MockLLM())
    obs = Obs(url="about:blank", step=0)
    act = p.next(f"apri {consts.BOOT_GITHUB_URL}", obs, "")
    assert act.action == "navigate"
    assert act.url is not None
    assert "github.com" in act.url
