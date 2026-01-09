from ag.plan import Planner
from ag.sch import Obs
from ag import consts


class _MockLLM:
    def gen(self, sys: str, user: str) -> str:
        u = user.lower()
        if "/search" in u or "?q=" in u:
            return '{"action":"click","selector":"h3","thought":"Clicco risultato"}'
        return '{"action":"done","text":"Fine"}'


def test_search_results_page_clicks_result():
    p = Planner(llm=_MockLLM())
    obs = Obs(
        url=consts.ALT_QUERY_BASE + "mars+news",
        text='[A] "Mars News" => h3',
        step=3
    )
    act = p.next("cerca mars news", obs, "navigate\ntype\npress")
    assert act.action == "click"
