#!/usr/bin/env bash
# Full regression: YAML validation + ELF compilation + test run + markdown report.
# Extends check-cores.sh by adding test execution (phase 3) and a report in reports/.
#
# Usage: bash scripts/run-cores.sh [options]
#
#   --no-update                Skip upstream fetch + merge.
#   --cores=X,Y                Include only configs whose name contains X or Y (substring match).
#   --no-exclude-cores         Clear default core exclusion list (cvw,cva6) — run all cores.
#   --exclude-cores-extra=X,Y  Append to default core exclusion list (cvw,cva6).
#   --skip-yaml                Skip YAML validation (assume already valid).
#   --skip-elf                 Skip ELF compilation (use existing ELFs in work/).
#   --yaml-only                Only validate YAML; skip ELF and test run.
#   --no-run                   Build (YAML + ELF) but skip test run.
#   --no-exclude               Include Sm and PMPSm (normally excluded).
#   --exclude-extra=X,Y        Append to default exclusion list (Sm,PMPSm).
#   --extensions=X,Y           Limit ELF generation to specific extensions.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

# ── Argument parsing ──────────────────────────────────────────────────────────
NO_UPDATE=false
CORES_FILTER=""
EXCLUDE_CORES_BASE="cvw,cva6"
EXCLUDE_CORES_EXTRA=""
SKIP_YAML=false
SKIP_ELF=false
YAML_ONLY=false
NO_RUN=false
EXCLUDE_BASE="Sm,PMPSm,SsstrictSm"
EXCLUDE_EXTRA=""
EXTENSIONS_ARG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-update)              NO_UPDATE=true ;;
        --cores=*)                CORES_FILTER="${1#--cores=}" ;;
        --no-exclude-cores)       EXCLUDE_CORES_BASE="" ;;
        --exclude-cores-extra=*)  EXCLUDE_CORES_EXTRA="${1#--exclude-cores-extra=}" ;;
        --skip-yaml)              SKIP_YAML=true ;;
        --skip-elf)               SKIP_ELF=true ;;
        --yaml-only)              YAML_ONLY=true ;;
        --no-run)                 NO_RUN=true ;;
        --no-exclude)             EXCLUDE_BASE="" ;;
        --exclude-extra=*)        EXCLUDE_EXTRA="${1#--exclude-extra=}" ;;
        --extensions=*)           EXTENSIONS_ARG="EXTENSIONS=${1#--extensions=}" ;;
        *)                        echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
    shift
done

COMBINED_EXCLUDE_CORES="${EXCLUDE_CORES_BASE}${EXCLUDE_CORES_BASE:+${EXCLUDE_CORES_EXTRA:+,}}${EXCLUDE_CORES_EXTRA}"
COMBINED_EXCLUDE="${EXCLUDE_BASE}${EXCLUDE_BASE:+${EXCLUDE_EXTRA:+,}}${EXCLUDE_EXTRA}"
EXCLUDE_ARG="EXCLUDE_EXTENSIONS=${COMBINED_EXCLUDE}"

# ── Upstream sync ─────────────────────────────────────────────────────────────
if [[ "$NO_UPDATE" == false ]]; then
    echo "Syncing with upstream/act4 ..."
    echo ""

    if ! git fetch upstream act4 2>&1; then
        echo ""
        echo "ERROR: git fetch upstream act4 failed. Check network / SSH key." >&2
        exit 1
    fi

    new_commits=$(git log HEAD..upstream/act4 --oneline 2>/dev/null)
    if [[ -z "$new_commits" ]]; then
        echo "Already up to date with upstream/act4."
    else
        echo "New commits from upstream:"
        echo "$new_commits" | sed 's/^/  /'
        echo ""
        if ! git merge upstream/act4 --no-edit 2>&1; then
            echo ""
            echo "ERROR: merge conflict — aborting." >&2
            git merge --abort 2>/dev/null || true
            echo "Resolve conflicts manually, then re-run with --no-update." >&2
            exit 1
        fi
    fi
    echo ""
fi

# ── Config discovery ──────────────────────────────────────────────────────────
mapfile -t ALL_CONFIGS < <(find config/cores -name "test_config.yaml" | sort)

