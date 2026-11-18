# shellcheck shell=bash
#
# Per-host settings for the ritz room budget and the gate (AGAST #2998).
# Sourced by .claude/host-budget.sh and .claude/skills/rz-iterate/run-gate.sh.
#
#   File: ~/.config/rz/host.env       (override: RZ_HOST_ENV, for tests)
#
#   RZ_ROOMS_MEMORY_HIGH=28G   ritz-rooms.slice MemoryHigh, all rooms together
#   RZ_ROOMS_MEMORY_MAX=32G    ritz-rooms.slice MemoryMax,  all rooms together
#   RZ_GATE_SLOTS=2            gates run-gate.sh lets run at once on this host
#   RZ_TRAIN_SLOTS=1           of those, how many only merge-train gates may
#                              take (AGAST #4031; default 0).  Room gates get
#                              the rest; train gates may use any free slot.
#                              Must be below RZ_GATE_SLOTS
#   RZ_TEST_BUDGET_SCALE=1.5   the gate's ritz0 suite budget (check_test_budget.py)
#                              times this, for a host slower than its calibration
#                              shows (AGAST #4004, #4138).  run-gate.sh passes it
#                              to the gate; main.yml hands it to the budget check
#                              alone, never to pytest
#   RZ_CPU_FACTOR=1.67         this host's CPU factor for that budget, fixed
#                              (AGAST #4172).  Unset: cpu_calibrate.py measures
#                              it for a few seconds before each suite, which a
#                              busy box misreads (skronk: 1.054 for ~1.67).
#                              Measure it once, idle: cpu_calibrate.py --runs 5
#
# Every key is optional; a missing key (or no file at all) keeps the script's
# default, which is sized for omegalisk's 15.6 GiB VM (7G / 8G / 1).  Only
# hosts with more memory need the file: huburght (47 GB, 6 rooms) is the one.
# The values are per host because rooms and gates share one machine's RAM
# and cores: they live outside the repo, next to the machine they describe.
#
# The file is PARSED, never sourced: KEY=VALUE lines, '#' comments and blank
# lines only, no quotes, no expansion.  An unknown key or a malformed value is
# an error, not a silent default: a typo'd key would otherwise leave a big
# host quietly running at omegalisk's numbers.

RZ_HOST_ENV_FILE="${RZ_HOST_ENV:-${XDG_CONFIG_HOME:-$HOME/.config}/rz/host.env}"

# rz_host_env_load: fill the associative array HOST_ENV from the file.
# Returns 1 with a message on stderr if the file is malformed.
declare -A HOST_ENV=()
rz_host_env_load() {
    HOST_ENV=()
    [[ -e "$RZ_HOST_ENV_FILE" ]] || return 0
    local line key val n=0
    while IFS= read -r line || [[ -n "$line" ]]; do
        n=$((n + 1))
        # Trim surrounding whitespace; skip blanks and comments.
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [[ -z "$line" || "$line" == \#* ]] && continue
        if [[ ! "$line" =~ ^([A-Z_]+)=(.*)$ ]]; then
            echo "error: $RZ_HOST_ENV_FILE:$n: expected KEY=VALUE: '$line'" >&2
            return 1
        fi
        key="${BASH_REMATCH[1]}"
        val="${BASH_REMATCH[2]}"
        case "$key" in
            RZ_ROOMS_MEMORY_HIGH | RZ_ROOMS_MEMORY_MAX)
                [[ "$val" =~ ^[1-9][0-9]*[KMG]?$ ]] || {
                    echo "error: $RZ_HOST_ENV_FILE:$n: $key must be a size like 28G: '$val'" >&2
                    return 1
                }
                ;;
            RZ_GATE_SLOTS)
                [[ "$val" =~ ^[1-9][0-9]*$ ]] || {
                    echo "error: $RZ_HOST_ENV_FILE:$n: $key must be a whole number >= 1: '$val'" >&2
                    return 1
                }
                ;;
            RZ_TRAIN_SLOTS)
                [[ "$val" =~ ^(0|[1-9][0-9]*)$ ]] || {
                    echo "error: $RZ_HOST_ENV_FILE:$n: $key must be a whole number >= 0: '$val'" >&2
                    return 1
                }
                ;;
            RZ_TEST_BUDGET_SCALE | RZ_CPU_FACTOR)
                rz_budget_scale_ok "$val" || {
                    echo "error: $RZ_HOST_ENV_FILE:$n: $key must be a number > 0 like 1.5: '$val'" >&2
                    return 1
                }
                ;;
            *)
                echo "error: $RZ_HOST_ENV_FILE:$n: unknown key $key" \
                    "(known: RZ_ROOMS_MEMORY_HIGH RZ_ROOMS_MEMORY_MAX RZ_GATE_SLOTS" \
                    "RZ_TRAIN_SLOTS RZ_TEST_BUDGET_SCALE RZ_CPU_FACTOR)" >&2
                return 1
                ;;
        esac
        HOST_ENV[$key]="$val"
    done < "$RZ_HOST_ENV_FILE"
}

