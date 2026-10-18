# Working in pygame_spiel

Read [CONTRIBUTING.md](CONTRIBUTING.md) for setup, checks and qualification limits.
Use `python -B -W error -m unittest discover -s tests -v` from the repository root.

## Owners and boundaries

Package paths below are relative to `pygame_spiel/`.

- `config.py` owns immutable settings, validation and explicit seeds.
- `controllers.py` owns the custom Python bot-file registry, construction and cleanup.
- `games/base.py` owns OpenSpiel state and controller lifetime; concrete games
  own rendering/mouse mapping. OpenSpiel owns turn order and game rules.
- `main.py` owns entry points and the display/event loop; `menu.py` owns selection.
- `resources.py` owns read-only image lookup and external model/cache paths.
  Lookup must not write. `downloads.py` alone fetches/extracts models explicitly.
- `bots/dqn.py` alone owns the TensorFlow graph/session; load it only for DQN.
  Keep neural and download dependencies optional at their selected-use boundaries.

OpenSpiel owns game rules and legal actions. Do not duplicate them in a renderer.
Do not introduce downloads or mutable package-directory writes during imports,
resource lookup or game/controller construction. Importing configuration, registry,
resources, menu, entry points or renderers must not load runtime backends; Menu
construction is also backend-free. `GameFactory.create` loads OpenSpiel
and controllers; `open_display`/`close` bound display/resource lifetime. `--no-menu`
opens a display and is not headless execution. Keep unit checks on explicit doubles
and qualify real backends separately. See [extension contracts](docs/extending.md).

When replacing an implementation, migrate all consumers, delete the replaced
implementation, and remove tests/fixtures/assets whose sole consumer disappeared.
Keep compatibility only for a named currently supported consumer; obsolete tests
alone do not justify retaining code. Document public contract changes.

## Maintained documentation

- Describe the current supported system and verify instructions against code.
- Keep completed-work reports and run evidence outside maintained product docs.
- Remove superseded prose when its replacement lands.
- Active plans contain remaining work, dependencies and acceptance criteria;
  update or retire them when completed.
- Review the surviving reading path, including untouched documents and links,
  rather than only the diff.
- Historical explanation needs a concrete present-day compatibility or decision purpose.
