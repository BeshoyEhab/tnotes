# fish/conf.d/tnotes-autoshow.fish — per-dir autoshow, once per dir per shell.
function __tnotes_maybe_show
    set -q __tnotes_seen_dirs; or set -g __tnotes_seen_dirs
    if contains -- "$PWD" $__tnotes_seen_dirs
        return
    end
    set -ga __tnotes_seen_dirs "$PWD"
    if set -q NOTE_AUTOSHOW_GLOBAL; and test "$NOTE_AUTOSHOW_GLOBAL" = "1"
        tn show --startup 2>/dev/null
    else
        tn show --startup -l 2>/dev/null
    end
end

function __tnotes_autoshow --on-variable PWD
    __tnotes_maybe_show
end

# Cover shell startup too (replaces manual `tn show --startup` in config.fish).
__tnotes_maybe_show
