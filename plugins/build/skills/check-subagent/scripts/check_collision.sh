#!/usr/bin/env bash
#
# check_collision.sh — Tier-3 description-collision check for subagent
# definitions. Emits a JSON ARRAY containing a single envelope
# (rule_id="description-collision") per scripts/_common.py.
#
# Computes pairwise token-set Jaccard similarity across every .md file
# in the audit scope. Flags any pair with similarity >=0.6 as a WARN —
# overlapping descriptions produce non-deterministic routing because
# the main agent has no basis to pick between two agents claiming the
# same trigger surface.
#
# Single-file scope is a no-op (no pairs to compare → empty findings,
# overall_status=pass).
#
# Usage:
#   check_collision.sh <path> [<path> ...]
#
# Exit codes:
#   0   no FAIL findings (WARN exits 0 per the Tier-1 contract)
#   1   one or more FAIL findings (not produced by this script)
#   64  usage error
#   69  missing dependency
#
# Dependencies:
#   awk, basename, find, tr, mktemp, python3

set -Eeuo pipefail
IFS=$'\n\t'

PROGNAME="$(basename "${0}")"
readonly PROGNAME

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

readonly THRESHOLD=60 # Jaccard * 100; >=60 => flag

readonly REQUIRED_CMDS=(awk basename find tr mktemp python3)

readonly RECIPE_DESCRIPTION_COLLISION='Pick one of: (1) **Merge** the two subagents into one if their capabilities are genuinely the same; (2) **Differentiate** — each description names a distinct trigger surface, distinct exclusions, distinct return artifacts; (3) **Retire** one and redirect via a deprecation note. Overlapping descriptions produce coin-flip routing — the main agent has no basis to pick between two agents claiming the same surface. Distinct vocabulary makes the routing contract deterministic.'

usage() {
  cat <<'EOF'
check_collision.sh — Flag subagent pairs with colliding descriptions.

Usage:
  check_collision.sh <path> [<path> ...]

Options:
  -h, --help   Show this help and exit.

Exit codes:
  0   no FAIL findings
  1   one or more FAIL findings (not produced)
  64  usage error
  69  missing dependency
EOF
}

install_hint() {
  case "${1}" in
    awk | basename | find | tr | mktemp) printf 'should be preinstalled on any POSIX system' ;;
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

extract_description() {
  awk '
    BEGIN { in_fm = 0; folded = 0; literal = 0; val = "" }
    /^---[[:space:]]*$/ {
      if (++fm_count == 1) { in_fm = 1; next }
      if (fm_count == 2)   { exit }
    }
    !in_fm { next }
    (folded || literal) && /^[^ \t]/ { folded = 0; literal = 0 }
    (folded || literal) && /^[[:space:]]+/ {
      line = $0
      sub(/^[[:space:]]+/, "", line)
      if (val == "") { val = line } else { val = val (folded ? " " : "\n") line }
      next
    }
    /^description:[[:space:]]*/ {
      rest = $0
      sub(/^description:[[:space:]]*/, "", rest)
      if (rest == ">" || rest == ">-") { folded = 1; next }
      if (rest == "|" || rest == "|-") { literal = 1; next }
      if (rest ~ /^".*"$/) { rest = substr(rest, 2, length(rest) - 2) }
      else if (rest ~ /^'\''.*'\''$/) { rest = substr(rest, 2, length(rest) - 2) }
      val = rest
    }
    END { print val }
  ' "$1"
}

tokenize() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | awk '
    BEGIN {
      split("the a an and or but of to for in on at by with as is are be use when not", s, " ")
      for (i in s) stop[s[i]] = 1
    }
    {
      n = split($0, tok, /[^a-z0-9]+/)
      for (i = 1; i <= n; i++) {
        if (length(tok[i]) < 3) continue
        if (tok[i] in stop) continue
        if (!(tok[i] in seen)) {
          seen[tok[i]] = 1
          print tok[i]
        }
      }
    }
  '
}

