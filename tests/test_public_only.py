import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('check_public', ROOT / 'scripts/check_public.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def test_repository_holds_only_public_market_data():
    assert check.problems() == []


def test_a_personal_file_is_blocked(tmp_path, monkeypatch):
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data/positions.csv').write_text('ticker,shares,avg_cost\n0050,1,1\n')
    monkeypatch.setattr(check, 'ROOT', tmp_path)
    assert any('positions.csv' in p for p in check.problems())


def test_personal_words_in_a_script_are_blocked(tmp_path, monkeypatch):
    (tmp_path / 'scripts').mkdir()
    (tmp_path / 'scripts/x.py').write_text("ACCOUNT = '永豐'\n", encoding='utf-8')
    monkeypatch.setattr(check, 'ROOT', tmp_path)
    assert check.problems()
