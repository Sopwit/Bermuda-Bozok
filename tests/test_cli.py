"""
Tests for WeatherWise Command-Line Interface (CLI).
"""

import json

import pytest

from weatherwise.cli import main


class TestCLI:
    def test_cli_help(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "WeatherWise CLI" in captured.out

    def test_cli_empty_args_shows_help(self, capsys):
        code = main([])
        assert code == 0
        captured = capsys.readouterr()
        assert "WeatherWise CLI" in captured.out

    def test_cli_version(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "weatherwise" in captured.out

    def test_cli_query_with_mock(self, monkeypatch, capsys, sample_weather, sample_ml_result):
        def fake_fetch(*args, **kwargs):
            return sample_weather

        def fake_predict(weather_dict):
            return sample_ml_result

        monkeypatch.setattr("weatherwise.cli.fetch_weather_data", fake_fetch)
        monkeypatch.setattr("weatherwise.cli.predict_ml_decisions", fake_predict)

        code = main(["query", "Ankara", "--activity", "walking"])
        assert code == 0
        captured = capsys.readouterr()
        assert "WeatherWise CLI -- Ankara" in captured.out
        assert "Temp:" in captured.out

    def test_cli_query_json_output(self, monkeypatch, capsys, sample_weather, sample_ml_result):
        def fake_fetch(*args, **kwargs):
            return sample_weather

        def fake_predict(weather_dict):
            return sample_ml_result

        monkeypatch.setattr("weatherwise.cli.fetch_weather_data", fake_fetch)
        monkeypatch.setattr("weatherwise.cli.predict_ml_decisions", fake_predict)

        code = main(["Ankara", "--json"])
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["location"] == "Ankara"
        assert "ml_decision" in data

    def test_cli_health(self, capsys):
        code = main(["health"])
        assert code == 0
        captured = capsys.readouterr()
        assert "WeatherWise Health & System Status" in captured.out

    def test_cli_health_json(self, capsys):
        code = main(["health", "--json"])
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "dependencies" in data
        assert "models_loaded" in data