# rz_budget_scale_ok <v>: is <v> a plain decimal > 0 (1, 1.5, 0.75)?  Exponents,
# signs and inf/nan are refused: Python's float() would take them.  Checks
# RZ_TEST_BUDGET_SCALE and RZ_CPU_FACTOR alike.
rz_budget_scale_ok() {
    [[ "$1" =~ ^[0-9]+(\.[0-9]+)?$ && "$1" =~ [1-9] ]]
}

# rz_size_bytes 28G -> 30064771072 (K/M/G are powers of 1024, as in systemd).
rz_size_bytes() {
    local v="$1" mult=1
    case "$v" in
        *K) mult=1024 ;;
        *M) mult=$((1024 ** 2)) ;;
        *G) mult=$((1024 ** 3)) ;;
    esac
    echo $(("${v%[KMG]}" * mult))
}

# rz_venv_path <path>: <path> with the gate's venv bin dirs in front, as on a
# host's own PATH: ~/dev/.venv (most hosts) first, then ~/dev/nevelis/.venv
# (omegalisk), each only if present.  For a PATH that has no venv on it: a
# hook's clean environment (provision-room.sh, AGAST #3722) or a remote login
# shell, whose /etc/profile resets PATH (train.sh's remote gate, AGAST #4025;
# train.sh sends this function's text to the host with `declare -f`, so keep
# it self-contained).
rz_venv_path() {
    local p="$1" v
    for v in "$HOME/dev/nevelis/.venv/bin" "$HOME/dev/.venv/bin"; do
        if [[ -d "$v" ]]; then p="$v:$p"; fi
    done
    echo "$p"
}

# rz_gate_slots: print "<slots> <train slots>" for this host: RZ_GATE_SLOTS and
# RZ_TRAIN_SLOTS from the environment, else host.env, else 1 and 0 (AGAST
# #4031).  Returns 2 with a message if host.env is malformed, a value is not a
# whole number, or the train slots would leave room gates none.  Reads
# host.env itself (RZ_HOST_ENV, as above), so train.sh can send it to another
# host with `declare -f` (with rz_host_env_load and rz_budget_scale_ok).
rz_gate_slots() {
    local RZ_HOST_ENV_FILE="${RZ_HOST_ENV:-${XDG_CONFIG_HOME:-$HOME/.config}/rz/host.env}"
    local -A HOST_ENV=()
    rz_host_env_load || return 2
    local s="${RZ_GATE_SLOTS:-${HOST_ENV[RZ_GATE_SLOTS]:-1}}" t="${RZ_TRAIN_SLOTS:-${HOST_ENV[RZ_TRAIN_SLOTS]:-0}}"
    if [[ ! "$s" =~ ^[1-9][0-9]*$ ]]; then
        echo "error: RZ_GATE_SLOTS must be a whole number >= 1: '$s'" >&2; return 2
    fi
    if [[ ! "$t" =~ ^(0|[1-9][0-9]*)$ ]]; then
        echo "error: RZ_TRAIN_SLOTS must be a whole number >= 0: '$t'" >&2; return 2
    fi
    if (( t >= s )); then
        echo "error: RZ_TRAIN_SLOTS ($t) must be below RZ_GATE_SLOTS ($s): room gates would get no slot" >&2
        return 2
    fi
    echo "$s $t"
}

# rz_train_free [<gate dir>]: how many more train gates this host can start
# now (AGAST #4031, train.sh pick_train_host): the gate slots no gate holds
# (a train gate may take any slot: its reserved ones and free general ones),
# minus the live train gates already queued for one (.gate-queue lines with
# train=1 and a live pid; run-gate.sh).  0 on a malformed host.env.  The
# gate dir defaults to run-gate.sh's.  Self-contained, as rz_gate_slots.
rz_train_free() {
    local dir="${1:-${RZ_GATE_DIR:-$HOME/dev/ritz-lang/gate-logs}}" st s i free=0 waiting=0 u p tr rest
    st="$(rz_gate_slots)" || { echo 0; return 0; }
    read -r s _ <<<"$st"
    for ((i = 0; i < s; i++)); do
        # A lock nobody holds is a free slot; ours is dropped as the subshell
        # exits.  No gate dir yet: nothing has ever run, every slot is free.
        if [[ ! -d "$dir" ]] || (exec 9>>"$dir/.gate-slot-$i" && flock -n 9) 2>/dev/null; then
            free=$((free + 1))
        fi
    done
    if [[ -f "$dir/.gate-queue" ]]; then
        while read -r u p tr rest; do
            [[ "$tr" == 1 ]] && kill -0 "$p" 2>/dev/null && waiting=$((waiting + 1))
        done < "$dir/.gate-queue"
    fi
    echo $((free > waiting ? free - waiting : 0))
}
