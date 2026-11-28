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


def test_personal_column_in_an_approved_market_file_is_blocked(tmp_path, monkeypatch):
    market = tmp_path / "data/market"
    market.mkdir(parents=True)
    (market / "SP500.csv").write_text("date,value,source_url,fetched_utc,client_name\n")
    monkeypatch.setattr(check, "ROOT", tmp_path)
    assert any("unexpected CSV columns" in p for p in check.problems())


# JC 2026-11-28: never leave an API key public. Fake keys are built at run time
# so this file itself never contains a key-shaped string.
FAKE_GITHUB = "".join(["gh", "p_", "A1b2C3d4" * 5])
FAKE_OPENAI = "".join(["sk", "-", "Zx9" * 14])


def test_an_api_key_in_any_file_is_blocked(tmp_path, monkeypatch):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/fetch.py").write_text(f"TOKEN = '{FAKE_GITHUB}'\n")
    (tmp_path / "notes.csv").write_text(f"x,{FAKE_OPENAI}\n")
    monkeypatch.setattr(check, "ROOT", tmp_path)
    found = check.problems()
    assert any("scripts/fetch.py" in p and "key" in p.lower() for p in found)
    assert any("notes.csv" in p for p in found)
    assert not any(FAKE_GITHUB in p or FAKE_OPENAI in p for p in found)  # never print the key


def test_the_real_fred_key_value_is_blocked(tmp_path, monkeypatch):
    real = "0123abcd" * 4  # stands in for the repo secret FRED_API_KEY
    monkeypatch.setenv("FRED_API_KEY", real)
    (tmp_path / "data").mkdir()
    (tmp_path / "data/sec_revenue.csv").write_text(f"url\nhttps://api.stlouisfed.org/?api_key={real}\n")
    monkeypatch.setattr(check, "ROOT", tmp_path)
    assert any("FRED_API_KEY" in p for p in check.problems())


def test_a_committed_env_file_is_blocked(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("A=1\n")
    monkeypatch.setattr(check, "ROOT", tmp_path)
    assert any(".env" in p for p in check.problems())
