#!/usr/bin/env bash
#
# check_size.sh — Deterministic Tier-1 size + line-length check for
# Bash scripts. Emits a JSON ARRAY of two envelopes (rule_id="size",
# rule_id="line-length") per scripts/_common.py.
#
# Bash's lack of data structures and error handling stops scaling past
# ~300 non-blank lines; this check WARNs at the threshold. Per-line
# length is also flagged at >100 chars. Both are WARN — coaching, not
# blocking.
#
# Usage:
#   check_size.sh <path> [<path> ...]
#
# Paths may be .sh files or directories (top-level only).
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
readonly MAX_LINE_LENGTH=100

readonly REQUIRED_CMDS=(awk find basename head python3)

readonly RECIPE_SIZE='Past 300 non-blank lines, Bash exhausts its scaling envelope (no data structures, weak error handling, hard-to-debug control flow). Extract cohesive sections into _lib_*.sh helpers and `source` them from a smaller orchestrator, or rewrite in Python via /build:build-python-script.'

readonly RECIPE_LINE_LENGTH='Break long lines with `\` continuation, or extract complex pipelines into named helper functions. Keep lines under 100 characters; the formatter (`shfmt`) cannot fix this — it requires authorial judgment about where the natural break is.'

usage() {
  cat <<'EOF'
check_size.sh — Flag Bash scripts exceeding size or line-length thresholds.

Usage:
  check_size.sh <path> [<path> ...]

Arguments:
  <path>   A .sh file or directory to scan (top-level files only).

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

is_bash_script() {
  local file="$1"
  case "${file}" in
    *.sh | *.bash) return 0 ;;
  esac
  local first
  first="$(head -n 1 "${file}" 2>/dev/null || true)"
  case "${first}" in
    "#!/usr/bin/env bash" | "#!/bin/bash" | "#!/usr/bin/env -S bash"*) return 0 ;;
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
    if is_bash_script "${target}"; then
      emit_raw "${target}"
    fi
  elif [[ -d "${target}" ]]; then
    while IFS= read -r file; do
      if is_bash_script "${file}"; then
        emit_raw "${file}"
      fi
    done < <(
      find "${target}" -maxdepth 1 -type f \
        \( -name '*.sh' -o -name '*.bash' -o ! -name '*.*' \) 2>/dev/null
    )
  else
    printf '%s: path not found: %s\n' "${PROGNAME}" "${target}" >&2
    return 64
  fi
}

readonly EMIT_PY='
import os
import sys

sys.path.insert(0, os.environ["CHECK_BASH_SCRIPT_DIR"])
from _common import emit_json_finding, emit_rule_envelope, print_envelope

recipes = {
    "size": os.environ["CHECK_BASH_RECIPE_SIZE"],
    "line-length": os.environ["CHECK_BASH_RECIPE_LINE_LENGTH"],
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
  CHECK_BASH_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_BASH_RECIPE_SIZE="${RECIPE_SIZE}" \
    CHECK_BASH_RECIPE_LINE_LENGTH="${RECIPE_LINE_LENGTH}" \
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
