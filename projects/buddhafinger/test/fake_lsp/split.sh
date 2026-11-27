# initialize answered in three pieces, cut in the header and in the body;
# diagnostics for didOpen's version; hover answered 0.3 s late.
printf '%s' "$RITZ1" > "$D/ritz1"
read_msg
printf 'Content-Len'; sleep 0.05
printf 'gth: %d\r\n\r\n{"jsonrpc":' "${#CAPS}"; sleep 0.05
printf '%s' "${CAPS#\{\"jsonrpc\":}"
read_msg
read_msg
send '{"jsonrpc":"2.0","method":"textDocument/publishDiagnostics","params":{"uri":"file:///src/a.ritz","version":'"$(version)"',"diagnostics":[{"range":{"start":{"line":0,"character":0},"end":{"line":0,"character":2}},"severity":1,"message":"bad"}]}}'
read_msg
sleep 0.3
send '{"jsonrpc":"2.0","id":2,"result":{"contents":"late but here"}}'
read_msg
