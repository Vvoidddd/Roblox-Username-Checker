import asyncio
import csv
import json
import os
import random
import string
import sys
import time
from datetime import datetime, timezone

import requests
from colorama import Fore, Style, init

try:
    import httpx
except ImportError:
    httpx = None

try:
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Initialize colorama
init(autoreset=True)

CONFIG_PATH = "config.json"

DEFAULT_CONFIG = {
    "min_length": 4,
    "max_length": 15,
    "request_delay": 0.05,
    "request_timeout": 10,
    "max_retries": 3,
    "retry_backoff_base": 0.5,
    "concurrency": 10,
    "use_async_batch": True,
    "basic_precheck": True,
    "allow_letters": True,
    "allow_digits": True,
    "allow_underscore": True,
    "skip_checked": True,
    "output_valid": "valid.txt",
    "output_checked": "checked.txt",
    "export_enabled": True,
    "export_csv": "results.csv",
    "export_json": "results.json",
    "webhook_url": "",
    "webhook_mode": "valid_only",
    "webhook_username": "Roblox Checker",
    "webhook_avatar_url": "",
    "proxy": "",
    "ideas_wordlist": "examplenames.txt",
    "ideas_prefixes": [],
    "ideas_suffixes": [],
    "ideas_use_leetspeak": True,
}

CODE_MAP = {
    0: (Fore.GREEN, "Valid"),
    1: (Fore.RED, "Invalid (already in use)"),
    2: (Fore.RED, "Invalid (not appropriate for Roblox)"),
    10: (Fore.YELLOW, "Invalid (might contain private info)"),
}

RICH_CONSOLE = Console() if RICH_AVAILABLE else None


# ------------------- Utilities -------------------

def ensure_config_file():
    if not os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH, "w") as file:
            json.dump(DEFAULT_CONFIG, file, indent=2)
        print(f"{Fore.CYAN}Created default {CONFIG_PATH}. Edit it to customize behavior.{Style.RESET_ALL}")


def load_config():
    ensure_config_file()
    cfg = DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r") as file:
            data = json.load(file)
        cfg.update(data)
    except (OSError, json.JSONDecodeError):
        print(f"{Fore.YELLOW}Warning: Failed to load {CONFIG_PATH}. Using defaults.{Style.RESET_ALL}")
    return cfg


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def read_lines(file_path):
    if not os.path.isfile(file_path):
        return []
    with open(file_path, "r") as file:
        return [line.strip() for line in file.read().splitlines() if line.strip()]


def read_example_usernames(file_path="examplenames.txt"):
    return read_lines(file_path)


def generate_username(min_length=4, max_length=15):
    characters = string.ascii_letters + string.digits
    username_length = random.randint(min_length, max_length)
    return "".join(random.choice(characters) for _ in range(username_length))


def leetspeak(text):
    translations = str.maketrans({
        "a": "4",
        "e": "3",
        "i": "1",
        "o": "0",
        "s": "5",
        "t": "7",
    })
    return text.translate(translations)


def generate_idea_usernames(words, prefixes, suffixes, count=10, use_leet=True, max_length=15):
    if not words:
        return []
    results = []
    for _ in range(count):
        parts = []
        if prefixes:
            parts.append(random.choice(prefixes))
        parts.append(random.choice(words))
        if random.random() < 0.5 and len(words) > 1:
            parts.append(random.choice(words))
        if suffixes:
            parts.append(random.choice(suffixes))
        candidate = "".join(parts)
        candidate = candidate.replace(" ", "")
        if use_leet and random.random() < 0.4:
            candidate = leetspeak(candidate)
        candidate = candidate[:max_length]
        results.append(candidate)
    return results


def generate_mashed_username(usernames, max_length=15):
    if len(usernames) < 2:
        return generate_username()
    random.shuffle(usernames)
    mashed_username = "".join(usernames[:2]).replace(" ", "")[:max_length]
    return mashed_username


def remove_duplicates(usernames):
    seen = set()
    unique = []
    for username in usernames:
        if username not in seen:
            unique.append(username)
            seen.add(username)
    return unique


def load_checked_set(filename):
    return set(read_lines(filename))


