# Snapshot file
# Unset all aliases to avoid conflicts with functions
unalias -a 2>/dev/null || true
shopt -u array_expand_once
shopt -u assoc_expand_once
shopt -u autocd
shopt -u bash_source_fullpath
shopt -u cdable_vars
shopt -u cdspell
shopt -u checkhash
shopt -u checkjobs
shopt -s checkwinsize
shopt -s cmdhist
shopt -u compat31
shopt -u compat32
shopt -u compat40
shopt -u compat41
shopt -u compat42
shopt -u compat43
shopt -u compat44
shopt -s complete_fullquote
shopt -u direxpand
shopt -u dirspell
shopt -u dotglob
shopt -u execfail
shopt -u expand_aliases
shopt -u extdebug
shopt -u extglob
shopt -s extquote
shopt -u failglob
shopt -s force_fignore
shopt -s globasciiranges
shopt -s globskipdots
shopt -u globstar
shopt -u gnu_errfmt
shopt -u histappend
shopt -u histreedit
shopt -u histverify
shopt -s hostcomplete
shopt -u huponexit
shopt -u inherit_errexit
shopt -s interactive_comments
shopt -u lastpipe
shopt -u lithist
shopt -u localvar_inherit
shopt -u localvar_unset
shopt -s login_shell
shopt -u mailwarn
shopt -u no_empty_cmd_completion
shopt -u nocaseglob
shopt -u nocasematch
shopt -u noexpand_translation
shopt -u nullglob
shopt -s patsub_replacement
shopt -s progcomp
shopt -u progcomp_alias
shopt -s promptvars
shopt -u restricted_shell
shopt -u shift_verbose
shopt -s sourcepath
shopt -u varredir_close
shopt -u xpg_echo
# Functions
gawklibpath_append () 
{ 
    [ -z "$AWKLIBPATH" ] && AWKLIBPATH=`gawk 'BEGIN {print ENVIRON["AWKLIBPATH"]}'`;
    export AWKLIBPATH="$AWKLIBPATH:$*"
}
gawklibpath_default () 
{ 
    unset AWKLIBPATH;
    export AWKLIBPATH=`gawk 'BEGIN {print ENVIRON["AWKLIBPATH"]}'`
}
gawklibpath_prepend () 
{ 
    [ -z "$AWKLIBPATH" ] && AWKLIBPATH=`gawk 'BEGIN {print ENVIRON["AWKLIBPATH"]}'`;
    export AWKLIBPATH="$*:$AWKLIBPATH"
}
gawkpath_append () 
{ 
    [ -z "$AWKPATH" ] && AWKPATH=`gawk 'BEGIN {print ENVIRON["AWKPATH"]}'`;
    export AWKPATH="$AWKPATH:$*"
}
gawkpath_default () 
{ 
    unset AWKPATH;
    export AWKPATH=`gawk 'BEGIN {print ENVIRON["AWKPATH"]}'`
}
gawkpath_prepend () 
{ 
    [ -z "$AWKPATH" ] && AWKPATH=`gawk 'BEGIN {print ENVIRON["AWKPATH"]}'`;
    export AWKPATH="$*:$AWKPATH"
}

# setopts 3
set -o braceexpand
set -o hashall
set -o interactive-comments

# aliases 0

