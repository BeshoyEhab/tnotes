# fish/conf.d/tnotes-autoshow.fish — per-dir autoshow, once per shell per dir.
function __tnotes_autoshow --on-variable PWD
    set -q __tnotes_last_dir; or set -g __tnotes_last_dir ""
    if test "$PWD" = "$__tnotes_last_dir"
        return
    end
    set -g __tnotes_last_dir "$PWD"
    if set -q NOTE_AUTOSHOW_GLOBAL; and test "$NOTE_AUTOSHOW_GLOBAL" = "1"
        tn show --startup 2>/dev/null
    else
        tn show --startup -l 2>/dev/null
    end
end
