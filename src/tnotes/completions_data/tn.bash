# bash completion for tn — source from ~/.bashrc:
#   source ~/tnotes/completions/tn.bash
_tn_active_ids() {
    tn list 2>/dev/null | awk '{print $NF}' 2>/dev/null
}
_tn_done_ids() {
    tn list --done 2>/dev/null | grep '^✔' 2>/dev/null | awk '{print $NF}' 2>/dev/null
}
_tn_all_ids() {
    tn list --done 2>/dev/null | awk '{print $NF}' 2>/dev/null
}
_tn() {
    local cur prev subs opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    subs="list search show open run edit rm done undone hide unhide path tui"
    opts="--url --cmd --note --title --tags --no-show -m -g -l --all --done --hidden --startup --preview"

    case "$prev" in
        --url|--cmd|--note|--title|--tags) return 0 ;;
        done)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "--all -g -l --done --hidden --startup --preview" -- "$cur"))
            else
                COMPREPLY=($(compgen -W "$(_tn_active_ids)" -- "$cur"))
            fi
            return 0 ;;
        undone)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "--all -g -l --done --hidden --startup --preview" -- "$cur"))
            else
                COMPREPLY=($(compgen -W "$(_tn_done_ids)" -- "$cur"))
            fi
            return 0 ;;
        open|run|edit|rm|hide|unhide|show)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "--all -g -l --done --hidden --startup --preview" -- "$cur"))
            else
                COMPREPLY=($(compgen -W "$(_tn_all_ids)" -- "$cur"))
            fi
            return 0 ;;
    esac

    if [[ "$cur" == -* ]]; then
        COMPREPLY=($(compgen -W "$opts" -- "$cur"))
    else
        COMPREPLY=($(compgen -W "$subs" -- "$cur"))
    fi
    return 0
}
complete -F _tn tn
