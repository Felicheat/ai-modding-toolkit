# Game time, day length and vitals

**Caution:** the numbers and formulas here describe the vanilla game as it was read or measured on the build this
skill is stamped with, by a few modders, not by GSC. A game update, the difficulty level or another mod can change
them. Read the current value from the game's own tables and prove it with a test in game before you build on it.

## How fast game time runs
- Game speed (game hours per real hour) = `RealToGameTimeCoef` x `TimeCoefCurve(game hour)`.
- `RealToGameTimeCoef` = 24, in `CoreVariables.cfg` (a text table inside `pakchunk0-Windows.pak`). The same file
  names the curve (`WeatherTimeCoefficientCurvePath` -> `/Game/_STALKER2/GameDesign/Time/TimeCoefCurve`) and holds a
  "Day Cycle" block (`DawnStartTime` 4, `DayStartTime` 6, `EveningStartTime` 20, `NightStartTime` 0; what reads
  these labels is not verified).
- `TimeCoefCurve` is a cooked UCurveFloat (file `Stalker2/Content/_STALKER2/GameDesign/Time/TimeCoefCurve`). Decode,
  edit and repack it with stalker2-curves; it ships as an IoStore trio.
- Real minutes per game hour at curve value v = 60 / (24 x v) = 2.5 / v. Lower value = slower clock = longer real
  time.

## The vanilla curve
| Key (game hour) | 4:00 | 5:30 | 7:30 | 19:00 | 21:00 | 22:00 |
|---|---|---|---|---|---|---|
| Value | 0.9 | 0.575 | 0.575 | 0.575 | 0.575 | 0.9 |

- Constant outside the keys: 0.9 from 22:00 through midnight to 04:00.
- So: night flat 22:00 to 04:00 (6 game hours at 0.9, about 17 real minutes), dawn ramp 04:00 to 05:30, day plateau
  05:30 to 21:00 (15.5 game hours at 0.575, about 67 real minutes), dusk ramp 21:00 to 22:00. A full game day is
  roughly 90 real minutes.
- Vanilla keys are cubic with irregular, hand-set tangents (one leave tangent is extreme), so the vanilla ramps do
  not follow a straight line. Integrate the evaluated curve if you need vanilla's exact figure.

## Vitals and other systems on the game clock
- Hunger, sleepiness and radiation accumulate on GAME time, not real time (community-reported; the tick logic is
  native code, nothing in cfg shows it).
- Stamina and health regeneration are probably real-time (not confirmed).
- Trader restocks run on game time too (reported every 8 game hours).

## After a game update
Re-extract `TimeCoefCurve` and compare it with your baseline, and byte-compare `CoreVariables.cfg`
(`RealToGameTimeCoef`, the Day Cycle block). How: stalker2-updates.
