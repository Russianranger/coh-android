#!/bin/bash
# step.sh <title> <command...>: run a CI step command; on failure, put the
# last 3,500 characters of its output into an ::error annotation, because the
# step logs are not readable from the review environment (check-run
# annotations are). The command's exit status is preserved.
title=$1; shift
log=$(mktemp)
"$@" > >(tee "$log") 2>&1
status=$?
wait
if [ $status -ne 0 ]; then
  tail -c 3500 "$log" | sed 's/%/%25/g; s/\r//g' | awk 'BEGIN{ORS="%0A"} {print}' > "$log.esc"
  echo "::error title=$title (exit $status)::$(cat "$log.esc")"
fi
rm -f "$log" "$log.esc"
exit $status