def append_line(filename, line):
    with open(filename, "a") as file:
        file.write(line + "\n")


def get_proxy_config(cfg):
    proxy = str(cfg.get("proxy", "")).strip()
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def basic_precheck(username, cfg):
    if not cfg.get("basic_precheck", True):
        return True, ""
    length = len(username)
    if length < cfg["min_length"] or length > cfg["max_length"]:
        return False, f"Invalid length ({length})"
    allowed = set()
    if cfg.get("allow_letters", True):
        allowed.update(string.ascii_letters)
    if cfg.get("allow_digits", True):
        allowed.update(string.digits)
    if cfg.get("allow_underscore", True):
        allowed.add("_")
    if allowed:
        for ch in username:
            if ch not in allowed:
                return False, "Invalid characters"
    return True, ""


def build_result(username, ok, code, message, source):
    return {
        "username": username,
        "ok": ok,
        "code": code,
        "message": message,
        "source": source,
        "checked_at": now_iso(),
    }


def map_code(code):
    color, message = CODE_MAP.get(code, (Fore.RED, "Unable to validate"))
    return color, message


def format_result(result):
    username = result["username"]
    if result["source"] == "local":
        return f"{Fore.YELLOW}Skipped (local rule): {username} - {result['message']}{Style.RESET_ALL}"
    if result["source"] == "error":
        return f"{Fore.RED}{result['message']}: {username}{Style.RESET_ALL}"
    color, message = map_code(result["code"])
    return f"{color}{message}: {username}{Style.RESET_ALL}"


def validate_username_sync(username, session, cfg):
    ok, reason = basic_precheck(username, cfg)
    if not ok:
        return build_result(username, False, "local_invalid", reason, "local")

    url = (
        "https://auth.roblox.com/v1/usernames/validate"
        f"?birthday=2006-09-21T07:00:00.000Z&context=Signup&username={username}"
    )
    retryable = {429, 500, 502, 503, 504}
    proxies = get_proxy_config(cfg)

    for attempt in range(cfg["max_retries"] + 1):
        try:
            resp = session.get(url, timeout=cfg["request_timeout"], proxies=proxies)
            if resp.status_code in retryable and attempt < cfg["max_retries"]:
                time.sleep(cfg["retry_backoff_base"] * (2 ** attempt))
                continue
            if resp.status_code >= 400:
                return build_result(username, False, resp.status_code, "API error", "error")
            data = resp.json()
            code = data.get("code", -1)
            _, message = map_code(code)
            return build_result(username, code == 0, code, message, "api")
        except requests.RequestException:
            if attempt < cfg["max_retries"]:
                time.sleep(cfg["retry_backoff_base"] * (2 ** attempt))
                continue
            return build_result(username, False, "error", "Unable to access Roblox API", "error")
        finally:
            if cfg.get("request_delay", 0) > 0:
                time.sleep(cfg["request_delay"])


def send_webhook_sync(content, cfg, session):
    url = str(cfg.get("webhook_url", "")).strip()
    if not url:
        return
    payload = {"content": content}
    username = str(cfg.get("webhook_username", "")).strip()
    avatar_url = str(cfg.get("webhook_avatar_url", "")).strip()
    if username:
        payload["username"] = username
    if avatar_url:
        payload["avatar_url"] = avatar_url
    try:
        session.post(url, json=payload, timeout=cfg["request_timeout"])
    except requests.RequestException:
        pass


def export_results(results, cfg):
    if not cfg.get("export_enabled", True):
        return
    csv_path = cfg.get("export_csv", "results.csv")
    json_path = cfg.get("export_json", "results.json")
    if csv_path:
        with open(csv_path, "w", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["username", "ok", "code", "message", "source", "checked_at"],
            )
            writer.writeheader()
            writer.writerows(results)
    if json_path:
        with open(json_path, "w") as file:
            json.dump(results, file, indent=2)


def update_progress_bar(iteration, total, start_time, bar_length=40):
    progress = iteration / total if total else 0
    arrow = "=" * max(int(round(progress * bar_length)) - 1, 0)
    spaces = " " * (bar_length - len(arrow))
    elapsed = time.time() - start_time
    rate = iteration / elapsed if elapsed > 0 else 0
    remaining = (total - iteration) / rate if rate > 0 else 0
    sys.stdout.write(
        f"\r[{arrow}{spaces}] {int(progress * 100)}% "
        f"({iteration}/{total}) {rate:.2f}/s ETA {int(remaining)}s"
    )
    sys.stdout.flush()


