# JXP 0.22.0 Working Integration Plan

Status: implementation complete in the staged workspace; static validation
complete; live Documents deployment and in-game runtime testing remain.

## Completed

- Consolidated 27 player-selectable route reforms and 38 founder-house reforms
  into the existing vanilla monarchy levels 1-11.
- Removed the four post-11 JXP reform levels and stopped auto-granting the 27
  visible route choices. Hidden/basic route carriers remain auto-granted.
- Generated and registered 35 EU4-format government reform icons.
- Added a one-day, flag-guarded `0.22.0` migration event for old saves.
- Corrected daimyo, JAP and transformed-route mission potentials.
- Added a five-column, rows 1-8 foundation tree for all transformed Japan tags.
- Added an effective vanilla-plus-mod topology validator pinned to the local
  EU4 1.37.5 Japanese mission files.
- Reduced Shinto harmonization to one guarded engine mutation and removed the
  manual `harmonized_shinto` add/remove workaround.
- Replaced annual scripted province conversion with three native Confucian
  Centers of Reformation in Kyoto, Hizen and Musashi, with fallbacks.
- Protected Ise province 4359 from the Confucian spread.
- Preserved all eight Shinto incident themes through Confucian bridge chains
  and retained the JXP oceanic-opening policy state.
- Regenerated active double-byte localisation, including the stale `jxp_52`
  file and the new mission/event files.
- Updated debug cleanup for native centers, bridge flags, migration state and
  JXP-owned Ise religious zeal.

## Validation complete

- General validator: no issues.
- Clausewitz parser: 162/162 gameplay scripts parsed.
- Mission topology: 187 missions, 35 mod series, 23 pinned vanilla series,
  11 effective profiles, no collisions or invalid dependency edges.
- Government reforms: 27 visible route + 38 founder reforms registered in the
  first 11 levels; 306 dormant definitions remain parked.
- Art: 35/35 DDS files are 57x57 RGBA with matching sprites and textures.
- Validator regression tests: 14/14 passed.
- Game-root residual scan: no `jxp_*` files in the vanilla EU4 directory.

## Remaining runtime work

- Deploy the staged tree to the Documents mod directory.
- Start a fresh game and one existing CJP save.
- Confirm the government reform choice UI, mission arrows and five-column
  layout in the actual renderer.
- Confirm native Confucian centers spread into harmonized Shinto provinces.
- Inspect a fresh `error.log` after the runtime test.
