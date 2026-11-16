# Damage and armor

## Contents
1. The bullet formula (no clamp)
2. How one hit is resolved, step by step
3. What it means per damage source
4. Inputs and where they live
5. Worked example
6. Where the two sources differ
7. Buckshot, and humans going down

Sections 1, 4 and 7: measured in game, plus cfg reading. Sections 2, 3 and 5: the game's own hit resolution with the
cfg values that feed it ([cfg] = read from `GameLite/GameData`, [inferred] = a guess). Section 6: where the two
sides disagree.

**Caution:** the numbers and formulas here describe the vanilla game as it was read or measured on the build this
skill is stamped with, by a few modders, not by GSC. A game update, the difficulty level or another mod can change
them. Read the current value from the game's own tables and prove it with a test in game before you build on it.

## 1. The bullet formula (no clamp)
Damage per hit = BaseDamage x ammo DamageMod x difficulty `Weapon_BaseDamage` x C ^ (AP - Strike) (measured in game)

- C = the target's `ArmorDifferenceCoefProjectiles`: 2 on humans, 1.5 on the mutants measured.
- **No clamp.** When AP is above Strike the hit does MORE than base damage: against Strike 0 and C 1.5, AP 1 gives
  1.5x and AP 3 about 3.4x (1.5^3).
- So any AP increase or Strike cut multiplies damage on every target it pushes past. Never model it as
  min(1, C^(AP - Strike)).

## 2. How one hit is resolved, step by step
1. Damage x the friendly-fire scaler (1.0 against hostiles).
2. Strike damage that is not an Explosion, Knife or WeaponButt hit: x the target ObjPrototype's
   `BoneDamageCoefficients` entry for the bone hit.
3. Player shooter: x the difficulty's `PlayerWeapon_HeadshotMultiplier`. Negative damage is floored at 0.
4. Protection of the target for the damage type: armor `Protection.<Type>` plus artifact and effect contributions
   plus the difficulty's `Armor_Strike_Add` / `NPC_Armor_Strike_Add`, clamped to the `ObjEffectMaxParamsPrototypes`
   MaxValue, then the effect modifiers. The Strike cap is 4.5 [cfg].
5. Coefficient by damage source (`EDamageSource`):
   - Bullet, BulletHeavy, Buckshot, StrikeVfEOneshot: `ArmorDifferenceCoefProjectiles`.
   - ShockWave, BiteSmall, BiteLarge, CutSmall, CutLarge, RamSmall, RamLarge, Knife, WeaponButt:
     `ArmorDifferenceCoefMeleeAttacks`.
   - Explosion and everything else: 1.0.
6. A hit flagged to ignore armor stops here with the damage so far.
7. Exponential term = coefficient ^ (piercing - protection), only when piercing is not 0 and the type is Strike;
   otherwise 1.
8. Deflect roll (never for explosions, nor for hits whose instigator is not an ordinary object, such as anomaly
   hits or hits with no instigator): chance = piercing - protection + 1,
   clamped between `ArmorDeflectMinChance` and `ArmorDeflectMaxChance`; the hit counts as deflected when a random
   0..1 number is above the chance.
9. Armor term:
   - Burn, Shock, ChemicalBurn, PSY, Fall, SteamBurn: x (100 - protection) / 100. Radiation and other types are
     untouched here.
   - Strike from an anomaly, an explosion, or a knife / weapon butt: x max(0, 1 - k x min(protection / 5, 1)), with
     k = `StrikeAnomalyArmorDifferenceCoef`, `ExplosionArmorDifferenceCoef` or `PlayerMeleeArmorDifferenceCoef`
     (the 5 is a CoreVariable). Strike hits with no instigator skip the term.
   - Any other Strike hit (plain bullets): only when deflected, x `ArmorDeflectDamageCoefHuman` or
     `ArmorDeflectDamageCoefMutant`.
10. Final damage = armor term x exponential term.

## 3. What it means per damage source
- **Bullets:** final = BaseDamage x `BoneDamageCoefficients[bone]` x `ArmorDifferenceCoefProjectiles` ^
  (ArmorPiercing - Protection.Strike) x (on 7% of hits: `ArmorDeflectDamageCoef`). Human NPCs have coefficient 2.0
  [cfg]: each point of protection above the bullet's piercing halves damage, each point of piercing above protection
  doubles it. Mutants use 1.3 to 1.5 [cfg], so armor matters much less for them. The exponent dominates every number
  in the weapon files.
- **Deflect is a flat 7% roll and RAISES damage.** `ArmorDeflectMinChance` = `ArmorDeflectMaxChance` = 0.93 [cfg], so
  the clamp discards piercing - protection + 1; a deflect multiplies damage by 1.5 (`ArmorDeflectDamageCoefHuman` and
  `...Mutant`, both 1.5 [cfg]) despite the name. How the deflect flag drives VFX or sound was not traced.
