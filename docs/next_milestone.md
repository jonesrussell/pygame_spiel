# Session and controller plan

## Goal and dependencies

Separate turn advancement from rendering so sessions can support additional
players, actor-specific information and responsive controller execution.
OpenSpiel or a separately qualified game adapter must own game rules. The
two supported board games and developer Python bot-file extension are acceptance
fixtures; a real-backend test environment is required for integration qualification.

## Next implementation scope

1. Move turn advancement from the renderer `play()` methods into one session
   owner. Use a player-count-aware controller mapping, session ID and state
   revision. Classify terminal, chance, player-turn, simultaneous and unsupported
   nodes before dispatch, with explicit failures for unsupported game types.
2. Define actor requests containing legal actions and the adapter's information
   or observation view for that actor. Test that changing hidden opponent state
   cannot change the actor's request. Never pass hidden opponent cards to a poker
   policy through a generic full-state bot API, and do not invent another game
   representation to work around missing adapter guarantees.
3. Dispatch controller work asynchronously through bounded requests/results
   carrying session ID, revision, actor and request ID. Reject stale results
   after a move, reset or stop. Define cancellation, timeout and resource cleanup
   while display/event handling continues.
4. Add Pause/Step/Stop and a reproducible session command stream. Define what one
   Step advances independently of FPS. Record game/controller settings, seeds
   and retained model identifiers; keep rendering timing outside RNG progression.

## Acceptance criteria

- Both board games retain legal mouse input and human/random/MCTS/custom-bot
  construction, with clear errors for unsupported configurations.
- One owner advances session state; rendering consumes a presentation snapshot.
- Headless checks cover turn classification, chance/terminal behavior, actor
  information boundaries, cancellation, stale results and replayed actions.
- Player counts are exercised through session handling and renderers together
  before additional-seat support is claimed.
- Real OpenSpiel/controller/display integration is checked in a suitable test
  environment; DQN checkpoint compatibility is qualified separately if DQN is used.
- Construction and resource lookup have no implicit download or display side effects.

## Dependent interface and adapter work

After the session/request boundary is qualified:

- Design the named-opponent selection experience around controller identities
  and settings. Keep Python bot-file loading as a developer extension.
- Start with a shared Python session API. Add a thin JSON CLI only for a named
  automation consumer; an eventual MCP or alternate UI adapter must call that
  same owner. Define a serialized boundary only for supported external requests;
  custom Python constructor kwargs are not automatically JSON configuration.
- Qualify additional game adapters and presentation data separately before adding
  games or player counts. Keep game rules and legal actions in OpenSpiel or the
  qualified adapter, and policy training outside the renderer.
