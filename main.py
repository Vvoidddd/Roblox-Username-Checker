import requests
from colorama import Fore, Style, init
import os
import random
import string
import sys
import time

# Initialize colorama
init(autoreset=True)

# ------------------- Utilities -------------------

def read_example_usernames(file_path="examplenames.txt"):
    """Read example usernames from a file."""
    if not os.path.isfile(file_path):
        print(f"{Fore.RED}File {file_path} does not exist.{Style.RESET_ALL}")
        return []
    with open(file_path, "r") as file:
        return file.read().splitlines()

def generate_username(min_length=4, max_length=15):
    """Generate a random username with letters and digits."""
    characters = string.ascii_letters + string.digits
    username_length = random.randint(min_length, max_length)
    return ''.join(random.choice(characters) for _ in range(username_length))

def generate_mashed_username(usernames, max_length=15):
    """Mash together two usernames randomly from a list."""
    if len(usernames) < 2:
        return generate_username()
    random.shuffle(usernames)
    mashed_username = ''.join(usernames[:2]).replace(' ', '')[:max_length]
    return mashed_username

def validate_username(username):
    """Validate username availability via Roblox API."""
    url = f"https://auth.roblox.com/v1/usernames/validate?birthday=2006-09-21T07:00:00.000Z&context=Signup&username={username}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        code_map = {
            0: (Fore.GREEN, "Valid"),
            1: (Fore.RED, "Invalid (already in use)"),
            2: (Fore.RED, "Invalid (not appropriate for Roblox)"),
            10: (Fore.YELLOW, "Invalid (might contain private info)")
        }
        color, message = code_map.get(data.get("code", -1), (Fore.RED, "Unable to validate"))
        return f"{color}{message}: {username}{Style.RESET_ALL}"
    except requests.RequestException:
        return f"{Fore.RED}Unable to access Roblox API{Style.RESET_ALL}"

def save_valid_username(username, filename="valid.txt"):
    """Append a valid username to file."""
    with open(filename, 'a') as file:
        file.write(username + '\n')

def remove_duplicates(usernames):
    """Remove duplicates from a list of usernames."""
    seen = set()
    unique = []
    for username in usernames:
        if username not in seen:
            unique.append(username)
            seen.add(username)
    return unique

def update_progress_bar(iteration, total, bar_length=50):
    """Display a progress bar in terminal."""
    progress = iteration / total if total else 0
    arrow = '=' * max(int(round(progress * bar_length)) - 1, 0)
    spaces = ' ' * (bar_length - len(arrow))
    sys.stdout.write(f"\r[{arrow}{spaces}] {int(progress * 100)}%")
    sys.stdout.flush()

def show_developer_info():
    """Display developer credits."""
    print(f"\n{Fore.CYAN}Thanks to jprocks101 for the base idea!{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Expanded and improved by Void with new features and UI enhancements.{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Forked version 2.0: https://github.com/VVoidddd/Roblox-Username-Checker{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}Follow Void at: https://www.twitch.tv/voidedluvr{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}Other projects: https://github.com/Vvoidddd{Style.RESET_ALL}")
    input(f"\n{Fore.MAGENTA}[Press Enter to return to the menu]{Fore.RESET}")

# ------------------- Main Menu -------------------

def main_menu():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"""
 {Fore.BLUE} 
 __   __   _____ _               _               ___   ______ _              _   ___
 \ \ / /  / ____| |             | |             |  _| |  ____(_)            | | |_  |
  \ V /  | |    | |__   ___  ___| | _____ _ __  | |   | |__   ___  _____  __| |   | |
   > <   | |    | '_ \ / _ \/ __| |/ / _ \ '__| | |   |  __| | \ \/ / _ \/ _` |   | |
  / . \  | |____| | | |  __/ (__|   <  __/ |    | |   | |    | |>  <  __/ (_| |   | |
 /_/ \_\  \_____|_| |_|\___|\___|_|\_\___|_|    | |_  |_|    |_/_/\_\___|\__,_|  _| |
                                                |___|                           |___|
{Style.RESET_ALL}""")

        print(f"{Fore.MAGENTA}[+]{Fore.RESET} Choose an option:")
        print(f"{Fore.MAGENTA}[1]{Fore.RESET} Manually enter a username")
        print(f"{Fore.MAGENTA}[2]{Fore.RESET} Check a list of usernames from a file")
        print(f"{Fore.MAGENTA}[3]{Fore.RESET} Generate random usernames")
        print(f"{Fore.MAGENTA}[4]{Fore.RESET} Generate mashed-up usernames from examples")
        print(f"{Fore.MAGENTA}[5]{Fore.RESET} Developer Info")
        print(f"{Fore.MAGENTA}[0]{Fore.RESET} Exit")
        choice = input(f"{Fore.MAGENTA}[>]{Fore.RESET} ")

        if choice == '1':
            username = input(f"{Fore.MAGENTA}[+]{Fore.RESET} Enter username: ")
            print(validate_username(username))

        elif choice == '2':
            filename = input(f"{Fore.MAGENTA}[+]{Fore.RESET} Enter filename (.txt): ")
            if not os.path.isfile(filename):
                print(f"{Fore.RED}File not found.{Style.RESET_ALL}")
                continue

            with open(filename, "r") as f:
                usernames = f.read().splitlines()

            print(f"{Fore.CYAN}Loaded {len(usernames)} usernames.{Style.RESET_ALL}")

            # Remove duplicates
            if len(usernames) != len(set(usernames)):
                resp = input(f"{Fore.YELLOW}Remove duplicates? (y/n){Style.RESET_ALL} ")
                if resp.lower() == 'y':
                    usernames = remove_duplicates(usernames)
                    print(f"{Fore.GREEN}Duplicates removed.{Style.RESET_ALL}")

            valid_count = 0
            invalid_count = 0
            for i, username in enumerate(usernames):
                result = validate_username(username)
                print(f"\r{result}", end="")
                if "Valid" in result:
                    valid_count += 1
                    save_valid_username(username)
                else:
                    invalid_count += 1
                update_progress_bar(i + 1, len(usernames))
                time.sleep(0.05)  # Optional delay

            print(f"\n{Fore.GREEN}Valid: {valid_count}{Style.RESET_ALL}")
            print(f"{Fore.RED}Invalid: {invalid_count}{Style.RESET_ALL}")

        elif choice == '3':
            min_len = int(input(f"{Fore.MAGENTA}[+]{Fore.RESET} Min length (4-15): "))
            max_len = int(input(f"{Fore.MAGENTA}[+]{Fore.RESET} Max length (4-15): "))
            num = int(input(f"{Fore.MAGENTA}[+]{Fore.RESET} How many usernames to generate? "))
            for _ in range(num):
                username = generate_username(min_len, max_len)
                print(f"{Fore.CYAN}Generated: {username}{Style.RESET_ALL} - {validate_username(username)}")
                save_valid_username(username)

        elif choice == '4':
            examples = read_example_usernames()
            if not examples:
                continue
            num = int(input(f"{Fore.MAGENTA}[+]{Fore.RESET} How many mashed-up usernames? "))
            for _ in range(num):
                username = generate_mashed_username(examples)
                print(f"{Fore.CYAN}Mashed-up: {username}{Style.RESET_ALL} - {validate_username(username)}")
                save_valid_username(username)

        elif choice == '5':
            show_developer_info()

        elif choice == '0':
            print(f"{Fore.MAGENTA}Exiting...{Style.RESET_ALL}")
            break
        else:
            print(f"{Fore.RED}Invalid choice.{Style.RESET_ALL}")
            time.sleep(1)

if __name__ == "__main__":
    main_menu()
