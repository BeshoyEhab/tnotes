# bash completion for tn — installed by `tn completions install` to
# ~/.local/share/bash-completion/completions/tn
_tn_active_ids() {
    tn list 2>/dev/null | awk '{print $NF}' 2>/dev/null
}
_tn_done_ids() {
    tn list --done 2>/dev/null | sed -E 's/^[0-9]+\. //' 2>/dev/null | grep '^✔' 2>/dev/null | awk '{print $NF}' 2>/dev/null
}
_tn() {
    local cur prev subs opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    subs="list search show open run edit rm done undone hide unhide path tui completions"
    opts="--url --cmd --note --title --tags --no-show -m -g -l --all --done --hidden --startup --preview"

    case "$prev" in
        --url|--cmd|--note|--title|--tags) return 0 ;;
        done|show|open|run|edit|rm|hide|unhide)
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
        completions)
            COMPREPLY=($(compgen -W "install uninstall" -- "$cur"))
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
