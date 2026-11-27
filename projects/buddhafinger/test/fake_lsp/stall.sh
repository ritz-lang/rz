# Answers initialize, floods stderr with 1 MiB, then reads nothing until
# the test creates $D/go; then reads every frame, and once one holds
# LAST-EDIT creates $D/done.
read_msg
send "$CAPS"
read_msg
head -c 1048576 /dev/zero | tr '\0' 'e' >&2
printf '\nflood done\n' >&2
wait_for go
while read_msg; do
  if grep -q LAST-EDIT "$D/msg.$n"; then touch "$D/done"; sleep 5; fi
done
