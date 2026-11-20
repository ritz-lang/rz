#!/usr/bin/env bash
# run.sh: one guarded harland boot on a Nitro EC2 instance (AGAST #1849).
#
#   account          aws sts get-caller-identity must say 412381736149, or stop
#   build            make -C projects/indium ec2-disk (rootless)
#   snapshot         tools/ebs_snapshot.py: the image -> an EBS snapshot, no builder
#   init / apply     terraform in iac/boot-run (LOCAL state): AMI, SG, one
#                    t3.micro, and for #1851 one peer t3.micro in the same
#                    subnet that pings it
#   poll             aws ec2 get-console-output --latest until "rzsh> ", a
#                    KERNEL PANIC, or the timeout
#   save-log         projects/indium/boot-logs/<date>-<sha>.txt
#   terminate        aws ec2 terminate-instances (both instances), from the
#                    EXIT trap: billing stops at shutting-down, and a halted
#                    guest took 4m23s to finish terminating in the first live
#                    run
#   destroy          terraform destroy, from the EXIT trap: always
#   verify-state     terraform state list must be empty, else LEAK
#   delete-snapshot  every snapshot tagged with this run's RunId
#
# Cost guard (Aaron, 2026-11-08): t3.micro only (boot-run/variables.tf
# rejects anything else), auto-destroy, and at most 15 minutes of instance
# time per run: polling stops at most CEILING - TERMINATE_RESERVE seconds
# after apply began, and the clock stops when termination is requested. The
# #1851 ping peer is the same t3.micro; at most these two run, and --no-peer
# leaves it out.
# Never run from CI: the DEFAULT profile on Aaron's host is the only
# credential this is meant for.
#
# Exit codes: 0 reached rzsh; 1 a step failed; 2 usage; 3 wrong account;
# 4 no rzsh prompt (timeout or kernel panic); 5 resources left behind (LEAK);
# 130 interrupted.
#
# --dry-run touches no AWS: every aws/terraform call is printed as
# "DRY <command>" and answered from canned output. DRY_ACCOUNT, DRY_FAIL
# (snapshot|apply|poll), DRY_CONSOLE (prompt|none|panic) and DRY_STATE_LEFT steer
# it; projects/ritz/ritz0/test_indium_ec2_run.py drives them.

set -euo pipefail

EXPECTED_ACCOUNT=412381736149
REGION=us-west-2
INSTANCE_TYPE=t3.micro
PRICE_PER_HOUR=0.0104          # t3.micro on-demand, us-west-2, Linux
CEILING=900                    # instance seconds per run (15 minutes)
TERMINATE_RESERVE=60           # seconds kept back to request termination
MAX_POLL=720
PROMPT='rzsh> '

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
INDIUM=$(dirname "$HERE")
TF_DIR=$HERE/boot-run

DRY=0
BUILD=1
PEER_PING=1
POLL_TIMEOUT=360
IMAGE=$INDIUM/build/ec2-boot.img
LOG_DIR=$INDIUM/boot-logs
POLL_INTERVAL=${POLL_INTERVAL:-15}

usage() {
    cat <<EOF
Usage: run.sh [options]

Boot harland once on a $INSTANCE_TYPE in $REGION, save the serial console
log under boot-logs/, and destroy everything the run created.

Options:
  --dry-run            print every aws/terraform call instead of running it
  --no-build           use the existing image instead of make ec2-disk
  --no-peer            do not launch the #1851 ping peer (one instance only)
  --image PATH         the disk image (default: build/ec2-boot.img)
  --poll-timeout SECS  how long to wait for "$PROMPT" (1-$MAX_POLL, default 360)
  --log-dir DIR        where the log goes (default: projects/indium/boot-logs)
  -h, --help           this text
EOF
}

die_usage() { echo "run.sh: $*" >&2; usage >&2; exit 2; }

