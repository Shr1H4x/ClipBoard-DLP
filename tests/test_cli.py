from click.testing import CliRunner

from clipboard_dlp import __version__
from clipboard_dlp.cli import main


def test_version_option():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_info_command():
    result = CliRunner().invoke(main, ["info"])
    assert result.exit_code == 0
    assert "Clipboard DLP prototype" in result.output


def test_analyze_without_text():
    result = CliRunner().invoke(main, ["analyze"])
    assert result.exit_code == 0
    assert "No text provided" in result.output


def test_analyze_plain_text():
    result = CliRunner().invoke(main, ["analyze", "--text", "hello world"])
    assert result.exit_code == 0
    assert "Matches:" in result.output
    assert "Entropy:" in result.output
    assert "Risk:" in result.output
