from api.query_expansion import expand_query


def test_expand_query_adds_synonyms():
    expanded = expand_query("Нужно поменять расчет тарифа для температурного груза")

    assert "Нужно поменять" in expanded
    assert "стоимость" in expanded
    assert "рефрижератор" in expanded
    assert "перевозка" in expanded


def test_expand_query_without_matches_returns_original():
    query = "Нужно изменить неизвестную настройку"

    assert expand_query(query) == query
