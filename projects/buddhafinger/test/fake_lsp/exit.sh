# Exits with status 3 after initialize, with its reason on stderr.
read_msg
echo 'starting' >&2
echo 'fatal: no ritz1 here' >&2
exit 3
