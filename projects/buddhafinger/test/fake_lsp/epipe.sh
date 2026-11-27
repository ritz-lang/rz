# Closes its stdin, then answers initialize and lingers: the client's next
# write (initialized) can only be EPIPE.
read_msg
exec 0<&-
send "$CAPS"
sleep 5
