# Answers initialize, floods stderr with 1 MiB, then never reads again
# (test_lsp_editor.ritz: the editor must go on regardless).
read_msg
send "$CAPS"
read_msg
head -c 1048576 /dev/zero | tr '\0' 'e' >&2
wait_for never