def show_summary_table(results):
    if not RICH_AVAILABLE:
        return
    table = Table(title="Batch Summary")
    table.add_column("Username", style="cyan")
    table.add_column("Status")
    table.add_column("Code")
    table.add_column("Source")
    for result in results[:50]:
        status = "OK" if result["ok"] else "NO"
        table.add_row(result["username"], status, str(result["code"]), result["source"])
    RICH_CONSOLE.print(table)


# ------------------- Async Batch -------------------

async def validate_username_async(username, client, cfg):
    ok, reason = basic_precheck(username, cfg)
    if not ok:
        return build_result(username, False, "local_invalid", reason, "local")

    url = (
        "https://auth.roblox.com/v1/usernames/validate"
        f"?birthday=2006-09-21T07:00:00.000Z&context=Signup&username={username}"
    )
    retryable = {429, 500, 502, 503, 504}

    for attempt in range(cfg["max_retries"] + 1):
        try:
            resp = await client.get(url)
            if resp.status_code in retryable and attempt < cfg["max_retries"]:
                await asyncio.sleep(cfg["retry_backoff_base"] * (2 ** attempt))
                continue
            if resp.status_code >= 400:
                return build_result(username, False, resp.status_code, "API error", "error")
            data = resp.json()
            code = data.get("code", -1)
            _, message = map_code(code)
            return build_result(username, code == 0, code, message, "api")
        except Exception:
            if attempt < cfg["max_retries"]:
                await asyncio.sleep(cfg["retry_backoff_base"] * (2 ** attempt))
                continue
            return build_result(username, False, "error", "Unable to access Roblox API", "error")
        finally:
            if cfg.get("request_delay", 0) > 0:
                await asyncio.sleep(cfg["request_delay"])


async def send_webhook_async(content, cfg, client):
    url = str(cfg.get("webhook_url", "")).strip()
    if not url:
        return
    payload = {"content": content}
    username = str(cfg.get("webhook_username", "")).strip()
    avatar_url = str(cfg.get("webhook_avatar_url", "")).strip()
    if username:
        payload["username"] = username
    if avatar_url:
        payload["avatar_url"] = avatar_url
    try:
        await client.post(url, json=payload)
    except Exception:
        pass


