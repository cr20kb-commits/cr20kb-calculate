#!/usr/bin/env sh
set -eu

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Usage: $0 PLAYLIST_URL [SECONDS]" >&2
  exit 2
fi

playlist_url=$1
seconds=${2:-60}
case "$seconds" in
  *[!0-9]*|'') echo "SECONDS must be an integer" >&2; exit 2 ;;
esac
if [ "$seconds" -lt 10 ] || [ "$seconds" -gt 300 ]; then
  echo "SECONDS must be between 10 and 300" >&2
  exit 2
fi

if docker info >/dev/null 2>&1; then
  docker_with_sudo=0
elif command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null; then
  docker_with_sudo=1
else
  echo "Docker is installed, but this user cannot access the Docker daemon." >&2
  echo "Run the test from an account with Docker access or sudo permission." >&2
  exit 1
fi

docker_cli() {
  if [ "$docker_with_sudo" -eq 1 ]; then
    sudo docker "$@"
  else
    docker "$@"
  fi
}

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
project_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
test_dir="$project_dir/.local-access-test"
image="cr20kb-offline-video-saver:host-access-test"

cleanup() {
  rm -rf -- "$test_dir"
  docker_cli image rm -f "$image" >/dev/null 2>&1 || true
}
trap cleanup EXIT HUP INT TERM

rm -rf -- "$test_dir"
mkdir -p -- "$test_dir"
chmod 0777 "$test_dir"

printf '%s\n' "Testing anonymous YouTube media access from this host."
printf 'Only the first %s seconds of the first playlist item will be fetched.\n' "$seconds"
if [ "$docker_with_sudo" -eq 1 ]; then
  printf '%s\n' "Using sudo for Docker access."
fi

cd "$project_dir"
docker_cli build -t "$image" .

docker_cli run --rm \
  --mount "type=bind,source=$test_dir,target=/test" \
  --entrypoint /usr/local/bin/yt-dlp-cr20kb \
  "$image" \
  --ignore-config \
  --playlist-items 1 \
  --download-sections "*0-$seconds" \
  --force-keyframes-at-cuts \
  --no-warnings \
  --js-runtimes node \
  --format 'bv*[height<=480]+ba/b[height<=480]/b' \
  --merge-output-format mkv \
  --paths /test \
  --output '%(id)s.%(ext)s' \
  --print 'after_move:filepath' \
  "$playlist_url"

result=$(find "$test_dir" -maxdepth 1 -type f -size +0c -print -quit)
if [ -z "$result" ]; then
  echo "The command exited without a non-empty media sample." >&2
  exit 1
fi

bytes=$(wc -c < "$result" | tr -d ' ')
printf 'SUCCESS: media access works from this host. Temporary sample: %s bytes.\n' "$bytes"
