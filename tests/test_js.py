import pytest

from ag.js import load_obj


def test_load_obj_simple():
    assert load_obj('{"a":1}') == {"a": 1}

def test_load_obj_single_quotes():
    assert load_obj("{'action':'done','text':'ok'}")["action"] == "done"


def test_load_obj_embedded():
    s = "text before\n{ \"action\": \"done\", \"text\": \"ok\" }\ntext after"
    assert load_obj(s)["action"] == "done"


def test_load_obj_missing():
    with pytest.raises(ValueError):
        load_obj("no json here")
