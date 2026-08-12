# Contributing

Thanks for considering contributions. Quick guidelines:

- Fork the repository and open a pull request.
- Keep changes small and focused.
- Add tests for new logic (`pytest`).
- Avoid storing sensitive clipboard content in commits or CI logs.
- For UI changes, keep default behavior privacy-preserving (don't enable history by default).

Recommended branches:
- `main` — stable prototype
- `dev` — active development

Run tests locally before opening a PR:

```bash
pytest -q
```
