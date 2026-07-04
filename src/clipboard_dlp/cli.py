import click
import pathlib
from clipboard_dlp import __version__
from clipboard_dlp import analyzer


@click.group()
@click.version_option(version=__version__)
def main():
    """Clipboard DLP — lightweight CLI demo."""


@main.command()
def info():
    """Show a short project info message."""
    click.echo("Clipboard DLP prototype — lightweight detection demo")
    click.echo("See docs/ for architecture and storage strategy.")


@main.command()
@click.option("--text", "text", help="Text to analyze (if omitted reads nothing)")
def analyze(text: str):
    """Analyze provided text and print detection result."""
    if not text:
        click.echo("No text provided. Use --text 'string' to analyze.")
        return
    res = analyzer.detect(text)
    click.echo(f"Matches: {res['matches']}")
    click.echo(f"Entropy: {res['entropy']:.2f}")
    click.echo(f"Risk: {res['risk']}")


@main.command(name="show-docs")
def show_docs():
    root = pathlib.Path(__file__).resolve().parents[2]
    docs_dir = root / "docs"
    if not docs_dir.exists():
        click.echo("No docs/ directory found.")
        return
    click.echo("Available docs:")
    for p in sorted(docs_dir.glob("*.md")):
        click.echo(f"- {p.name}")


if __name__ == "__main__":
    main()
