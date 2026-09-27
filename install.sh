#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
TARGET="both"
SCOPE="user"
PROJECT_DIR="$PWD"
SELECTED=()
SELECTOR_PROVIDED=0
FORCE=0
DRY_RUN=0
LIST_ONLY=0

usage() {
  cat <<'EOF'
Usage: ./install.sh [options]

Install converted Cursor skills for Claude Code and/or Codex.

Options:
  --target claude|codex|both   Installation target (default: both)
  --scope user|project        User or project installation (default: user)
  --project-dir PATH          Project root for --scope project (default: cwd)
  --skill NAME                Install one skill; repeat to select more
  --force                     Replace conflicts after creating timestamped backups
  --dry-run                   Print operations without changing files
  --list                      List available skill names and exit
  -h, --help                  Show this help
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      [ "$#" -ge 2 ] || die "--target requires a value"
      TARGET=$2
      shift 2
      ;;
    --scope)
      [ "$#" -ge 2 ] || die "--scope requires a value"
      SCOPE=$2
      shift 2
      ;;
    --project-dir)
      [ "$#" -ge 2 ] || die "--project-dir requires a value"
      PROJECT_DIR=$2
      shift 2
      ;;
    --skill)
      [ "$#" -ge 2 ] || die "--skill requires a value"
      [ -n "$2" ] || die "--skill requires a non-empty value"
      SELECTOR_PROVIDED=1
      SELECTED+=("$2")
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --list)
      LIST_ONLY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

case "$TARGET" in claude|codex|both) ;; *) die "invalid target: $TARGET" ;; esac
case "$SCOPE" in user|project) ;; *) die "invalid scope: $SCOPE" ;; esac
[ -d "$SCRIPT_DIR/skills/claude-code/skills" ] || die "missing generated skills; run scripts/build_skills.py"
[ -d "$SCRIPT_DIR/skills/codex" ] || die "missing generated skills; run scripts/build_skills.py"

if [ "$LIST_ONLY" -eq 1 ]; then
  find "$SCRIPT_DIR/skills/codex" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | LC_ALL=C sort
  exit 0
fi

if [ "$SCOPE" = "project" ]; then
  [ -d "$PROJECT_DIR" ] || die "project directory does not exist: $PROJECT_DIR"
  PROJECT_DIR=$(CDPATH='' cd -- "$PROJECT_DIR" && pwd)
fi

if [ "$SELECTOR_PROVIDED" -eq 1 ]; then
  for requested in "${SELECTED[@]}"; do
    [ -d "$SCRIPT_DIR/skills/codex/$requested" ] || die "unknown skill: $requested"
  done
fi

is_selected() {
  candidate=$1
  [ "$SELECTOR_PROVIDED" -eq 0 ] && return 0
  for requested in "${SELECTED[@]}"; do
    [ "$requested" = "$candidate" ] && return 0
  done
  return 1
}

destination_for() {
  platform=$1
  if [ "$SCOPE" = "project" ]; then
    if [ "$platform" = "claude-code" ]; then
      printf '%s/.claude/skills\n' "$PROJECT_DIR"
    else
      printf '%s/.agents/skills\n' "$PROJECT_DIR"
    fi
  elif [ "$platform" = "claude-code" ]; then
    printf '%s/skills\n' "${CLAUDE_CONFIG_DIR:-${HOME:?HOME is required}/.claude}"
  else
    printf '%s/skills\n' "${CODEX_HOME:-${HOME:?HOME is required}/.codex}"
  fi
}

backup_for() {
  platform=$1
  name=$2
  destination=$3
  timestamp=$4
  if [ "$platform" = "codex" ]; then
    if [ "$SCOPE" = "project" ]; then
      printf '%s/.agents/skill-backups/%s.backup.%s\n' "$PROJECT_DIR" "$name" "$timestamp"
    else
      printf '%s/skill-backups/%s.backup.%s\n' \
        "${CODEX_HOME:-${HOME:?HOME is required}/.codex}" "$name" "$timestamp"
    fi
  else
    printf '%s.backup.%s\n' "$destination" "$timestamp"
  fi
}

install_platform() {
  platform=$1
  destination_root=$(destination_for "$platform")
  source_root="$SCRIPT_DIR/skills/$platform"
  if [ "$platform" = "claude-code" ]; then
    source_root="$source_root/skills"
  fi
  timestamp=$(date '+%Y%m%d%H%M%S')

  if [ "$DRY_RUN" -eq 0 ]; then
    mkdir -p "$destination_root"
  fi

  found=0
  for source_skill in "$source_root"/*; do
    [ -d "$source_skill" ] || continue
    name=${source_skill##*/}
    is_selected "$name" || continue
    found=$((found + 1))
    destination="$destination_root/$name"

    if [ -d "$destination" ] && diff -qr "$source_skill" "$destination" >/dev/null 2>&1; then
      printf 'unchanged %s: %s\n' "$platform" "$name"
      continue
    fi
    if [ -e "$destination" ] && [ "$FORCE" -eq 0 ]; then
      printf 'skipped   %s: %s (already exists; use --force)\n' "$platform" "$name"
      continue
    fi
    if [ "$DRY_RUN" -eq 1 ]; then
      if [ -e "$destination" ]; then
        backup=$(backup_for "$platform" "$name" "$destination" "$timestamp")
        printf 'would back up %s to %s\n' "$destination" "$backup"
      fi
      printf 'would install %s to %s\n' "$name" "$destination"
      continue
    fi

    temp_root=$(mktemp -d "${TMPDIR:-/tmp}/potato-skills.XXXXXX")
    staged="$temp_root/$name"
    cp -R "$source_skill" "$staged"
    if [ -e "$destination" ]; then
      backup=$(backup_for "$platform" "$name" "$destination" "$timestamp")
      [ ! -e "$backup" ] || die "backup already exists: $backup"
      mkdir -p "${backup%/*}"
      mv "$destination" "$backup"
      printf 'backed up %s to %s\n' "$destination" "$backup"
    fi
    mv "$staged" "$destination"
    rmdir "$temp_root"
    printf 'installed %s: %s\n' "$platform" "$name"
  done

  if [ "$SELECTOR_PROVIDED" -eq 1 ] && [ "$found" -eq 0 ]; then
    die "none of the requested skills exist for $platform"
  fi
}

case "$TARGET" in
  claude) install_platform claude-code ;;
  codex) install_platform codex ;;
  both)
    install_platform claude-code
    install_platform codex
    ;;
esac