while [ $# -gt 0 ]; do
    case $1 in
        --dry-run) DRY=1 ;;
        --no-build) BUILD=0 ;;
        --no-peer) PEER_PING=0 ;;
        --image)
            [ $# -ge 2 ] || die_usage "--image needs a path"
            IMAGE=$2; shift ;;
        --poll-timeout)
            [ $# -ge 2 ] || die_usage "--poll-timeout needs seconds"
            [[ $2 =~ ^[0-9]+$ ]] && [ "$2" -ge 1 ] && [ "$2" -le $MAX_POLL ] \
                || die_usage "--poll-timeout must be 1-$MAX_POLL seconds, not '$2'"
            POLL_TIMEOUT=$2; shift ;;
        --log-dir)
            [ $# -ge 2 ] || die_usage "--log-dir needs a directory"
            LOG_DIR=$2; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die_usage "unknown argument '$1'" ;;
    esac
    shift
done

if [ $BUILD = 0 ] && [ ! -f "$IMAGE" ]; then
    echo "run.sh: no image at $IMAGE (drop --no-build to build it)" >&2
    exit 2
fi

# The Makefile's EC2_NET_RESPONDER takes 1/0; Terraform's bool takes true/false.
PEER_TF=false
[ $PEER_PING = 1 ] && PEER_TF=true

step() { echo "==> $1${2:+: $2}"; }

# --- aws / terraform, or their dry-run stand-ins ---------------------------------

aws_() {
    if [ $DRY = 1 ]; then
        echo "DRY aws $*" >&2
        case "$*" in
            "sts get-caller-identity"*) echo "${DRY_ACCOUNT:-$EXPECTED_ACCOUNT}" ;;
            "ec2 get-console-output"*)
                [ "${DRY_FAIL:-}" = poll ] && return 1
                printf 'Harland kernel starting...\n[init] Starting rzsh...\n'
                case ${DRY_CONSOLE:-prompt} in
                    prompt) printf '%s' "$PROMPT" ;;
                    panic) printf '*** KERNEL PANIC: dry ***\nSystem halted.\n' ;;
                esac
                ;;
            "ec2 describe-snapshots"*) echo "snap-dry" ;;
        esac
        return 0
    fi
    aws --region "$REGION" "$@"
}

tf() {
    if [ $DRY = 1 ]; then
        echo "DRY terraform $*" >&2
        case "$1" in
            apply) [ "${DRY_FAIL:-}" = apply ] && return 1 ;;
            output)
                # `terraform output -raw NAME`: the name is $3.
                case "${3:-}" in
                    peer_instance_id) echo "i-peer-dry" ;;
                    peer_ip) echo "172.31.32.10" ;;
                    *) echo "i-dry" ;;
                esac
                ;;
            state) [ -n "${DRY_STATE_LEFT:-}" ] && echo "aws_instance.harland" ;;
        esac
        return 0
    fi
    # Ten minutes per call: a hung apply or destroy must not outlive the
    # instance-time ceiling unnoticed.
    timeout 600 terraform -chdir="$TF_DIR" "$@"
}

snapshot_upload() {
    if [ $DRY = 1 ]; then
        echo "DRY ebs_snapshot.py upload $IMAGE"
        python3 "$INDIUM/tools/ebs_snapshot.py" plan "$IMAGE"
        [ "${DRY_FAIL:-}" = snapshot ] && return 1
        SNAPSHOT_ID=snap-dry
        return 0
    fi
    SNAPSHOT_ID=$(python3 "$INDIUM/tools/ebs_snapshot.py" upload "$IMAGE" --region "$REGION" \
        --tag "Project=harland-boot-run" --tag "RunId=$RUN_ID" --tag "Task=AGAST-1849")
}

# --- state for the trap ---------------------------------------------------------------

RUN_ID=$(date -u +%Y%m%d-%H%M%S)-$$
SHA=$(git -C "$INDIUM" rev-parse --short=12 HEAD 2>/dev/null || echo nogit)
SNAPSHOT_ID=
TF_TOUCHED=0           # past the account check: destroy + verify are owed
APPLY_START=0
TERMINATED_AT=0        # when termination was requested: the billing clock stops
INSTANCE_ID=
PEER_INSTANCE_ID=      # #1851: the one ping peer, empty with --no-peer
PEER_IP=
CONSOLE=
RESULT="did not boot"
RC=0
TF_VARS=()

# Seconds since apply began, up to the termination request: an upper bound
# on what EC2 bills (the instance launched a few seconds after apply began).
instance_seconds() {
    local end=$TERMINATED_AT
    [ "$end" = 0 ] && end=$(date +%s)
    if [ "$APPLY_START" = 0 ]; then echo 0; else echo $(( end - APPLY_START )); fi
}