- **Explosions:** coefficient 1.0, so no exponential term and no deflect; only the linear term
  1 - k x min(protection / 5, 1) with `ExplosionArmorDifferenceCoef` k = 0.5 [cfg, the kit's `CoreVariables.cfg`]:
  at most 50% less, 45% at the Strike cap 4.5.
- **Anomaly strikes:** `StrikeAnomalyArmorDifferenceCoef` k = 1.0 [cfg]: full protection (protection / 5) comes off
  linearly.
- **Knife / weapon butt:** both terms, `ArmorDifferenceCoefMeleeAttacks` ^ (piercing - protection) and
  1 - 0.6 x min(protection / 5, 1) (`PlayerMeleeArmorDifferenceCoef` 0.6 [cfg]).
- **Non-strike damage** (Burn, Shock, ChemicalBurn, PSY, Fall, SteamBurn): flat damage x (100 - protection) / 100,
  protections capped at 90 [cfg].
- **Health** is only the pool: player `MaxHP` = 100, human NPC base 200 [cfg], scaled by the difficulty's `NPC_HP`;
  `HPThresholdToKill` = 0.1 [cfg]. Nothing in the armor chain reads HP.
- `ArmorDifferenceCoefProjectiles` / `...MeleeAttacks` are stored as 16-bit half-floats on the ObjPrototype and are
  parsed by hand: no validation. The deflect and armor-difference CoreVariables have compiled-in defaults that
  `CoreVariables.cfg` overwrites at load: the cfg values are authoritative.
- Not traced: how ammo `ArmorPiercingMod` / `DamageMod` fold into piercing and BaseDamage; the difficulty multipliers
  (`NPC_Weapon_BaseDamage`, `Weapon_BaseDamage`, `NPCToPlayerDamageScaler`, `Mutant_BaseDamage`), which apply before
  step 1; how a hit is tagged as anomaly-caused.

## 4. Inputs and where they live
| Input | Where |
|---|---|
| BaseDamage, ArmorPiercing (weapon) | `WeaponData/CharacterWeaponSettingsPrototypes/` (player or NPC record) |
| DamageMod, ArmorPiercingMod (ammo) | `ItemPrototypes/AmmoPrototypes.cfg` |
| Difficulty multiplier | `DifficultyPrototypes` `Weapon_BaseDamage`: Medium 1.0, Hard 0.75 |
| Mutant Strike, HP, body-part coefficients | `ObjPrototypes` (`VitalParams.MaxHP`) |
| Human `BoneDamageCoefficients`, `ArmorDifferenceCoefProjectiles` | `ObjPrototypes/GeneralNPCObjPrototypes.cfg` |
| NPC armor | the worn body armor item's `ProtectionNPC.Strike` (`ItemPrototypes/ArmorPrototypes.cfg`) |
| Deflect and armor-difference coefficients | `CoreVariables.cfg` |
| Armor upgrades | percentage effects in `EffectPrototypes` |

- Vanilla HP: humans 100; Snork 150, Bloodsucker 500, Chimera 1400, Pseudogiant 2500.
- Human head coefficient 6 in vanilla.
- Flesh, BoggyFlesh, Boar and Blinddog have Body and Limbs coefficient 1.0: any non-head hit counts the same.
- Human base `Protection.Strike` is 0, on a root named by position (`[0]`; patching such roots: stalker2-cfg).
- Grenades carry an ArmorPiercing value too (F1: 4); per section 3, explosions get no exponential term.

## 5. Worked example
Player AK-74 into a human NPC in a Zorya suit, body shot; inputs [cfg].

| Input | Value | Authored in |
|---|---|---|
| `BaseDamage` / `ArmorPiercing` | 23.0 / 1.0 | `GunAK74_ST_Player`, `PlayerWeaponSettingsPrototypes.cfg` |
| `Protection.Strike` | 2.0 | `Zorya_Neutral_Armor`, `ItemPrototypes/ArmorPrototypes.cfg` |
| `BoneDamageCoefficients` | Body 1.0, Head 6.0, Limbs 0.7 | `ObjPrototypes/GeneralNPCObjPrototypes.cfg` |
| `ArmorDifferenceCoefProjectiles` | 2.0 | same |

23 x 1.0 x 2^(1 - 2) = 11.5 off 200 HP, about 18 shots.

| Change | Multiplier | Damage |
|---|---|---|
| headshot (6.0) | 6 x 0.5 | 69.0 |
| unarmored (protection 0) | 2^1 | 46.0 |
| best armor (protection 4.5, the cap) | 2^-3.5 = 0.088 | 2.0 |
| AP ammo, IF `ArmorPiercingMod` 0.5 adds, giving piercing 1.5 [inferred] | 2^-0.5 | 16.3 |
| deflect roll fires | x 1.5 | 17.3 |

Protection 2.0 to 4.5 against this rifle is a 5.7x survivability swing.

## 6. Where the two sources differ
**Caution:** where two sources disagree, neither is settled. Do not pick one because it reads more confident: tell
the user the point is open, and test it in game on the current build before a design relies on it.
Both agree on the core: C ^ (AP - Strike) with no clamp, 2 on humans. Not reconciled, so test before relying on
either side:
- **Human NPC health.** Measured in game: humans behave as 100 HP, down at about 60 damage (section 7). Cfg reading:
  human NPC base 200, scaled by the difficulty's `NPC_HP`, with `HPThresholdToKill` 0.1; the worked example counts
  about 18 shots against 200 HP.
- **Deflect.** The measured formula has no deflect term. The hit resolution has a 7% roll that multiplies a
  bullet's damage by 1.5.
- **Which armor field an NPC uses.** Section 4 and the armor reference of this skill: NPC wearers use
  `ProtectionNPC`. The worked example reads `Protection.Strike` for an NPC wearer.
- **Ammo and difficulty.** The measured formula includes ammo DamageMod, ammo AP and difficulty
  `Weapon_BaseDamage`; the hit resolution leaves them untraced.

## 7. Buckshot, and humans going down
- Buckshot: `FractionCount` 12 x `DamageMod` 0.084, so a full pattern is about 1.0 x BaseDamage. The pattern counts
  like one bullet: there is no per-pellet multiplication (measured in game).
- Human NPCs go DOWN after about 60 damage and the next hit kills, unless a single hit takes them from full to 0
  (measured in game).
- NPC corpses carry no lootable armor, so the suit cannot be identified from the body.

Sections 2, 3 and 5 and the cfg side of section 6:
Adapted from the Stalker 2 modding harness (github.com/noahsemus/stalker2-modding-harness, MIT, copyright Noah Semus); this part was contributed there by sdwvit.
