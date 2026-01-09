from ag.plan import Planner
from ag.sch import Obs
from ag import consts


class _MockLLM:
    """LLM mock che simula ragionamento autonomo."""
    def gen(self, sys: str, user: str) -> str:
        u = user.lower()
        mem = ""
        if "fatto:" in u:
            idx = u.find("fatto:")
            mem = u[idx:idx+100]
        
        # Se pagina vuota e obiettivo menziona un sito, naviga direttamente
        if "about:blank" in u or "pagina vuota" in u:
            if "openai" in u:
                return f'{{"action":"navigate","url":"{consts.DEFAULT_TARGET_SITE}","thought":"Navigo a destinazione"}}'
            return f'{{"action":"navigate","url":"{consts.DEFAULT_HOME_URL}","thought":"Inizio da home"}}'
        
        # Se su pagina risultati (URL con /search)
        if "/search?q=" in u:
            return '{"action":"click","selector":"h3","thought":"Clicco risultato"}'
        
        # Se su Google e ha già digitato (type in memoria)
        if "google.com" in u and "type" in mem:
            return '{"action":"press","key":"Enter","thought":"Invio ricerca"}'
        
        # Se su Google con campo ricerca e non ha ancora digitato
        if "google.com" in u and "textarea" in u:
            if "machine learning" in u:
                return '{"action":"type","selector":"#APjFqb","text":"machine learning tutorial","thought":"Cerco"}'
            return '{"action":"type","selector":"#APjFqb","text":"test","thought":"Cerco"}'
        
        # Default
        return '{"action":"done","text":"Completato","thought":"Fine"}'


def test_planner_navigates_directly_to_known_site():
    p = Planner(llm=_MockLLM())
    obs = Obs(url="about:blank", text="", step=0)
    act = p.next("apri openai", obs, "")
    
    assert act.action == "navigate"
    assert "openai.com" in (act.url or "")


def test_planner_searches_for_generic_query():
    p = Planner(llm=_MockLLM())
    obs = Obs(
        url=consts.DEFAULT_HOME_URL + "/",
        text='[TEXTAREA] "Cerca" => #APjFqb',
        step=1
    )
    act = p.next("cerca machine learning", obs, "")
    
    assert act.action == "type"
    assert act.text is not None


def test_planner_presses_enter_after_type():
    p = Planner(llm=_MockLLM())
    obs = Obs(
        url=consts.DEFAULT_HOME_URL + "/",
        text='[TEXTAREA] "test" => #APjFqb',
        step=2
    )
    act = p.next("cerca test", obs, "type #APjFqb=test")
    
    assert act.action == "press"
    assert act.key == "Enter"


def test_planner_clicks_result_on_search_page():
    p = Planner(llm=_MockLLM())
    obs = Obs(
        url=consts.DEFAULT_HOME_URL + "/search?q=test",
        text='[A] "Result" => h3',
        step=3
    )
    act = p.next("cerca test", obs, "type\npress Enter")
    
    assert act.action == "click"


def test_planner_completes_when_done():
    p = Planner(llm=_MockLLM())
    obs = Obs(
        url=consts.EXAMPLE_ARTICLE_URL,
        text="Contenuto trovato...",
        step=5
    )
    act = p.next("trova info", obs, "navigate\nclick")
    
    assert act.action == "done"
