# Japan Expanded 0.9.1 Phase Report: Daimyo House Agendas

## Scope

0.9.1 returns the focus to daimyo diversity. The existing framework already gives every Japanese daimyo ideas, at least one decision, at least one flavor event, origin recording, and unification legacy coverage. This slice adds another layer: low-frequency pre-unification agenda events tied to the founding-house archetype.

## New Content

- Added `events/jxp_25_daimyo_house_agenda_events.txt`.
- Added `common/event_modifiers/jxp_25_daimyo_house_agenda_modifiers.txt`.
- Added `localisation_source/jxp_25_daimyo_house_agenda_l_english_utf8_source.yml` and generated active localisation.
- Bumped descriptors to `0.9.1`.

## Design

Five events cover every daimyo through the existing 0.8.7 origin groups:

- Warrior houses: military rolls versus captain oaths.
- Court houses: Kyoto rank petitions versus local steward reform.
- Maritime houses: port registers versus ship rolls.
- Frontier houses: pass wardens versus frontier market brokers.
- Temple-market houses: shrine-temple privileges versus public account books.

Each event has two player choices. Choices apply an 8-year modifier and nudge one of the three age attributes by 5 points. This keeps the event from being a pure notification while avoiding large permanent stacking.

## Testing

Suggested route:

1. Start as one daimyo from each origin group, or use debug setup to seed origins.
2. Fire `event jxp_daimyo_agenda.1` through `.5` as appropriate.
3. Confirm event text, options, modifiers, and government-mechanic values update.
4. Use debug cleanup and confirm flags/modifiers are removed for repeat tests.