save_log() {
    step save-log
    mkdir -p "$LOG_DIR"
    LOG_FILE=$LOG_DIR/$(date -u +%Y-%m-%d)-$SHA.txt
    {
        echo "# harland boot on EC2 Nitro (AGAST #1849)"
        echo "# commit: $(git -C "$INDIUM" rev-parse HEAD 2>/dev/null || echo nogit) (ritz0 build)"
        if [ -f "$IMAGE" ]; then
            echo "# image: sha256:$(sha256sum "$IMAGE" | cut -d' ' -f1) $IMAGE"
        fi
        echo "# instance: ${INSTANCE_ID:-none} $INSTANCE_TYPE $REGION, run $RUN_ID"
        if [ -n "$PEER_INSTANCE_ID" ]; then
            echo "# peer: $PEER_INSTANCE_ID $PEER_IP"
        else
            echo "# peer: none"
        fi
        echo "# captured: $(date -u +%Y-%m-%dT%H:%M:%SZ) via aws ec2 get-console-output --latest"
        echo "#   (the last 64 KiB of serial output at that moment, not the whole boot)"
        echo "# result: $RESULT"
        echo
        printf '%s\n' "$CONSOLE"
    } > "$LOG_FILE"
    # The peer's console is diagnostic, not the acceptance artefact: it tells
    # "the user-data never ran" from "it ran and got no reply". Only a boot
    # that reached rzsh has it (the panic path must not make a second call).
    if [ "${1:-}" = peer ] && [ -n "$PEER_INSTANCE_ID" ]; then
        local pcon
        pcon=$(aws_ ec2 get-console-output --instance-id "$PEER_INSTANCE_ID" --latest \
            --output text --query Output) || pcon="(unavailable)"
        {
            echo
            echo "# --- peer console (${PEER_INSTANCE_ID}, ${PEER_IP}) ---"
            echo "# captured: $(date -u +%Y-%m-%dT%H:%M:%SZ) via aws ec2 get-console-output --latest"
            printf '%s\n' "$pcon"
        } >> "$LOG_FILE"
    fi
    echo "log: $LOG_FILE"
}

cleanup() {
    RC=$?
    trap - EXIT INT TERM
    set +e
    if [ $TF_TOUCHED = 1 ]; then
        [ -n "$CONSOLE" ] && [ -z "${LOG_FILE:-}" ] && save_log
        if [ -n "$INSTANCE_ID" ]; then
            step terminate
            local -a ids=("$INSTANCE_ID")
            [ -n "$PEER_INSTANCE_ID" ] && [ "$PEER_INSTANCE_ID" != "$INSTANCE_ID" ] \
                && ids+=("$PEER_INSTANCE_ID")
            aws_ ec2 terminate-instances --instance-ids "${ids[@]}" \
                --query 'TerminatingInstances[].CurrentState.Name' --output text \
                || echo "run.sh: terminate-instances failed; terraform destroy will retry" >&2
            TERMINATED_AT=$(date +%s)
        fi
        step destroy
        local ok=0
        for _ in 1 2 3; do
            if tf destroy -auto-approve -input=false "${TF_VARS[@]}"; then ok=1; break; fi
            sleep 10
        done
        [ $ok = 1 ] || echo "run.sh: terraform destroy failed three times" >&2
        step verify-state
        # stdout only; a failing `state list` cannot prove the state empty.
        local left
        left=$(tf state list) || left="(terraform state list failed: state unverified)"
        if [ -n "$left" ]; then
            echo "run.sh: LEAK: terraform state still lists:" >&2
            echo "$left" >&2
            RC=5
        else
            echo "state empty"
        fi
    fi
    if [ -n "$SNAPSHOT_ID" ] || [ $TF_TOUCHED = 1 ]; then
        step delete-snapshot
        # By tag as well as by id: an upload that died after start-snapshot
        # never printed its id.
        local snaps
        snaps=$(aws_ ec2 describe-snapshots --owner-ids self \
            --filters "Name=tag:RunId,Values=$RUN_ID" \
            --query 'Snapshots[].SnapshotId' --output text)
        # tr maps each character in SET1 to the one at the same position in
        # SET2 (a short SET2 repeats its last character), so one '\n' turns
        # both the space and the tab into newlines.
        for s in $(echo "$SNAPSHOT_ID $snaps" | tr ' \t' '\n' | sort -u); do
            [ "$s" = None ] && continue
            if aws_ ec2 delete-snapshot --snapshot-id "$s"; then
                echo "deleted $s"
            else
                echo "run.sh: LEAK: snapshot $s not deleted" >&2
                RC=5
            fi
        done
    fi
    step summary
    local secs; secs=$(instance_seconds)
    local instances=1
    [ $PEER_PING = 1 ] && instances=2
    echo "result: $RESULT"
    echo "billed seconds: $secs x $instances instances (ceiling $CEILING; apply to termination request)"
    # EC2 bills Linux per second with a 60 s minimum, per instance.
    awk -v s="$secs" -v p="$PRICE_PER_HOUR" -v t="$INSTANCE_TYPE" -v n="$instances" \
        'BEGIN { b = (s > 0 && s < 60) ? 60 : s; printf "cost: $%.4f (%s x %s at $%s/h)\n", b * p * n / 3600, t, n, p }'
    exit $RC
}
trap cleanup EXIT
trap 'RESULT="interrupted, last result: $RESULT"; exit 130' INT TERM

