#!/home/aaron/dev/nevelis/.venv/bin/python3
"""Archive Adele rooms for finished ritz-task-* tickets (Aaron, 2026-11-14).

    archive-rooms.py ritz-task-2377 ritz-task-2260   # archive these rooms
    archive-rooms.py --from-git 400 [--apply]         # rooms named in main's last 400 subjects
    archive-rooms.py --sweep [--apply]                # unarchived ritz-task-* rooms on the server

Named rooms are archived as given: rz runs this after `train.sh land` for
every MERGED room (local or remote), and after closing a ticket with a REAP
`none`.

--from-git and --sweep are for catching up. Each finds candidate rooms,
skips any whose AGAST ticket isn't `completed` (still working, or needs a
look: reported as KEEP), skips rooms already archived or missing on the
server, and archives the rest with --apply (dry run without).
- --from-git N: every `ritz-task-<id>:` prefix in origin/main's last N commit
  subjects (every merged room's commit is titled that way).
- --sweep: GET /api/rooms/ (the 100 most recently updated unarchived rooms;
  with --apply it re-lists until no new room appears). Also catches rooms
  closed without a merge (REAP `none`), which git history can't name.

Archiving is DELETE /api/rooms/<room>/: is_archived=True, is_active=False.
History is kept and `unarchive_room` reverses it. Units, worktrees and
branches are untouched (that is TEARDOWN / `adele room rm`).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.expanduser('~/dev/nevelis/adele'))

from cli.main import _merged_env  # noqa: E402
from cli.room_api import AgastClient, ApiError, RoomServer  # noqa: E402

ROOM_RE = re.compile(r'^ritz-task-(\d+)$')
REPO = os.path.expanduser('~/dev/ritz-lang/rz')


def archive(server: RoomServer, room: str) -> str:
    try:
        server._call('DELETE', f'/api/rooms/{urllib.parse.quote(room)}/')
    except ApiError as e:
        return f'FAILED   {room} ({e.status}: {e})'
    return f'ARCHIVED {room}'


def ticket_status(agast: AgastClient, task_id: int) -> str:
    # AGAST answers the odd lookup with a transient 500; retry before giving up.
    for attempt in range(3):
        try:
            return agast.get_task(task_id).get('status') or 'unknown'
        except ApiError as e:
            if attempt == 2:
                return f'lookup failed ({e.status})'
            time.sleep(1 + attempt)
    return 'unknown'


def consider(server, agast, room, apply, *, check_archived) -> str:
    """One candidate room: KEEP / ALREADY / MISSING / WOULD / ARCHIVED / FAILED."""
    if check_archived:
        try:
            archived = server.is_archived(room)
        except ApiError as e:
            return f'SKIP     {room} (room lookup failed: {e.status})'
        if archived is None:
            return f'MISSING  {room}'
        if archived:
            return f'ALREADY  {room}'
    status = ticket_status(agast, int(ROOM_RE.match(room).group(1)))
    if status != 'completed':
        return f'KEEP     {room} (ticket {status})'
    return archive(server, room) if apply else f'WOULD    {room}'


def git_rooms(n: int) -> list[str]:
    subjects = subprocess.run(
        ['git', '-C', REPO, 'log', f'-{n}', '--format=%s', 'origin/main'],
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    rooms: list[str] = []
    for s in subjects:
        m = re.match(r'(ritz-task-\d+):', s)
        if m and m.group(1) not in rooms:
            rooms.append(m.group(1))
    return rooms


def summarise(lines: list[str]) -> None:
    counts: dict[str, int] = {}
    for line in lines:
        key = line.split()[0]
        counts[key] = counts.get(key, 0) + 1
    print('TOTAL ' + ' '.join(f'{k.lower()}={v}' for k, v in sorted(counts.items())))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('rooms', nargs='*', help='ritz-task-<id> rooms to archive')
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument('--from-git', type=int, metavar='N', help="rooms in main's last N subjects")
    mode.add_argument('--sweep', action='store_true', help='unarchived ritz-task-* rooms on the server')
    ap.add_argument('--apply', action='store_true', help='with --from-git/--sweep: archive (default: dry run)')
    args = ap.parse_args()
    catch_up = args.from_git is not None or args.sweep
    if bool(args.rooms) == catch_up:
        ap.error('give room names, --from-git N or --sweep (exactly one)')

    env = _merged_env()
    server = RoomServer.from_cached_token(env.get('ADELE_SERVER_URL') or os.environ['ADELE_SERVER_URL'])

    if args.rooms:
        bad = [r for r in args.rooms if not ROOM_RE.match(r)]
        if bad:
            ap.error(f'not a ritz-task-<id> room: {", ".join(bad)}')
        lines = [archive(server, r) for r in args.rooms]
        print('\n'.join(lines))
        return 0 if all(line.startswith('ARCHIVED') for line in lines) else 1

    agast = AgastClient.from_env(env)
    lines: list[str] = []
    if args.from_git is not None:
        for room in git_rooms(args.from_git):
            lines.append(consider(server, agast, room, args.apply, check_archived=True))
            print(lines[-1], flush=True)
    else:
        seen: set[str] = set()
        while True:
            listed = [r['room_id'] for r in server._call('GET', '/api/rooms/').get('rooms', [])]
            fresh = [r for r in listed if r not in seen]
            if not fresh:
                break
            for room in fresh:
                seen.add(room)
                if ROOM_RE.match(room):
                    lines.append(consider(server, agast, room, args.apply, check_archived=False))
                    print(lines[-1], flush=True)
            if not args.apply:
                if len(listed) >= 100:
                    print('NOTE     a dry run sees only the 100 most recently updated rooms')
                break
    summarise(lines)
    return 0 if not any(line.startswith('FAILED') for line in lines) else 1


if __name__ == '__main__':
    sys.exit(main())
