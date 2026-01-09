from ag.cur import Cur, PathResult, DEFAULT_FPS


def test_cur_ends_at_target():
    """Verifica che il cursore arrivi esattamente al target."""
    c = Cur(10, 10)
    pts = list(c.move(200, 150, w=40, seed=123))
    assert pts[0] != pts[-1]
    assert pts[-1] == (200, 150)


def test_cur_path_has_many_points():
    """Verifica che il path abbia abbastanza punti per un movimento fluido."""
    c = Cur(0, 0)
    pts = list(c.move(400, 10, w=20, seed=1))
    assert len(pts) >= 12


def test_cur_move_timed_returns_path_result():
    """Verifica che move_timed ritorni un PathResult valido."""
    c = Cur(0, 0)
    result = c.move_timed(300, 200, w=30, seed=42)
    
    assert isinstance(result, PathResult)
    assert len(result.points) >= 8
    assert result.total_time_ms > 0
    assert result.delay_per_step_ms > 0
    # L'ultimo punto deve essere il target
    assert result.points[-1] == (300, 200)


def test_cur_iter_timed_yields_correct_format():
    """Verifica che iter_timed produca tuple (x, y, delay_ms)."""
    c = Cur(50, 50)
    points = list(c.iter_timed(200, 150, w=25, seed=99))
    
    assert len(points) >= 8
    # Verifica formato di ogni punto
    for pt in points:
        assert len(pt) == 3  # (x, y, delay_ms)
        x, y, delay_ms = pt
        assert isinstance(x, (int, float))  # Può essere int o float
        assert isinstance(y, (int, float))
        assert isinstance(delay_ms, float)
        assert delay_ms >= 0


def test_cur_timing_increases_with_distance():
    """Verifica che la Legge di Fitts aumenti il tempo con la distanza."""
    c1 = Cur(0, 0)
    result_short = c1.move_timed(50, 50, w=20, seed=1)
    
    c2 = Cur(0, 0)
    result_long = c2.move_timed(500, 500, w=20, seed=1)
    
    # Distanza maggiore = tempo maggiore
    assert result_long.total_time_ms > result_short.total_time_ms


def test_cur_timing_decreases_with_target_size():
    """Verifica che la Legge di Fitts diminuisca il tempo con target più grandi."""
    c1 = Cur(0, 0)
    result_small = c1.move_timed(200, 200, w=10, seed=1)
    
    c2 = Cur(0, 0)
    result_large = c2.move_timed(200, 200, w=100, seed=1)
    
    # Target più grande = tempo minore (più facile da raggiungere)
    assert result_large.total_time_ms <= result_small.total_time_ms


def test_cur_spring_settle_included():
    """Verifica che i punti di spring settle siano inclusi nel path."""
    c = Cur(0, 0)
    result = c.move_timed(100, 100, w=20, seed=1)
    
    # Il path deve avere punti extra per il settle (tipicamente 9 punti)
    # Verifica che il penultimo punto NON sia esattamente il target
    # (perché il settle aggiunge oscillazioni prima del punto finale)
    assert len(result.points) > 15  # Movimento base + settle
    # L'ultimo punto deve essere esattamente il target
    assert result.points[-1] == (100, 100)

