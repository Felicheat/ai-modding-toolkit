# Rendering facts: reflections, ray tracing, NPC hair

What a mod can and cannot change in reflections and hair, on game 2.1.0.
Adapted from the Stalker 2 modding harness by Noah Semus (github.com/noahsemus/stalker2-modding-harness, MIT).

## Reflections and ray tracing
- **No hardware ray tracing is possible from paks, ini or shaders.** Retail and the Zone Kit editor were both built without
  ray tracing support (a compile-time switch), and the retail global shader map and material shader archives hold no ray
  tracing shaders. The game was cooked with `r.RayTracing=False` (retail `Stalker2/Config/DefaultEngine.ini`);
  `r.Lumen.HardwareRayTracing=True` next to it is a dead leftover. The `r.Lumen.HardwareRayTracing*` cvars are present
  but inert.
- Lumen is software only: screen traces, then mesh SDFs (only up to `r.Lumen.TraceMeshSDFs.TraceDistance` from the
  surface, shared with GI), then the global SDF + surface cache. Vanilla `ReflectionQuality@3` sets
  `r.Lumen.Reflections.TraceMeshSDFs=0`.
- Water is Single Layer Water. Its Lumen reflection pass never traces mesh SDFs (opaque pass only), is never temporally
  denoised and always runs at full resolution: off-screen water reflections come from the global SDF
  (`r.LumenScene.GlobalSDF.Resolution`) + surface cache. `r.Water.SingleLayer.Reflection` 3 forces SSR.
- `r.Nanite.DisableFallbackMeshes` is a GSC cvar ("saves extra VRAM used by nanite fallback"); retail sets it True.
- A user `%LOCALAPPDATA%/Stalker2/Saved/Config/Windows/Engine.ini` is not present by default.
- `r.ReflectionMethod` is overruled by the GSC cvar `r.ReflectionMethod.Override` (scalability sets it to 1 = Lumen on
  every `ReflectionQuality` level): to switch reflection method set the `.Override` cvar (2 = SSR; a user saw the change).
  The same pattern exists for `r.DynamicGlobalIlluminationMethod.Override`.
- Planar reflections do not show: the code and global shaders are in retail, `r.AllowGlobalClipPlane=False` (only a
  warning in UE 5.5), and a `PlanarReflection` actor spawned at the player's feet at runtime got its
  `PlanarReflectionComponent`, but no mirror image appeared with Lumen or SSR reflections. Characters occluding the
  background in reflections (screen traces have no data behind them; the fallback is the SDF / surface cache, which has
  no skinned meshes) therefore have no fix short of ray tracing.

## NPC hair (Groom)
- NPC hair is Groom (HairStrands): each hairstyle = a strands groom `..._STR` plus a cards groom `..._CAR` in
  `AdditionalGrooms` (`GroomGeneratorPrototypes.cfg`; faces via `AttachMeshPrototypes.cfg` `GroomPrototypeSID`), quality
  copies picked by `mg.HairQuality`.
- Strands LODs are visible only at close-up screen sizes (head hair STR LOD2 invisible below 0.35; CAR LOD0 invisible),
  so strands appear only in dialogue and cutscene close-ups. Stock 5.5 groom LOD has no hysteresis.
- Dialogue: FOV 90 to 70 and DOF f/32 (`CoreVariables.cfg`); the GSC cvar `ai.AgentLODBiasForCinematicsAndDialogs`
  (default -1) changes NPC mesh LOD. GSC cvar `r.HairStrands.ForceLOD` ("Force the hair LOD to this value", default -1).
- GSC loads groom data asynchronously at every LOD (`DefaultEngine.ini`:
  `r.HairStrands.Strands/Cards.BulkData.AsyncLoading=10`, stock -1 = synchronous; `ReleaseAfterUse=1`). Until a groom
  LOD's curves have streamed in, that LOD is not drawn, and a finer LOD (more curves) loads again.
- Strands resources themselves always allocate asynchronously (hard-coded; the cvar covers guides and cards only), and a
  groom whose data is not ready after a face mesh LOD change is not drawn that frame: the first strands use per
  hairstyle and per mesh LOD blinks for a frame or two.
- `ForceLOD 1` + `AgentLODBiasForCinematicsAndDialogs 0` did not stop the dialogue-start hair flicker; it stopped only
  after the same conversation was entered a few times.
