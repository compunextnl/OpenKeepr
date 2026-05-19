#!/usr/bin/env bash
# OpenKeepr service helper — installed at /usr/local/bin/openkeepr.
# Lets the openkeepr user start/stop/restart/inspect the service without
# remembering the systemctl invocation.
set -euo pipefail

cmd="${1:-status}"
shift || true

case "$cmd" in
    start|stop|restart|reload|status|is-active|is-enabled)
        exec sudo /bin/systemctl "$cmd" openkeepr "$@"
        ;;
    logs|log|tail)
        exec sudo /usr/bin/journalctl -u openkeepr -f "$@"
        ;;
    journal|history)
        exec sudo /usr/bin/journalctl -u openkeepr -n 200 --no-pager "$@"
        ;;
    -h|--help|help)
        cat <<EOF
Usage: openkeepr <command>

  start       Start the OpenKeepr service
  stop        Stop the service
  restart     Restart the service
  reload      Send SIGHUP (graceful worker reload)
  status      Show systemd unit status
  is-active   Print "active" if running
  logs        Tail the journal (Ctrl-C to exit)
  journal     Show the last 200 log lines
EOF
        ;;
    *)
        echo "Unknown command: $cmd" >&2
        echo "Try: openkeepr help" >&2
        exit 2
        ;;
esac
