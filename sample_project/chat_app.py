"""Chat room (existing code)."""

VERSION = "1.0.0"

ROOMS = {}


def join_room(room, display_name):
    ROOMS.setdefault(room, {"members": [], "messages": []})
    ROOMS[room]["members"].append(display_name)