async def async_batch_check(usernames, cfg):
    results = []
    semaphore = asyncio.Semaphore(cfg["concurrency"])
    proxy = str(cfg.get("proxy", "")).strip() or None
    timeout = cfg.get("request_timeout", 10)

    async with httpx.AsyncClient(timeout=timeout, proxies=proxy) as client:
        async def worker(username):
            async with semaphore:
                return await validate_username_async(username, client, cfg)

        tasks = [asyncio.create_task(worker(u)) for u in usernames]
        total = len(tasks)
        start = time.time()

        progress = None
        task_id = None
        if RICH_AVAILABLE:
            progress = Progress(
                TextColumn("{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
            )
            progress.start()
            task_id = progress.add_task("Checking", total=total)

        for idx, coro in enumerate(asyncio.as_completed(tasks), start=1):
            result = await coro
            results.append(result)
            if progress:
                progress.update(task_id, advance=1)
            else:
                update_progress_bar(idx, total, start)

        if progress:
            progress.stop()
        else:
            print()

    return results


# ------------------- Main Menu -------------------


def show_developer_info():
    print(f"\n{Fore.CYAN}Thanks to jprocks101 for the base idea!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Expanded and improved by Void with new features and UI enhancements.{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Forked version 2.0: https://github.com/VVoidddd/Roblox-Username-Checker{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}Follow Void at: https://www.twitch.tv/voidedluvr{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}Other projects: https://github.com/Vvoidddd{Style.RESET_ALL}")
    input(f"\n{Fore.MAGENTA}[Press Enter to return to the menu]{Fore.RESET}")


def check_list_from_file(cfg):
    filename = input(f"{Fore.MAGENTA}[+]{Fore.RESET} Enter filename (.txt): ")
    if not os.path.isfile(filename):
        print(f"{Fore.RED}File not found.{Style.RESET_ALL}")
        return

    with open(filename, "r") as f:
        usernames = [line.strip() for line in f.read().splitlines() if line.strip()]

    print(f"{Fore.CYAN}Loaded {len(usernames)} usernames.{Style.RESET_ALL}")

    if len(usernames) != len(set(usernames)):
        resp = input(f"{Fore.YELLOW}Remove duplicates? (y/n){Style.RESET_ALL} ")
        if resp.lower() == "y":
            usernames = remove_duplicates(usernames)
            print(f"{Fore.GREEN}Duplicates removed.{Style.RESET_ALL}")

    checked_file = cfg.get("output_checked", "checked.txt")
    checked = load_checked_set(checked_file) if cfg.get("skip_checked", True) else set()
    if checked:
        skip_count = sum(1 for u in usernames if u in checked)
        usernames = [u for u in usernames if u not in checked]
        print(f"{Fore.CYAN}Skipping {skip_count} already checked usernames.{Style.RESET_ALL}")

    if not usernames:
        print(f"{Fore.YELLOW}No usernames to check.{Style.RESET_ALL}")
        return

    results = []
    valid_count = 0
    invalid_count = 0

    webhook_mode = str(cfg.get("webhook_mode", "valid_only")).lower()

    if cfg.get("use_async_batch", True) and httpx is None:
        print(f"{Fore.YELLOW}Warning: httpx not installed. Falling back to sync batch mode.{Style.RESET_ALL}")

    if cfg.get("use_async_batch", True) and httpx is not None:
        results = asyncio.run(async_batch_check(usernames, cfg))
        session = requests.Session()
        for result in results:
            if result["ok"]:
                valid_count += 1
                append_line(cfg.get("output_valid", "valid.txt"), result["username"])
            else:
                invalid_count += 1
            append_line(checked_file, result["username"])

            if webhook_mode in {"valid_only", "all"}:
                if webhook_mode == "all" or result["ok"]:
                    send_webhook_sync(format_result(result).replace(Style.RESET_ALL, ""), cfg, session)
        session.close()
    else:
        session = requests.Session()
        start = time.time()
        total = len(usernames)
        for i, username in enumerate(usernames, start=1):
            result = validate_username_sync(username, session, cfg)
            results.append(result)
            print(f"\r{format_result(result)}", end="")
            if result["ok"]:
                valid_count += 1
                append_line(cfg.get("output_valid", "valid.txt"), username)
            else:
                invalid_count += 1
            append_line(checked_file, username)

            if webhook_mode in {"valid_only", "all"}:
                if webhook_mode == "all" or result["ok"]:
                    send_webhook_sync(format_result(result).replace(Style.RESET_ALL, ""), cfg, session)

            update_progress_bar(i, total, start)
        print()
        session.close()

    print(f"{Fore.GREEN}Valid: {valid_count}{Style.RESET_ALL}")
    print(f"{Fore.RED}Invalid: {invalid_count}{Style.RESET_ALL}")

    if webhook_mode == "summary" and results:
        summary = f"Batch complete. Valid: {valid_count} Invalid: {invalid_count} Total: {len(results)}"
        session = requests.Session()
        send_webhook_sync(summary, cfg, session)
        session.close()

    export_results(results, cfg)
    show_summary_table(results)


def main_menu():
    cfg = load_config()
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(
            f"""
 {Fore.BLUE}
 __   __   _____ _               _               ___   ______ _              _   ___
 \\ \\ / /  / ____| |             | |             |  _| |  ____(_)            | | |_  |
  \\ V /  | |    | |__   ___  ___| | _____ _ __  | |   | |__   ___  _____  __| |   | |
   > <   | |    | '_ \\ / _ \\ / __| |/ / _ \\ '__| | |   |  __| | \\ \\ / / _ \\ / _` |   | |
  / . \\  | |____| | | |  __/ (__|   <  __/ |    | |   | |    | |>  <  __/ (_| |   | |
 /_/ \\_\\  \\_____|_| |_|\\___|\\___|_|\\_\\___|_|    | |_  |_|    |_/_/\\_\\___|\\__,_|  _| |
                                                |___|                           |___|
{Style.RESET_ALL}"""
        )

        print(f"{Fore.MAGENTA}[+]{Fore.RESET} Choose an option (config: {CONFIG_PATH}):")
        print(f"{Fore.MAGENTA}[1]{Fore.RESET} Manually enter a username")
        print(f"{Fore.MAGENTA}[2]{Fore.RESET} Check a list of usernames from a file")
        print(f"{Fore.MAGENTA}[3]{Fore.RESET} Generate random usernames")
        print(f"{Fore.MAGENTA}[4]{Fore.RESET} Generate mashed-up usernames from examples")
        print(f"{Fore.MAGENTA}[5]{Fore.RESET} Developer Info")
        print(f"{Fore.MAGENTA}[6]{Fore.RESET} Username ideas (wordlists / prefixes / leetspeak)")
        print(f"{Fore.MAGENTA}[0]{Fore.RESET} Exit")
        choice = input(f"{Fore.MAGENTA}[>]{Fore.RESET} ")

        if choice == "1":
            username = input(f"{Fore.MAGENTA}[+]{Fore.RESET} Enter username: ")
            session = requests.Session()
            result = validate_username_sync(username, session, cfg)
            print(format_result(result))
            session.close()

        elif choice == "2":
            check_list_from_file(cfg)

        elif choice == "3":
            min_len = int(input(f"{Fore.MAGENTA}[+]{Fore.RESET} Min length (4-15): "))
            max_len = int(input(f"{Fore.MAGENTA}[+]{Fore.RESET} Max length (4-15): "))
            num = int(input(f"{Fore.MAGENTA}[+]{Fore.RESET} How many usernames to generate? "))
            session = requests.Session()
            for _ in range(num):
                username = generate_username(min_len, max_len)
                result = validate_username_sync(username, session, cfg)
                print(f"{Fore.CYAN}Generated: {username}{Style.RESET_ALL} - {format_result(result)}")
                if result["ok"]:
                    append_line(cfg.get("output_valid", "valid.txt"), username)
            session.close()

        elif choice == "4":
            examples = read_example_usernames()
            if not examples:
                print(f"{Fore.RED}No examples found.{Style.RESET_ALL}")
                time.sleep(1)
                continue
            num = int(input(f"{Fore.MAGENTA}[+]{Fore.RESET} How many mashed-up usernames? "))
            session = requests.Session()
            for _ in range(num):
                username = generate_mashed_username(examples)
                result = validate_username_sync(username, session, cfg)
                print(f"{Fore.CYAN}Mashed-up: {username}{Style.RESET_ALL} - {format_result(result)}")
                if result["ok"]:
                    append_line(cfg.get("output_valid", "valid.txt"), username)
            session.close()

        elif choice == "5":
            show_developer_info()

        elif choice == "6":
            words = read_lines(cfg.get("ideas_wordlist", "examplenames.txt"))
            prefixes = cfg.get("ideas_prefixes", [])
            suffixes = cfg.get("ideas_suffixes", [])
            use_leet = cfg.get("ideas_use_leetspeak", True)

            if not words:
                print(f"{Fore.RED}Wordlist is empty. Update ideas_wordlist in {CONFIG_PATH}.{Style.RESET_ALL}")
                time.sleep(1)
                continue

            count = int(input(f"{Fore.MAGENTA}[+]{Fore.RESET} How many ideas? "))
            ideas = generate_idea_usernames(words, prefixes, suffixes, count=count, use_leet=use_leet, max_length=cfg["max_length"])
            session = requests.Session()
            for username in ideas:
                result = validate_username_sync(username, session, cfg)
                print(f"{Fore.CYAN}Idea: {username}{Style.RESET_ALL} - {format_result(result)}")
                if result["ok"]:
                    append_line(cfg.get("output_valid", "valid.txt"), username)
            session.close()

        elif choice == "0":
            print(f"{Fore.MAGENTA}Exiting...{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}Invalid choice.{Style.RESET_ALL}")
            time.sleep(1)


if __name__ == "__main__":
    main_menu()
