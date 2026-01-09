from ag.plan import Planner
from ag.sch import Obs
from ag import consts


class _MockLLM:
    def gen(self, sys: str, user: str) -> str:
        # Se c'è hint di blocco, l'LLM deve cambiare strategia
        if "blocco" in user.lower() or "captcha" in user.lower():
            return f'{{"action":"navigate","url":"{consts.ALT_NEWS_URL}","thought":"Uso fonte alternativa"}}'
        return '{"action":"done","text":"x"}'


def test_captcha_triggers_alternative_approach():
    p = Planner(llm=_MockLLM())
    obs = Obs(
        url=consts.ALT_QUERY_BASE + "test",
        text="Please verify you are human. Complete the captcha.",
        step=3,
    )
    act = p.next("cerca test", obs, "")
    # L'LLM riceve l'hint del blocco e decide di navigare altrove
    assert act.action == "navigate"
