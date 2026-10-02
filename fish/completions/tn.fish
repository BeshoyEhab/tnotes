# fish/completions/tn.fish
complete -c tn -f
complete -c tn -s g -d "global scope"
complete -c tn -s l -d "this dir only"
complete -c tn -l all -d "all dirs (picker)"
complete -c tn -l done -d "include completed"
complete -c tn -l hidden -d "include hidden"
complete -c tn -l url -d "add URL" -r
complete -c tn -l cmd -d "add command" -r
complete -c tn -l note -d "add note" -r
complete -c tn -l title -d "title" -r
complete -c tn -l tags -d "comma tags" -r
complete -c tn -l no-show -d "hide from autoshow"
complete -c tn -s m -d "compose in editor"
complete -c tn -n __fish_use_subcommand -a list -d "list entries"
complete -c tn -n __fish_use_subcommand -a search -d "search entries"
complete -c tn -n __fish_use_subcommand -a show -d "show entries"
complete -c tn -n __fish_use_subcommand -a open -d "open URL"
complete -c tn -n __fish_use_subcommand -a run -d "run command"
complete -c tn -n __fish_use_subcommand -a edit -d "edit entry"
complete -c tn -n __fish_use_subcommand -a rm -d "remove entry"
complete -c tn -n __fish_use_subcommand -a done -d "mark done"
complete -c tn -n __fish_use_subcommand -a undone -d "mark active"
complete -c tn -n __fish_use_subcommand -a hide -d "hide from autoshow"
complete -c tn -n __fish_use_subcommand -a unhide -d "show on open"
complete -c tn -n __fish_use_subcommand -a path -d "print store path"
complete -c tn -n __fish_use_subcommand -a tui -d "open TUI browser"
complete -c tn -l all -d "all dirs (picker)"
complete -c tn -l startup -d "startup autoshow (silent when empty)"
complete -c tn -l preview -d "preview rendering"
# Single ID-main row per entry; description shows number + title.
# done -> active only (tn list); undone -> done only; others -> all (tn list --done).
# Numbers match resolve_entry modes so `tn done 1` == startup #1.
function __tn_active
    tn list 2>/dev/null | awk '{
        id=$NF; NF-=2;
        sub(/^✔ /,""); sub(/^[^ ]+ /,"");
        printf "%s\t%s %s\n", id, NR, $0;
    }' 2>/dev/null
end
function __tn_done_only
    tn list --done 2>/dev/null | grep '^✔' 2>/dev/null | awk '{
        id=$NF; NF-=2;
        sub(/^✔ /,""); sub(/^[^ ]+ /,"");
        printf "%s\t%s %s\n", id, NR, $0;
    }' 2>/dev/null
end
function __tn_all
    tn list --done 2>/dev/null | awk '{
        id=$NF; NF-=2;
        sub(/^✔ /,""); sub(/^[^ ]+ /,"");
        printf "%s\t%s %s\n", id, NR, $0;
    }' 2>/dev/null
end
complete -c tn -n "__fish_seen_subcommand_from done" -a "(__tn_active)"
complete -c tn -n "__fish_seen_subcommand_from undone" -a "(__tn_done_only)"
for sub in show open run edit rm hide unhide
    complete -c tn -n "__fish_seen_subcommand_from $sub" -a "(__tn_all)"
end
