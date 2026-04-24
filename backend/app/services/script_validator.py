import re
from typing import Any

import yaml


class ScriptValidator:
    """Static analysis for submitted scripts (defence-in-depth before Docker sandbox)."""

    ALLOWED_MODULES: list[str] = [
        "copy", "apt", "yum", "dnf", "file", "template", "service",
        "user", "group", "lineinfile", "blockinfile", "get_url",
        "unarchive", "stat", "debug", "assert", "fail", "set_fact",
        "include_vars", "include_tasks", "import_tasks", "package",
        "pip", "git", "cron", "mount", "sysctl",
    ]

    # SECURITY: these modules allow arbitrary host command execution
    FORBIDDEN_MODULES: list[str] = ["shell", "raw", "command", "script", "expect"]

    # Task-level directives that are not module names (skip allow-list check)
    ALLOWED_TASK_DIRECTIVES: frozenset[str] = frozenset({
        "name", "when", "register", "loop", "vars", "notify",
        "tags", "become", "ignore_errors", "failed_when",
        "changed_when", "block", "rescue", "always", "no_log",
        "with_items", "with_list",
    })

    _SHELL_PATTERNS: list[tuple[str, str]] = [
        (r"rm\s+-[rRf]{1,3}\s*/", "Destructive rm -rf / pattern"),
        (r"rm\s+--no-preserve-root", "--no-preserve-root is forbidden"),
        (r"\bmkfs\b", "Filesystem formatting (mkfs) is forbidden"),
        (r"\bdd\s+if=", "dd if= may overwrite block devices"),
        (r":\(\)\{.*:\|.*:&", "Fork-bomb pattern detected"),
        (r">\s*/dev/(s?d[a-z]|nvme)", "Direct block device write"),
        (r"\bchmod\s+[0-7]*777", "World-writable chmod"),
        (r"curl\s+.*\|\s*(ba)?sh", "Remote code execution via curl|sh"),
        (r"wget\s+.*-O\s*-\s*\|", "Remote code execution via wget pipe"),
        (r"\beval\b", "eval of dynamic code is forbidden"),
        (r"\b(sudo|su)\b", "sudo/su is forbidden inside the sandbox"),
    ]

    @classmethod
    def validate_ansible_playbook(cls, content: str) -> tuple[bool, list[str]]:
        errors: list[str] = []
        try:
            playbook: Any = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            return False, [f"YAML parse error: {exc}"]

        if not isinstance(playbook, list):
            return False, ["Playbook must be a YAML list of plays"]

        for play_idx, play in enumerate(playbook):
            if not isinstance(play, dict):
                errors.append(f"Play #{play_idx} is not a mapping")
                continue
            tasks: list = (
                play.get("tasks", []) + play.get("pre_tasks", [])
                + play.get("post_tasks", []) + play.get("handlers", [])
            )
            for task_idx, task in enumerate(tasks):
                if not isinstance(task, dict):
                    continue
                loc = f"play #{play_idx}, task #{task_idx}"
                for key in task:
                    short = key.split(".")[-1]
                    if short in cls.FORBIDDEN_MODULES:
                        errors.append(f"{loc}: forbidden module '{key}'")
                    elif short not in cls.ALLOWED_MODULES and key not in cls.ALLOWED_TASK_DIRECTIVES:
                        errors.append(f"{loc}: module '{key}' is not in the allow-list")

        return len(errors) == 0, errors

    @classmethod
    def validate_shell_script(cls, content: str) -> tuple[bool, list[str]]:
        errors: list[str] = []
        for pattern, message in cls._SHELL_PATTERNS:
            if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                errors.append(message)
        return len(errors) == 0, errors
