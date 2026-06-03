from indexer.bsl_splitter import split_bsl


def test_one_procedure():
    chunks = split_bsl("Процедура Выполнить()\nСообщить(\"x\");\nКонецПроцедуры\n")

    assert len(chunks) == 1
    assert chunks[0].symbol_name == "Выполнить"
    assert chunks[0].symbol_type == "procedure"
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 3


def test_one_function():
    chunks = split_bsl("Функция Рассчитать()\nВозврат 1;\nКонецФункции\n")

    assert len(chunks) == 1
    assert chunks[0].symbol_name == "Рассчитать"
    assert chunks[0].symbol_type == "function"


def test_multiple_procedures():
    chunks = split_bsl(
        "Процедура Первая()\nКонецПроцедуры\n"
        "Функция Вторая()\nВозврат 2;\nКонецФункции\n"
    )

    assert [chunk.symbol_name for chunk in chunks] == ["Первая", "Вторая"]
    assert [chunk.symbol_type for chunk in chunks] == ["procedure", "function"]


def test_file_without_symbols_returns_module():
    chunks = split_bsl("Перем Значение;\nЗначение = 1;\n")

    assert len(chunks) == 1
    assert chunks[0].symbol_type == "module"
    assert chunks[0].symbol_name == "<module>"


def test_russian_identifier():
    chunks = split_bsl("Процедура РассчитатьТарифДляГруза()\nКонецПроцедуры\n")

    assert chunks[0].symbol_name == "РассчитатьТарифДляГруза"


def test_empty_file_returns_empty_module():
    chunks = split_bsl("")

    assert len(chunks) == 1
    assert chunks[0].symbol_type == "module"
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 0
    assert chunks[0].code == ""


def test_unclosed_symbol_falls_back_to_module():
    chunks = split_bsl("Процедура Сломана()\nСообщить(\"x\");\n")

    assert len(chunks) == 1
    assert chunks[0].symbol_type == "module"
