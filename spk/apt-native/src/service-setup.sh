service_postinst() {
  echo "[apt-native] installed. Run 'apt-native-bootstrap' as root to initialize experimental apt runtime." >&2
}

service_postupgrade() {
  echo "[apt-native] upgraded. Re-run 'apt-native-bootstrap' if runtime scripts changed." >&2
}
