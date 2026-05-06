#!/usr/bin/env bash
#
# check_size.sh — Deterministic Tier-1 size + line-length check for
# Makefiles. Emits a JSON ARRAY of two envelopes (rule_id="size",
# rule_id="line-length") per scripts/_common.py.
#
# Makefiles rot fast past ~300 non-blank lines — navigation suffers
# and the single-file advantage is lost. WARN at the threshold.
# Per-line length is also flagged at >120 chars (readability in code
# review). Both rules are WARN — coaching, not blocking.
#
# Usage:
#   check_size.sh <path> [<path> ...]
#
# Paths may be Makefile / GNUmakefile / *.mk files or directories
# (top-level only).
#
# Exit codes:
#   0   overall_status pass / warn for every emitted envelope
#   1   overall_status=fail (not produced by this script)
#   64  usage error
#   69  missing dependency
#
# Dependencies:
#   awk, find, basename, head, python3

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly MAX_NON_BLANK_LINES=300
readonly MAX_LINE_LENGTH=120

readonly REQUIRED_CMDS=(awk find basename head python3)

readonly RECIPE_SIZE='Past ~300 non-blank lines, navigation suffers and the single-file advantage is lost. Split cohesive sections into included `*.mk` files (e.g., `mk/build.mk`, `mk/test.mk`, `mk/deploy.mk`) and `include` them from the top-level Makefile. A ~120-line top-level Makefile that includes per-domain slices keeps each diff focused on one area.'

readonly RECIPE_LINE_LENGTH='Break long lines with `\` continuation, or extract the recipe body into `scripts/<name>.sh` and invoke it from the target. Long lines break side-by-side diff views and are unreadable in code review; the formatter cannot fix this — it requires authorial judgment about the natural break.'

usage() {
  cat <<'EOF'
check_size.sh — Flag Makefiles exceeding size or line-length thresholds.

Usage:
  check_size.sh <path> [<path> ...]

Arguments:
  <path>   A Makefile / GNUmakefile / *.mk file or directory (top-level).

Options:
  -h, --help   Show this help and exit.

Exit codes:
  0   overall_status pass / warn
  1   overall_status fail (not produced by this script)
  64  usage error
  69  missing dependency
EOF
}

install_hint() {
  case "${1}" in
    awk | find | basename | head) printf 'should be preinstalled on any POSIX system' ;;
    python3) printf 'install Python 3.9+' ;;
    *) printf 'see your package manager' ;;
  esac
}

preflight() {
  local missing=()
  local cmd
  for cmd in "${REQUIRED_CMDS[@]}"; do
    if ! command -v "${cmd}" >/dev/null 2>&1; then
      missing+=("${cmd}")
    fi
  done
  if [[ "${#missing[@]}" -gt 0 ]]; then
    for cmd in "${missing[@]}"; do
      printf '%s: missing required command %q. Install: %s\n' \
        "${PROGNAME}" "${cmd}" "$(install_hint "${cmd}")" >&2
    done
    exit 69
  fi
}

is_makefile() {
  local file="$1"
  local base
  base="$(basename "${file}")"
  case "${base}" in
    Makefile | GNUmakefile) return 0 ;;
    *.mk) return 0 ;;
  esac
  return 1
}

non_blank_count() {
  awk 'NF { count++ } END { print count + 0 }' "$1"
}

# Emit findings as TSV: <rule_id>\t<file>\t<line>\t<context>
# Per-line-length finding count capped at 3 per file (noise control).
emit_raw() {
  local file="$1"
  local count
  count="$(non_blank_count "${file}")"
  if [[ "${count}" -gt "${MAX_NON_BLANK_LINES}" ]]; then
    printf 'size\t%s\t1\t%s non-blank lines (threshold %s)\n' \
      "${file}" "${count}" "${MAX_NON_BLANK_LINES}"
  fi

  local emitted=0
  while IFS=: read -r lineno length; do
    if [[ "${emitted}" -ge 3 ]]; then
      break
    fi
    printf 'line-length\t%s\t%s\tline is %s chars (threshold %s)\n' \
      "${file}" "${lineno}" "${length}" "${MAX_LINE_LENGTH}"
    emitted=$((emitted + 1))
  done < <(awk -v max="${MAX_LINE_LENGTH}" '
    length($0) > max { printf "%d:%d\n", NR, length($0) }
  ' "${file}")
}

scan_path() {
  local target="$1"
  local file

  if [[ -f "${target}" ]]; then
    if is_makefile "${target}"; then
      emit_raw "${target}"
    fi
  elif [[ -d "${target}" ]]; then
    while IFS= read -r file; do
      if is_makefile "${file}"; then
        emit_raw "${file}"
      fi
    done < <(
      find "${target}" -maxdepth 1 -type f \
        \( -name 'Makefile' -o -name 'GNUmakefile' -o -name '*.mk' \) 2>/dev/null
    )
  else
    printf '%s: path not found: %s\n' "${PROGNAME}" "${target}" >&2
    return 64
  fi
}

readonly EMIT_PY='
import os
import sys

sys.path.insert(0, os.environ["CHECK_MAKEFILE_SCRIPT_DIR"])
from _common import emit_json_finding, emit_rule_envelope, print_envelope

recipes = {
    "size": os.environ["CHECK_MAKEFILE_RECIPE_SIZE"],
    "line-length": os.environ["CHECK_MAKEFILE_RECIPE_LINE_LENGTH"],
}

per_rule = {"size": [], "line-length": []}
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue
    parts = line.split("\t", 3)
    if len(parts) != 4:
        continue
    rule_id, path, lineno, context = parts
    if rule_id not in per_rule:
        continue
    try:
        line_int = int(lineno)
    except ValueError:
        line_int = 1
    per_rule[rule_id].append(
        emit_json_finding(
            rule_id=rule_id,
            status="warn",
            location={"line": line_int, "context": f"{path}: {context}"},
            reasoning=f"{path} {context}.",
            recommended_changes=recipes[rule_id],
        )
    )

envelopes = [
    emit_rule_envelope(rule_id="size", findings=per_rule["size"]),
    emit_rule_envelope(rule_id="line-length", findings=per_rule["line-length"]),
]
print_envelope(envelopes)
'

emit_envelopes() {
  CHECK_MAKEFILE_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_MAKEFILE_RECIPE_SIZE="${RECIPE_SIZE}" \
    CHECK_MAKEFILE_RECIPE_LINE_LENGTH="${RECIPE_LINE_LENGTH}" \
    python3 -c "${EMIT_PY}"
}

main() {
  if [[ "$#" -eq 0 ]]; then
    usage >&2
    exit 64
  fi

  case "${1:-}" in
    -h | --help)
      usage
      exit 0
      ;;
  esac

  preflight

  local target
  {
    for target in "$@"; do
      scan_path "${target}"
    done
  } | emit_envelopes
  # set -o pipefail propagates scan_path's path-not-found return (64).
  exit 0
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