# --- the run --------------------------------------------------------------------------------

step account
ACCOUNT=$(aws_ sts get-caller-identity --query Account --output text)
if [ "$ACCOUNT" != "$EXPECTED_ACCOUNT" ]; then
    echo "run.sh: AWS account is '$ACCOUNT', not $EXPECTED_ACCOUNT: stopping before anything is created" >&2
    RESULT="wrong account"
    exit 3
fi
echo "account $ACCOUNT"

step build
if [ $BUILD = 1 ]; then
    if [ $DRY = 1 ]; then
        echo "DRY make -C $INDIUM ec2-disk EC2_NET_RESPONDER=$PEER_PING"
    else
        make -C "$INDIUM" ec2-disk EC2_NET_RESPONDER=$PEER_PING
    fi
else
    echo "skipped (--no-build): $IMAGE"
fi

# From here on the trap owes a destroy and an empty-state check. init comes
# first so that destroy can run whichever later step fails.
TF_TOUCHED=1
TF_VARS=(-var "run_id=$RUN_ID" -var "snapshot_id=none" -var "instance_type=$INSTANCE_TYPE" -var "peer_ping=$PEER_TF")
step init
tf init -input=false

step snapshot
snapshot_upload
echo "snapshot $SNAPSHOT_ID"
TF_VARS=(-var "run_id=$RUN_ID" -var "snapshot_id=$SNAPSHOT_ID" -var "instance_type=$INSTANCE_TYPE" -var "peer_ping=$PEER_TF")

step apply
APPLY_START=$(date +%s)
tf apply -auto-approve -input=false "${TF_VARS[@]}"
INSTANCE_ID=$(tf output -raw instance_id)
echo "instance $INSTANCE_ID"
if [ $PEER_PING = 1 ]; then
    PEER_INSTANCE_ID=$(tf output -raw peer_instance_id)
    PEER_IP=$(tf output -raw peer_ip)
    echo "peer $PEER_INSTANCE_ID ($PEER_IP)"
fi

step poll "up to ${POLL_TIMEOUT}s for '$PROMPT'"
deadline=$(( $(date +%s) + POLL_TIMEOUT ))
hard=$(( APPLY_START + CEILING - TERMINATE_RESERVE ))
[ $deadline -gt $hard ] && deadline=$hard
while :; do
    out=$(aws_ ec2 get-console-output --instance-id "$INSTANCE_ID" --latest --output text \
        --query Output)
    [ -n "$out" ] && [ "$out" != None ] && CONSOLE=$out
    if [[ $CONSOLE == *"$PROMPT"* ]]; then
        RESULT="reached rzsh"
        echo "reached rzsh after $(instance_seconds)s"
        break
    fi
    if [[ $CONSOLE == *"KERNEL PANIC"* ]]; then
        RESULT="kernel panic"
        echo "kernel panic after $(instance_seconds)s"
        save_log
        exit 4
    fi
    if [ "$(date +%s)" -ge $deadline ]; then
        RESULT="no rzsh prompt within ${POLL_TIMEOUT}s"
        echo "no rzsh prompt after $(instance_seconds)s"
        save_log
        exit 4
    fi
    sleep "$POLL_INTERVAL"
done
save_log peer