# exports (native declarations)
declare -x AI_AGENT="claude-code_2-1-301_agent"
declare -x ANTHROPIC_API_KEY=""
declare -x ANTHROPIC_AUTH_TOKEN="tgp_v1_TFh_ipD91wcwf6vXGhcUmgUeXcfS6N96SC7oekg8avg"
declare -x ANTHROPIC_BASE_URL="https://gateway.togetherlink.dev"
declare -x ANTHROPIC_CUSTOM_MODEL_OPTION="auto[1m]"
declare -x ANTHROPIC_DEFAULT_FABLE_MODEL="zai-org/GLM-5.3[1m]"
declare -x ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-ai/DeepSeek-V4.1-Flash[1m]"
declare -x ANTHROPIC_DEFAULT_OPUS_MODEL="moonshotai/Kimi-K3[1m]"
declare -x ANTHROPIC_DEFAULT_SONNET_MODEL="zai-org/GLM-5.3-Flash[1m]"
declare -x ANTHROPIC_MODEL="auto[1m]"
declare -x BUN_INSTALL="/home/riccardogiorato/.bun"
declare -x CLAUDECODE="1"
declare -x CLAUDE_AGENT_SDK_VERSION="0.3.276"
declare -x CLAUDE_CODE_CHILD_SESSION="1"
declare -x CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY="0"
declare -x CLAUDE_CODE_ENTRYPOINT="sdk-ts"
declare -x CLAUDE_CODE_EXECPATH="/home/riccardogiorato/.local/share/mise/installs/claude/2.1.301/claude"
declare -x CLAUDE_CODE_MAX_CONTEXT_TOKENS="1000000"
declare -x CLAUDE_CODE_MAX_OUTPUT_TOKENS="131072"
declare -x CLAUDE_CODE_MESSAGING_SOCKET="/run/user/1000/cc-socks/1371000.sock"
declare -x CLAUDE_CODE_MESSAGING_TOKEN="6489acb7624dd399298d2b4afa324a04"
declare -x CLAUDE_CODE_SESSION_ATTENDED="0"
declare -x CLAUDE_CODE_SESSION_ID="256256f0-58a2-4b26-94f8-9e6d8a88514d"
declare -x CLAUDE_EFFORT="high"
declare -x CLAUDE_PID="1371000"
declare -x CODEX_HOME="/home/riccardogiorato/Desktop/github/local-ai-rtx2080/experiments/strata-codex-agbench-20261022/codex-home"
declare -x COREPACK_ENABLE_AUTO_PIN="0"
declare -x CPU_PRESSURE_WATCH="/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/app.slice/t3code.service/cpu.pressure"
declare -x CPU_PRESSURE_WRITE="c29tZSAyMDAwMDAgMjAwMDAwMAA="
declare -x CUDA_PATH="/opt/cuda"
declare -x DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus"
declare -x DEBUGINFOD_URLS="https://debuginfod.archlinux.org "
declare -x ENABLE_TOOL_SEARCH="true"
declare -x GIT_EDITOR="true"
declare -x HOME="/home/riccardogiorato"
declare -x INPUT_METHOD="fcitx"
declare -x INVOCATION_ID="cb19ab4a3dd8433483877efde1d63868"
declare -x IO_PRESSURE_WATCH="/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/app.slice/t3code.service/io.pressure"
declare -x IO_PRESSURE_WRITE="c29tZSAyMDAwMDAgMjAwMDAwMAA="
declare -x LANG="en_US.UTF-8"
declare -x LOGNAME="riccardogiorato"
declare -x MANAGERPID="898"
declare -x MANAGERPIDFDID="4253"
declare -x MEMORY_PRESSURE_WATCH="/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/app.slice/t3code.service/memory.pressure"
declare -x MEMORY_PRESSURE_WRITE="c29tZSAyMDAwMDAgMjAwMDAwMAA="
declare -x MISE_MINIMUM_RELEASE_AGE="0"
declare -x NVCC_CCBIN="/usr/bin/g++"
declare -x NoDefaultCurrentDirectoryInExePath="1"
declare -x OMARCHY_PATH="/usr/share/omarchy"
declare -x PATH="/home/riccardogiorato/.local/bin:/home/riccardogiorato/.togetherlink/bin:/home/riccardogiorato/.bun/bin:/home/riccardogiorato/Desktop/github/local-ai-rtx2080/experiments/strata-codex-agbench-20261022/codex-home/tmp/arg0-linux/codex-arg0VoPsYw:/home/riccardogiorato/.local/share/mise/installs/codex/0.163.0/codex-path:/home/riccardogiorato/.local/bin:/home/riccardogiorato/.togetherlink/bin:/home/riccardogiorato/.bun/bin:/home/riccardogiorato/.local/share/mise/installs/claude/latest:/home/riccardogiorato/.local/share/mise/installs/codex/latest/bin:/home/riccardogiorato/.local/share/mise/installs/gh/latest/gh_2.102.0_linux_amd64/bin:/home/riccardogiorato/.local/share/mise/installs/node/26.8.1/bin:/home/riccardogiorato/.local/share/mise/installs/npm-xai-official-grok/latest/node_modules/.bin:/home/riccardogiorato/.local/share/mise/installs/opencode/latest:/home/riccardogiorato/.local/share/mise/installs/pi/latest/pi:/home/riccardogiorato/.local/share/mise/shims:/usr/local/sbin:/usr/local/bin:/usr/bin:/opt/cuda/bin:/usr/bin/site_perl:/usr/bin/vendor_perl:/usr/bin/core_perl"
declare -x QT_IM_MODULE="fcitx"
declare -x SDL_IM_MODULE="fcitx"
declare -x SHELL="/usr/bin/bash"
declare -x SHLVL="3"
declare -x STRATA_API_KEY="local"
declare -x SYSTEMD_EXEC_PID="1136"
declare -x T3CODE_HOME="/home/riccardogiorato/.t3"
declare -x T3CODE_HOST="127.0.0.1"
declare -x T3CODE_PORT="3773"
declare -x T3_BOOT_SERVICE_UNIT="t3code.service"
declare -x T3_SERVICE_LAUNCHER_CONTEXT="{\"protocol\":3,\"childVersion\":\"0.1.1\",\"update\":{\"id\":\"8f3a3ec2-aa5e-4a21-947f-99ec0bdf8d66\",\"fromVersion\":\"0.1.0\",\"targetVersion\":\"0.1.1\",\"dbPath\":\"/home/riccardogiorato/.t3/userdata/statev2.sqlite\",\"status\":\"pending\"}}"
declare -x USER="riccardogiorato"
declare -x VSSCRIPT_PATH="/usr/lib/python3.14/site-packages/vapoursynth/libvsscript.so"
declare -x XDG_RUNTIME_DIR="/run/user/1000"
declare -x XMODIFIERS="@im=fcitx"
declare -x __MISE_DIFF="eAFqWVjGtDg/J6VhcV5qecOSgsSSjOk37fQz8nNT9Ysyk5MTi1Ly0zPzixJL8vX1cvKTE3P0izMSi1L1czOLU/Uz84pLEnNyivWTcxJLU1L1cxJLUotLbjqSrj8/JbUCql0/KTPvZijJRqRnwPSnZ8Qb6RkaGOkZxOdk5pVWxCfmppiZgI11INlYwPLyU1L1jcz0LPQMwSbEk25CQa5uRWKmbn5aWmZyZmKObnpRfjbMrSDj43PzU0pzUov19UA+J92J+QWpeckgZ0KD35ZkJxZkwtxTkAkArQvLUQ"
