#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
developer_dir=${DEVELOPER_DIR:-/Applications/Xcode-26.3.0.app/Contents/Developer}
workflow_backend="$repo_dir/macos/build/Build/Products/Release/Notaeo.app/Contents/Resources/backend/research-backend"
workflow_build=1
while [ "$#" -gt 0 ]; do
    case "$1" in
        --no-build) workflow_build=0 ;;
        --backend)
            shift
            if [ "$#" -eq 0 ]; then printf '%s\n' '--backend requires an executable path' >&2; exit 2; fi
            workflow_backend=$1
            ;;
        *) printf '%s\n' 'Usage: sh scripts/test_macos_workflows.sh [--no-build] [--backend PATH]' >&2; exit 2 ;;
    esac
    shift
done
cd "$repo_dir"
if [ "$workflow_build" -eq 1 ]; then
    DEVELOPER_DIR="$developer_dir" sh scripts/build_macos_app.sh
fi
if [ ! -x "$workflow_backend" ]; then
    printf '%s\n' 'Packaged backend missing or not executable. Run sh scripts/build_macos_app.sh first.' >&2
    exit 1
fi

umask 077
workflow_build_dir=$(mktemp -d "${TMPDIR:-/tmp}/notaeo-workflow-build.XXXXXX")
workflow_pid=
workflow_backend_pid=
stop_owned() {
    workflow_stop_pid=$1
    if kill -0 "$workflow_stop_pid" 2>/dev/null; then
        kill -TERM "$workflow_stop_pid" 2>/dev/null || true
        workflow_stop_ticks=0
        while kill -0 "$workflow_stop_pid" 2>/dev/null && [ "$workflow_stop_ticks" -lt 100 ]; do
            sleep 0.05
            workflow_stop_ticks=$((workflow_stop_ticks + 1))
        done
        if kill -0 "$workflow_stop_pid" 2>/dev/null; then
            kill -KILL "$workflow_stop_pid" 2>/dev/null || true
            workflow_stop_ticks=0
            while kill -0 "$workflow_stop_pid" 2>/dev/null && [ "$workflow_stop_ticks" -lt 40 ]; do
                sleep 0.05
                workflow_stop_ticks=$((workflow_stop_ticks + 1))
            done
        fi
        if kill -0 "$workflow_stop_pid" 2>/dev/null; then
            printf '%s\n' 'Owned test child could not be stopped; scratch data retained.' >&2
            return 1
        fi
    fi
    wait "$workflow_stop_pid" 2>/dev/null || true
}
cleanup() {
    workflow_cleanup_status=0
    if [ -n "$workflow_pid" ]; then
        if ! stop_owned "$workflow_pid" 2>/dev/null; then workflow_cleanup_status=1; fi
    fi
    if [ -n "$workflow_backend_pid" ]; then
        if ! stop_owned "$workflow_backend_pid" 2>/dev/null; then workflow_cleanup_status=1; fi
    fi
    if [ "$workflow_cleanup_status" -eq 0 ]; then
        rm -rf -- "$workflow_build_dir" || return 1
        [ ! -e "$workflow_build_dir" ] || return 1
    fi
    if [ "$workflow_cleanup_status" -ne 0 ]; then
        printf '%s\n' 'Owned test child could not be stopped; scratch data retained.' >&2
    fi
    return "$workflow_cleanup_status"
}
finish() {
    workflow_exit_status=$?
    trap - EXIT
    trap '' INT TERM
    cleanup || workflow_exit_status=1
    if [ "$workflow_exit_status" -eq 0 ]; then
        printf '%s\n' 'PACKAGED WORKFLOW CLEANUP PASS: owned processes stopped; scratch removed'
    fi
    exit "$workflow_exit_status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
workflow_sdk=$(DEVELOPER_DIR="$developer_dir" xcrun --sdk macosx --show-sdk-path)
workflow_arch=$(uname -m)
DEVELOPER_DIR="$developer_dir" xcrun swiftc -parse-as-library -swift-version 6 \
    -strict-concurrency=complete -sdk "$workflow_sdk" -target "$workflow_arch-apple-macos14.0" \
    macos/Research/Models.swift macos/Research/APIClient.swift \
    macos/Research/AppState.swift macos/Research/BackendProcess.swift \
    macos/Research/DownloadHandler.swift macos/Research/NativeStyle.swift \
    macos/Research/NativePresentation.swift macos/Research/SourcePasteController.swift \
    macos/WorkflowChecks/PackagedWorkflow.swift -o "$workflow_build_dir/check"
workflow_fixture="$workflow_build_dir/fixture"
mkdir "$workflow_fixture" "$workflow_fixture/home" "$workflow_fixture/tmp" "$workflow_fixture/data"
: > "$workflow_fixture/backend.log"
workflow_token=$(/usr/bin/uuidgen)
# Both children get an explicit clean environment. No host provider/operator keys.
env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin LANG=en_US.UTF-8 PYTHONUTF8=1 \
    HOME="$workflow_fixture/home" TMPDIR="$workflow_fixture/tmp/" \
    RESEARCH_DATA_DIR="$workflow_fixture/data" RESEARCH_NATIVE_DESKTOP=1 \
    RESEARCH_DESKTOP_TOKEN="$workflow_token" RESEARCH_AI_ENABLED=0 \
    "$workflow_backend" > "$workflow_fixture/backend.log" 2>&1 &
workflow_backend_pid=$!
env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME="$workflow_fixture/home" \
    TMPDIR="$workflow_fixture/tmp/" NOTAEO_WORKFLOW_TOKEN="$workflow_token" \
    "$workflow_build_dir/check" "$workflow_fixture" "$workflow_backend_pid" &
workflow_pid=$!
workflow_status=0
wait "$workflow_pid" || workflow_status=$?
workflow_pid=
if [ "$workflow_status" -ne 0 ]; then exit "$workflow_status"; fi
# Validate archive integrity, without extracting any paths.
/usr/bin/unzip -t -qq "$workflow_fixture/saved-course.zip" &
workflow_pid=$!
workflow_archive_ticks=0
while kill -0 "$workflow_pid" 2>/dev/null && [ "$workflow_archive_ticks" -lt 100 ]; do
    sleep 0.05
    workflow_archive_ticks=$((workflow_archive_ticks + 1))
done
if kill -0 "$workflow_pid" 2>/dev/null; then
    printf '%s\n' 'Export integrity check exceeded five seconds.' >&2
    exit 1
fi
workflow_status=0
wait "$workflow_pid" || workflow_status=$?
workflow_pid=
exit "$workflow_status"
