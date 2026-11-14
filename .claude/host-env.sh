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
            *)
                echo "error: $RZ_HOST_ENV_FILE:$n: unknown key $key" \
                    "(known: RZ_ROOMS_MEMORY_HIGH RZ_ROOMS_MEMORY_MAX RZ_GATE_SLOTS)" >&2
                return 1
                ;;
        esac
        HOST_ENV[$key]="$val"
    done < "$RZ_HOST_ENV_FILE"
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
