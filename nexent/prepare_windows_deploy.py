"""Apply narrow Git Bash / Windows path fixes to the supplied Nexent source."""
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "external" / "nexent-develop"
p = root / "deploy/docker/deploy.sh"
s = p.read_text(encoding="utf-8")
marker = "# Qicetong: normalize host paths for native Windows Docker Compose."
if marker not in s:
    anchor = 'SQL_DIR="$DEPLOY_ROOT/sql"\n'
    if s.count(anchor) != 1:
        raise RuntimeError("Unsupported Nexent deployment script layout")
    s = s.replace(anchor, anchor + '''
# Qicetong: normalize host paths for native Windows Docker Compose.
if command -v cygpath >/dev/null 2>&1; then
  ROOT_ENV_FILE="$(cygpath -m "$ROOT_ENV_FILE")"
  MONITORING_ENV_FILE="$(cygpath -m "$MONITORING_ENV_FILE")"
  COMPOSE_DIR="$(cygpath -m "$COMPOSE_DIR")"
fi
''')
    s = s.replace('NEXENT_USER_DIR="$HOME/nexent"', 'NEXENT_USER_DIR="${NEXENT_USER_DIR:-$ROOT_DIR/workspace}"')
    s = s.replace('echo "✅ ELASTICSEARCH_API_KEY Generated: $ELASTICSEARCH_API_KEY"', 'echo "✅ ELASTICSEARCH_API_KEY generated (value hidden)"')
s = s.replace('if [[ "$OSTYPE" == msys* ]]; then', 'if command -v cygpath >/dev/null 2>&1; then')
prefetch_marker = "# Qicetong: skip unused optional image prefetch on local deployment."
if prefetch_marker not in s:
    for function_name in ("pull_mcp_image", "pull_sandbox_image"):
        anchor = f"{function_name}() {{\n"
        if s.count(anchor) != 1:
            raise RuntimeError(f"Unsupported Nexent {function_name} layout")
        s = s.replace(anchor, anchor + f'''  {prefetch_marker}
  if [ "${{NEXENT_SKIP_OPTIONAL_PREFETCH:-0}}" = "1" ]; then
    echo "Skipping optional {function_name} image prefetch."
    return 0
  fi
''')
p.write_text(s, encoding="utf-8", newline="\n")

# Keep the official v2.6.0 images for every service except the backend image
# that carries the narrow Ollama/CodeAgent compatibility overlay.
common = root / "deploy/common/common.sh"
common_text = common.read_text(encoding="utf-8")
overlay_marker = "# Qicetong: use the local backend compatibility overlay when provided."
if overlay_marker not in common_text:
    anchor = '  export NEXENT_IMAGE="${NEXENT_IMAGE:-nexent/nexent:$version}"\n'
    if common_text.count(anchor) != 1:
        raise RuntimeError("Unsupported Nexent image selection layout")
    common_text = common_text.replace(
        anchor,
        f'''  {overlay_marker}
  if [ -n "${{QICETONG_NEXENT_IMAGE:-}}" ]; then
    export NEXENT_IMAGE="$QICETONG_NEXENT_IMAGE"
  fi
{anchor}''',
    )
    common.write_text(common_text, encoding="utf-8", newline="\n")
print("Nexent Windows deployment path fixes ready.")
