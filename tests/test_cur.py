from ag.cur import Cur


def test_cur_ends_at_target():
    c = Cur(10, 10)
    pts = list(c.move(200, 150, w=40, seed=123))
    assert pts[0] != pts[-1]
    assert pts[-1] == (200, 150)


def test_cur_path_has_many_points():
    c = Cur(0, 0)
    pts = list(c.move(400, 10, w=20, seed=1))
    assert len(pts) >= 12

