"""Ask the installed libxkbcommon for fixture expectations; no keyboard engine."""

import ctypes as c


class Names(c.Structure):
    _fields_ = [(name, c.c_char_p) for name in ("rules", "model", "layout", "variant", "options")]


def expected(layout, keycode, modifiers=0):
    library = c.CDLL("libxkbcommon.so.0")
    for name, result, args in [
        ("xkb_context_new", c.c_void_p, [c.c_int]),
        ("xkb_keymap_new_from_names", c.c_void_p, [c.c_void_p, c.POINTER(Names), c.c_int]),
        ("xkb_state_new", c.c_void_p, [c.c_void_p]),
        ("xkb_state_update_key", c.c_int, [c.c_void_p, c.c_uint, c.c_int]),
        ("xkb_state_key_get_utf8", c.c_int, [c.c_void_p, c.c_uint, c.c_char_p, c.c_size_t]),
        ("xkb_state_mod_name_is_active", c.c_int, [c.c_void_p, c.c_char_p, c.c_uint]),
        ("xkb_keymap_mod_get_index", c.c_uint, [c.c_void_p, c.c_char_p]),
        ("xkb_state_key_get_consumed_mods2", c.c_uint, [c.c_void_p, c.c_uint, c.c_int]),
        ("xkb_context_unref", None, [c.c_void_p]),
        ("xkb_keymap_unref", None, [c.c_void_p]),
        ("xkb_state_unref", None, [c.c_void_p]),
    ]:
        function = getattr(library, name)
        function.restype, function.argtypes = result, args
    context = library.xkb_context_new(0)
    if not context:
        raise RuntimeError("The installed XKB context could not be created")
    keymap = state = None
    try:
        names = Names(None, None, layout.encode(), None, None)
        keymap = library.xkb_keymap_new_from_names(context, c.byref(names), 0)
        if not keymap:
            raise RuntimeError("The installed XKB layout could not be loaded")
        state = library.xkb_state_new(keymap)
        if not state:
            raise RuntimeError("The installed XKB state could not be created")
        for flag, modifier_keycode in [(2, 42), (64, 100)]:
            if modifiers & flag:
                library.xkb_state_update_key(state, modifier_keycode + 8, 1)
        # An unconsumed Alt modifier is a GTK shortcut, not printable text.
        # XKB reports whether Right Alt is ordinary Alt or the layout's AltGr.
        if library.xkb_state_mod_name_is_active(state, b"Mod1", 8) == 1:
            index = library.xkb_keymap_mod_get_index(keymap, b"Mod1")
            if index >= 32:
                raise RuntimeError("The installed XKB Alt modifier is unavailable")
            consumed = library.xkb_state_key_get_consumed_mods2(state, keycode + 8, 0)
            if not consumed & (1 << index):
                return ""
        buffer = c.create_string_buffer(64)
        length = library.xkb_state_key_get_utf8(state, keycode + 8, buffer, len(buffer))
        if not 0 < length < len(buffer):
            raise RuntimeError("Expected a printable fixture key")
        return buffer.value.decode("utf-8")
    finally:
        if state:
            library.xkb_state_unref(state)
        if keymap:
            library.xkb_keymap_unref(keymap)
        library.xkb_context_unref(context)
