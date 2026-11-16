using UAssetAPI;
using UAssetAPI.UnrealTypes;

// uasset-dump <in.uasset> <out.json> [EngineVersion]
// Writes the asset as UAssetAPI JSON (name map, imports, exports with SerialOffset / SerialSize and their properties).
// The pack's scripts pass VER_UE5_5 for Zone Kit assets. Build: dotnet build -c Release
if (args.Length < 2)
{
    Console.Error.WriteLine("usage: uasset-dump <in.uasset> <out.json> [EngineVersion, e.g. VER_UE5_5; default VER_UE5_1]");
    return 2;
}
var path = args[0];
var outp = args[1];
var ver = args.Length > 2 ? Enum.Parse<EngineVersion>(args[2]) : EngineVersion.VER_UE5_1;
var asset = new UAsset(path, ver);
File.WriteAllText(outp, asset.SerializeJson());
Console.WriteLine($"OK exports={asset.Exports.Count} names={asset.GetNameMapIndexList().Count}");
return 0;