jaccard_pct() {
  local a="$1" b="$2"
  awk '
    NR == FNR { set1[$0] = 1; n1++; next }
    {
      set2[$0] = 1; n2++
      if ($0 in set1) inter++
    }
    END {
      if (n1 == 0 && n2 == 0) { print 0; exit }
      union = n1 + n2 - inter
      if (union == 0) { print 0; exit }
      printf "%d\n", int(100 * inter / union)
    }
  ' "$a" "$b"
}

gather_files() {
  local target file
  for target in "$@"; do
    if [[ -f "${target}" ]]; then
      case "${target}" in
        *.md) printf '%s\n' "${target}" ;;
      esac
    elif [[ -d "${target}" ]]; then
      find "${target}" -maxdepth 1 -type f -name '*.md' 2>/dev/null
    fi
  done
}

# TSV: <file_a>\t<file_b>\t<pct>
collect_collisions() {
  local files=("$@")
  if [[ "${#files[@]}" -lt 2 ]]; then
    return 0
  fi

  local tmpdir=""
  trap '[[ -n "${tmpdir}" ]] && rm -rf "${tmpdir}"' RETURN
  tmpdir="$(mktemp -d)"

  local i tok_file desc
  for i in "${!files[@]}"; do
    desc="$(extract_description "${files[$i]}")"
    tok_file="${tmpdir}/tok.${i}"
    if [[ -n "${desc}" ]]; then
      tokenize "${desc}" >"${tok_file}"
    else
      : >"${tok_file}"
    fi
  done

  local j pct
  for i in "${!files[@]}"; do
    for j in "${!files[@]}"; do
      if [[ "${j}" -le "${i}" ]]; then continue; fi
      if [[ ! -s "${tmpdir}/tok.${i}" ]] || [[ ! -s "${tmpdir}/tok.${j}" ]]; then
        continue
      fi
      pct="$(jaccard_pct "${tmpdir}/tok.${i}" "${tmpdir}/tok.${j}")"
      if [[ "${pct}" -ge "${THRESHOLD}" ]]; then
        printf '%s\t%s\t%s\n' "${files[$i]}" "${files[$j]}" "${pct}"
      fi
    done
  done
}

readonly EMIT_PY='
import os
import sys

sys.path.insert(0, os.environ["CHECK_SUBAGENT_SCRIPT_DIR"])
from _common import emit_json_finding, emit_rule_envelope, print_envelope

recipe = os.environ["CHECK_SUBAGENT_RECIPE_DESCRIPTION_COLLISION"]

findings = []
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue
    parts = line.split("\t", 2)
    if len(parts) != 3:
        continue
    file_a, file_b, pct = parts
    findings.append(
        emit_json_finding(
            rule_id="description-collision",
            status="warn",
            location={"line": 1, "context": f"{file_a} <-> {file_b}: similarity {pct}%"},
            reasoning=(
                f"{file_a} and {file_b} have description Jaccard "
                f"similarity {pct}% (threshold 60%). Overlapping "
                "descriptions force non-deterministic routing — the "
                "main agent has no basis to pick between two agents "
                "claiming the same trigger surface."
            ),
            recommended_changes=recipe,
        )
    )

envelope = emit_rule_envelope(rule_id="description-collision", findings=findings)
print_envelope([envelope])
if envelope["overall_status"] == "fail":
    sys.exit(1)
'

emit_envelopes() {
  CHECK_SUBAGENT_SCRIPT_DIR="${SCRIPT_DIR}" \
    CHECK_SUBAGENT_RECIPE_DESCRIPTION_COLLISION="${RECIPE_DESCRIPTION_COLLISION}" \
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

  local files=()
  while IFS= read -r f; do
    [[ -n "${f}" ]] && files+=("${f}")
  done < <(gather_files "$@")

  local rc=0
  if [[ "${#files[@]}" -lt 2 ]]; then
    : | emit_envelopes || rc=$?
  else
    collect_collisions "${files[@]}" | emit_envelopes || rc=$?
  fi
  exit "${rc}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
