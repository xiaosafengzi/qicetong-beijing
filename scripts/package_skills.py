from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
out = root / "artifacts" / "nexent-skills"
out.mkdir(parents=True, exist_ok=True)
for skill in sorted((root / "nexent" / "skills").iterdir()):
    if not (skill / "SKILL.md").exists():
        continue
    with zipfile.ZipFile(out / f"{skill.name}.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in skill.rglob("*"):
            if file.is_file():
                archive.write(file, file.relative_to(skill))
    print(out / f"{skill.name}.zip")