if [[ ${#ALL_CONFIGS[@]} -eq 0 ]]; then
    echo "No configs found under config/cores/" >&2
    exit 1
fi

# Filters match against the path relative to config/cores/ (e.g. "cva6/cv32a65x"),
# so --exclude-cores=cva6 matches the group and --cores=cv32e40p matches the config name.
cfg_relpath() { echo "${1#config/cores/}"; }

# Apply exclude-cores filter
if [[ -n "$COMBINED_EXCLUDE_CORES" ]]; then
    IFS=',' read -ra EXCL_TERMS <<< "$COMBINED_EXCLUDE_CORES"
    FILTERED=()
    for cfg in "${ALL_CONFIGS[@]}"; do
        rel=$(cfg_relpath "$cfg")
        excluded=false
        for term in "${EXCL_TERMS[@]}"; do
            if [[ "$rel" == *"$term"* ]]; then
                excluded=true
                break
            fi
        done
        [[ "$excluded" == false ]] && FILTERED+=("$cfg")
    done
    ALL_CONFIGS=("${FILTERED[@]}")
fi

# Apply --cores include filter
if [[ -n "$CORES_FILTER" ]]; then
    IFS=',' read -ra CORE_TERMS <<< "$CORES_FILTER"
    CONFIGS=()
    for cfg in "${ALL_CONFIGS[@]}"; do
        rel=$(cfg_relpath "$cfg")
        for term in "${CORE_TERMS[@]}"; do
            if [[ "$rel" == *"$term"* ]]; then
                CONFIGS+=("$cfg")
                break
            fi
        done
    done
    if [[ ${#CONFIGS[@]} -eq 0 ]]; then
        echo "No configs matched --cores=$CORES_FILTER (after exclusions: ${COMBINED_EXCLUDE_CORES:-none})" >&2
        echo "Available configs:" >&2
        for cfg in "${ALL_CONFIGS[@]}"; do basename "$(dirname "$cfg")"; done | sed 's/^/  /' >&2
        exit 1
    fi
    echo "Cores filter: $CORES_FILTER → ${#CONFIGS[@]} config(s) selected"
    echo ""
else
    if [[ ${#ALL_CONFIGS[@]} -eq 0 ]]; then
        echo "No configs remaining after exclusions (${COMBINED_EXCLUDE_CORES})" >&2
        exit 1
    fi
    CONFIGS=("${ALL_CONFIGS[@]}")
fi

[[ -n "$COMBINED_EXCLUDE_CORES" ]] && echo "Excluded cores: ${COMBINED_EXCLUDE_CORES}" && echo ""

# Tracking state per config
declare -A yaml_status   # pass | FAIL | skip
declare -A elf_status    # pass | FAIL | skip
declare -A run_status    # pass | FAIL | no-cmd | skip | n/a
declare -A run_counts    # "N/total" or ""
declare -A fail_details  # human-readable failure info

fail=0
pass_yaml=0
pass_elf=0
pass_run=0

# ── Phase 1: YAML validation ──────────────────────────────────────────────────
if [[ "$SKIP_YAML" == true ]]; then
    echo "Phase 1: YAML validation — skipped (--skip-yaml)"
    echo ""
    for cfg in "${CONFIGS[@]}"; do
        name=$(basename "$(dirname "$cfg")")
        yaml_status[$name]="skip"
    done
else
    echo "Phase 1: YAML validation (${#CONFIGS[@]} configs)"
    echo ""

    for cfg in "${CONFIGS[@]}"; do
        name=$(basename "$(dirname "$cfg")")
        dir=$(dirname "$cfg")

        if ! err=$(python3 -c "import yaml,sys; yaml.safe_load(open('$cfg'))" 2>&1); then
            echo "  FAIL  $name  [test_config.yaml]"
            yaml_status[$name]="FAIL"
            fail_details[$name]="YAML (test_config.yaml): $err"
            ((fail++))
            continue
        fi

        udb_config=$(python3 -c "
import yaml
cfg = yaml.safe_load(open('$cfg'))
print(cfg.get('udb_config') or '')
" 2>/dev/null)

        if [[ -n "$udb_config" ]]; then
            udb_path="$dir/$udb_config"
            if [[ ! -f "$udb_path" ]]; then
                echo "  FAIL  $name  [udb_config: $udb_config not found]"
                yaml_status[$name]="FAIL"
                fail_details[$name]="YAML (udb_config): file not found: $udb_path"
                ((fail++))
                continue
            fi
            if ! err=$(python3 -c "import yaml; yaml.safe_load(open('$udb_path'))" 2>&1); then
                echo "  FAIL  $name  [$udb_config]"
                yaml_status[$name]="FAIL"
                fail_details[$name]="YAML ($udb_config): $err"
                ((fail++))
                continue
            fi
        fi

        echo "  pass  $name"
        yaml_status[$name]="pass"
        ((pass_yaml++))
    done
    echo ""
fi

# ── Phase 2: ELF generation ───────────────────────────────────────────────────
if [[ "$YAML_ONLY" == true ]]; then
    echo "Phase 2: ELF generation — skipped (--yaml-only)"
    echo ""
    for cfg in "${CONFIGS[@]}"; do
        name=$(basename "$(dirname "$cfg")")
        elf_status[$name]="skip"
    done
elif [[ "$SKIP_ELF" == true ]]; then
    echo "Phase 2: ELF generation — skipped (--skip-elf, using existing ELFs)"
    echo ""
    for cfg in "${CONFIGS[@]}"; do
        name=$(basename "$(dirname "$cfg")")
        elf_status[$name]="skip"
    done
else
    exclude_display="${EXCLUDE_ARG#EXCLUDE_EXTENSIONS=}"
    echo "Phase 2: ELF generation (FAST=True, exclude=${exclude_display:-none})"
    [[ -n "$EXTENSIONS_ARG" ]] && echo "         extensions=${EXTENSIONS_ARG#EXTENSIONS=}"
    echo ""

    for cfg in "${CONFIGS[@]}"; do
        name=$(basename "$(dirname "$cfg")")

        if [[ "${yaml_status[$name]:-}" == "FAIL" ]]; then
            printf "  skip  %-40s (yaml failed)\n" "$name"
            elf_status[$name]="skip"
            continue
        fi

        log="/tmp/run-cores-elf-${name}.log"
        printf "        %-40s" "$name"

        if make CONFIG_FILES="$cfg" elfs FAST=True \
                $EXCLUDE_ARG $EXTENSIONS_ARG \
                > "$log" 2>&1; then
            echo "pass"
            elf_status[$name]="pass"
            ((pass_elf++))
        else
            echo "FAIL"
            elf_status[$name]="FAIL"
            fail_details[$name]="ELF build failed (log: $log)"
            ((fail++))
        fi
    done
    echo ""
fi

# ── Runner discovery ──────────────────────────────────────────────────────────
# Auto-prepend DV runner script dirs to PATH (and export each repo root) so
# phase 3 finds the per-ELF runners with no manual PATH setup. run-cve4.sh
# requires CVE4_DV_ROOT; the cv32e20/cv32e40x runners self-derive their root
# but honor CVE20_DV_ROOT / CVE40X_DV_ROOT when set. A pre-set env var wins;
# otherwise the default sibling-checkout location is used (skipped if absent).
declare -A DV_ROOTS=(
    [CVE4_DV_ROOT]="$REPO/../../../cv32e40p-dv-review"
    [CVE20_DV_ROOT]="$REPO/../../cv32e20-dv"
    [CVE40X_DV_ROOT]="$REPO/../../cv32e40x-dv"
    [CVE40S_DV_ROOT]="$REPO/../../cv32e40s-dv-v2"
)
for var in "${!DV_ROOTS[@]}"; do
    root="${!var:-${DV_ROOTS[$var]}}"
    [[ -d "$root" ]] || continue
    root="$(cd "$root" && pwd)"
    export "$var=$root"
    [[ -d "$root/.github/scripts" ]] && PATH="$root/.github/scripts:$PATH"
done
export PATH

# ── Phase 3: Test run ─────────────────────────────────────────────────────────
if [[ "$YAML_ONLY" == true || "$NO_RUN" == true ]]; then
    label=$([[ "$YAML_ONLY" == true ]] && echo "--yaml-only" || echo "--no-run")
    echo "Phase 3: Test run — skipped ($label)"
    echo ""
    for cfg in "${CONFIGS[@]}"; do
        name=$(basename "$(dirname "$cfg")")
        run_status[$name]="n/a"
        run_counts[$name]=""
    done
else
    echo "Phase 3: Test run"
    echo ""

    for cfg in "${CONFIGS[@]}"; do
        name=$(basename "$(dirname "$cfg")")
        cfg_dir=$(dirname "$cfg")

        # Block if earlier phase failed or was skipped due to failure
        if [[ "${yaml_status[$name]:-}" == "FAIL" || "${elf_status[$name]:-}" == "FAIL" ]]; then
            printf "  skip  %-40s (earlier phase failed)\n" "$name"
            run_status[$name]="skip"
            run_counts[$name]=""
            continue
        fi

        # Check for run_cmd.txt
        run_cmd_file="$cfg_dir/run_cmd.txt"
        if [[ ! -f "$run_cmd_file" ]]; then
            printf "  n/a   %-40s (no run_cmd.txt)\n" "$name"
            run_status[$name]="no-cmd"
            run_counts[$name]=""
            continue
        fi

        run_cmd=$(cat "$run_cmd_file")
        first_word="${run_cmd%% *}"

        # Warn if runner is not in PATH — environment issue, not a config failure
        if ! command -v "$first_word" &>/dev/null; then
            printf "  warn  %-40s (%s not in PATH)\n" "$name" "$first_word"
            run_status[$name]="no-runner"
            run_counts[$name]=""
            continue
        fi

        elf_dir="work/${name}/elfs"
        summary_log="work/${name}/summary.log"
        log="/tmp/run-cores-run-${name}.log"

        printf "        %-40s" "$name"

        if ./run_tests.py "$run_cmd" "$elf_dir" > "$log" 2>&1; then
            run_exit=0
        else
            run_exit=$?
        fi

        # Parse summary counts
        if [[ -f "$summary_log" ]]; then
            n_pass=$(grep -c "TEST PASSED" "$summary_log" 2>/dev/null || true)
            n_fail=$(grep -c "TEST FAILED\|TEST SIGRUN" "$summary_log" 2>/dev/null || true)
            n_total=$(( n_pass + n_fail ))
            run_counts[$name]="${n_pass}/${n_total}"
        else
            run_counts[$name]="?/?"
        fi

        if [[ $run_exit -eq 0 ]]; then
            echo "pass  (${run_counts[$name]})"
            run_status[$name]="pass"
            ((pass_run++))
        else
            echo "FAIL  (${run_counts[$name]})"
            run_status[$name]="FAIL"
            if [[ -f "$summary_log" ]]; then
                failed_lines=$(grep "TEST FAILED\|TEST SIGRUN" "$summary_log" 2>/dev/null | \
                               sed 's/^/    /' | head -10)
                fail_details[$name]="${fail_details[$name]:+${fail_details[$name]}$'\n'}Test failures:
${failed_lines}"
            else
                fail_details[$name]="${fail_details[$name]:+${fail_details[$name]}; }run_tests.py exit ${run_exit} (log: $log)"
            fi
            ((fail++))
        fi
    done
    echo ""
fi

# ── Phase 4: Report ───────────────────────────────────────────────────────────
mkdir -p reports
timestamp=$(date '+%Y-%m-%d_%H-%M-%S')
report_file="reports/${timestamp}.md"

git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
cores_label="${CORES_FILTER:-all (${#CONFIGS[@]} configs)}"

{
    echo "# ACT4 Core Run Report"
    echo ""
    echo "**Date:** $(date '+%Y-%m-%d %H:%M:%S')  "
    echo "**Branch:** ${git_branch}  "
    echo "**Commit:** ${git_commit}  "
    echo "**Cores:** ${cores_label}  "
    echo "**Excluded cores:** ${COMBINED_EXCLUDE_CORES:-none}  "
    [[ -n "$EXTENSIONS_ARG" ]] && echo "**Extensions:** ${EXTENSIONS_ARG#EXTENSIONS=}  "
    exclude_display="${COMBINED_EXCLUDE:-none}"
    echo "**Excluded extensions:** ${exclude_display}  "
    echo ""
    echo "---"
    echo ""
    echo "## Summary"
    echo ""
    echo "| Config | YAML | ELF | Tests | Result |"
    echo "|--------|------|-----|-------|--------|"

    for cfg in "${CONFIGS[@]}"; do
        name=$(basename "$(dirname "$cfg")")

        y="${yaml_status[$name]:-—}"
        e="${elf_status[$name]:-—}"
        r_s="${run_status[$name]:-—}"
        r_c="${run_counts[$name]:-}"

        case "$r_s" in
            pass)       r_cell="${r_c}" ;;
            FAIL)       r_cell="FAIL (${r_c})" ;;
            no-cmd)     r_cell="— (no run_cmd)" ;;
            no-runner)  r_cell="— (runner not in PATH)" ;;
            skip)       r_cell="— (skipped)" ;;
            n/a)        r_cell="— (not run)" ;;
            *)          r_cell="—" ;;
        esac

        if [[ "$y" == "FAIL" || "$e" == "FAIL" || "$r_s" == "FAIL" ]]; then
            overall="**FAIL**"
        elif [[ "$r_s" == "no-runner" ]]; then
            overall="warn (no runner)"
        elif [[ "$y" == "pass" || "$y" == "skip" ]]; then
            if [[ "$r_s" == "pass" ]]; then
                overall="pass"
            elif [[ "$r_s" == "no-cmd" || "$r_s" == "n/a" ]]; then
                overall="pass (no run)"
            else
                overall="pass"
            fi
        else
            overall="—"
        fi

        echo "| ${name} | ${y} | ${e} | ${r_cell} | ${overall} |"
    done

    echo ""

    if [[ $fail -gt 0 ]]; then
        echo "---"
        echo ""
        echo "## Failures"
        echo ""
        for name in "${!fail_details[@]}"; do
            echo "### ${name}"
            echo ""
            echo "${fail_details[$name]}"
            echo ""
            run_log="/tmp/run-cores-run-${name}.log"
            elf_log="/tmp/run-cores-elf-${name}.log"
            if [[ -f "$run_log" ]]; then
                echo "<details><summary>run_tests.py output (last 30 lines)</summary>"
                echo ""
                echo '```'
                tail -30 "$run_log"
                echo '```'
                echo ""
                echo "</details>"
            elif [[ -f "$elf_log" ]]; then
                echo "<details><summary>ELF build log (last 30 lines)</summary>"
                echo ""
                echo '```'
                tail -30 "$elf_log"
                echo '```'
                echo ""
                echo "</details>"
            fi
            echo ""
        done
    fi

    echo "---"
    echo ""
    echo "_Generated by \`scripts/run-cores.sh\` — build artifacts in \`work/\`, per-test logs in \`work/<config>/logs/\`_"
} > "$report_file"

# ── Summary ───────────────────────────────────────────────────────────────────
echo "────────────────────────────────────────────────────────────"
echo "Report: $report_file"
echo ""

if [[ "$YAML_ONLY" == true ]]; then
    echo "YAML: $pass_yaml/${#CONFIGS[@]} passed"
elif [[ "$NO_RUN" == true ]]; then
    if [[ "$SKIP_ELF" == true ]]; then
        echo "ELF: skipped (--skip-elf)"
    else
        echo "ELF: $pass_elf/${#CONFIGS[@]} passed"
    fi
else
    n_with_run=0
    for cfg in "${CONFIGS[@]}"; do
        [[ -f "$(dirname "$cfg")/run_cmd.txt" ]] && ((n_with_run++)) || true
    done
    if [[ "$SKIP_ELF" == true ]]; then
        echo "ELF: skipped (--skip-elf)"
    else
        echo "ELF: $pass_elf/${#CONFIGS[@]} passed"
    fi
    echo "Run: $pass_run/${n_with_run} runnable config(s) passed"
fi

# Count configs where runner was not in PATH
no_runner=0
for cfg in "${CONFIGS[@]}"; do
    name=$(basename "$(dirname "$cfg")")
    [[ "${run_status[$name]:-}" == "no-runner" ]] && ((no_runner++)) || true
done
if [[ $no_runner -gt 0 ]]; then
    echo ""
    echo "WARN: $no_runner config(s) skipped — runner not in PATH (re-run with PATH set + --no-update --skip-elf)"
fi

if [[ $fail -gt 0 ]]; then
    echo ""
    echo "FAIL: $fail failure(s) — see $report_file"
    echo ""
    exit 1
fi

echo "All OK."
exit 0
