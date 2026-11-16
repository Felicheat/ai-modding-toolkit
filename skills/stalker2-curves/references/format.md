# Cooked curve byte layout

`retoc to-legacy` writes each curve as `<Name>.uasset` (package summary, names, imports, export table) plus
`<Name>.uexp` (the export's serialized properties, then the package tag). Every value edit happens in the `.uexp`.

## .uexp layout
```
top-level fragment header    2 bytes per fragment
property values              one FRichCurve per value: CurveFloat 1, CurveLinearColor up to 4 (R, G, B, A)
00 00 00 00                  no object GUID
C1 83 2A 9E                  package file tag
```
Each FRichCurve value:
```
fragment header              2 bytes; 00 03 for a curve with keys (Keys is its only serialized property)
int32 key count
keys                         27 bytes each
```
An empty channel is only its 2-byte header (`05 01`: properties skipped, no values) with no count and no keys.

## Fragment headers (unversioned property serialization)
- A uint16, little-endian: bits 0 to 6 = properties skipped before the values, bit 7 = a zero mask follows, bit 8 =
  last fragment, bits 9 to 15 = values that follow. Read big-endian (as the pack's decoder does), the same word
  shows bit 0 = last, bits 1 to 7 = value count, bits 8 to 14 = skip count and bit 15 = zero mask.
- Vanilla values: CurveFloat top level `00 03` (1 value), CurveLinearColor `00 09` (4 values), a channel with keys
  `00 03`, an empty channel `05 01`. No vanilla curve sets the zero-mask bit; if one ever does, a bit mask over the
  values follows the last fragment and the offsets below shift.
- Default properties are not serialized, so pre- and post-infinity extrapolation stay at their default: constant.
  The curve holds its first key's value before the first key and its last key's value after the last.

## Key (27 bytes)
| Offset | Type | Field |
|---|---|---|
| 0 | uint8 | InterpMode: 0 linear, 1 constant, 2 cubic |
| 1 | uint8 | TangentMode: 0 auto, 1 user, 2 break |
| 2 | uint8 | TangentWeightMode: 0 none, 1 arrive, 2 leave, 3 both |
| 3 | float32 | Time |
| 7 | float32 | Value |
| 11 | float32 | ArriveTangent |
| 15 | float32 | ArriveTangentWeight |
| 19 | float32 | LeaveTangent |
| 23 | float32 | LeaveTangentWeight |

## Offsets that follow
- CurveFloat: key k starts at byte 8 + 27 x k (2 top-level + 2 channel header + 4 count); its Value at
  8 + 27 x k + 7.
- CurveLinearColor: the R channel's keys start at byte 8 as well; each later channel starts right after the
  previous channel's last key (2-byte header, then a 4-byte count unless the channel is empty).
- File size = 2 + the sum over channels of (2 + 4 + 27 x keys), or 2 for an empty channel, + 8.
- Vanilla mode bytes: TimeCoefCurve keys are `02 02 03` (cubic, break, weighted both; one key `02 02 00`). Almost
  every weather-curve key is `00 00 00` (linear, auto, no weights); a few dozen are cubic.

## How keys evaluate
- Linear keys: a straight line between neighbours; tangents are ignored.
- Cubic keys: a curve shaped by the tangents (and, in weighted mode, by the weights as handle lengths). Vanilla
  tangents fit vanilla values only, which is why new values overshoot.
- Cubic with all four tangent floats zero: no overshoot. With weighted-both keys the segment runs as a straight
  line between the two values; without weights it is a gentle S between them.

## Changing the key count
- A new `.uexp` size changes the export's serial size in the `.uasset` export table and the package's total and
  bulk-data offsets in the summary. Rewrite through UAssetAPI (atenfyr), which reads and writes these legacy files
  with its UE 5.3 engine-version setting, or re-save the curve in the Zone Kit.
- Keep keys sorted by time, and keep the mode bytes consistent with the neighbours you copy from.
- In-place edits (same count) need nothing else: values, times, tangents and mode bytes can all be overwritten at
  their offsets.
