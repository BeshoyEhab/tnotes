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
