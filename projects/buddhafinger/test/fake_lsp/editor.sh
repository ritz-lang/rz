# A server for the editor on a pty (test_lsp_editor.ritz). Every didOpen
# and didChange gets diagnostics for its version, unasked: one error on
# line 0, bytes 0..6, while the text holds BROKEN, else none. Hover answers
# "HOVER: helper returns i32"; definition answers line 0, character 3 of
# the same file.
read_msg
send "$CAPS"
read_msg
uri=
while read_msg; do
  m="$D/msg.$n"
  id=$(sed -n 's/^{"jsonrpc":"2.0","method":"[^"]*","id":\([0-9]*\).*/\1/p' "$m")
  case $(cat "$m") in
    *'"method":"textDocument/didOpen"'*|*'"method":"textDocument/didChange"'*)
      uri=$(sed -n 's/.*"uri":"\([^"]*\)".*/\1/p' "$m" | head -n 1)
      v=$(version)
      if grep -q BROKEN "$m"; then
        send '{"jsonrpc":"2.0","method":"textDocument/publishDiagnostics","params":{"uri":"'"$uri"'","version":'"$v"',"diagnostics":[{"range":{"start":{"line":0,"character":0},"end":{"line":0,"character":6}},"severity":1,"message":"undefined: BROKEN"}]}}'
      else
        send '{"jsonrpc":"2.0","method":"textDocument/publishDiagnostics","params":{"uri":"'"$uri"'","version":'"$v"',"diagnostics":[]}}'
      fi ;;
    *'"method":"textDocument/hover"'*)
      send '{"jsonrpc":"2.0","id":'"$id"',"result":{"contents":{"kind":"markdown","value":"```ritz\nHOVER: helper returns i32\n```"}}}' ;;
    *'"method":"textDocument/definition"'*)
      send '{"jsonrpc":"2.0","id":'"$id"',"result":{"uri":"'"$uri"'","range":{"start":{"line":0,"character":3},"end":{"line":0,"character":9}}}}' ;;
  esac
done
