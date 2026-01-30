# Roblox-Username-Checker

👋 Welcome to Roblox Username Validator, a Python script that validates the availability and appropriateness of Roblox usernames.

---

## 🔍 Features:
- **Manual Checks**: Enter a single username to check its validity and availability.
- **Batch Checks**: Validate a list of usernames from a `.txt` file.
- **Random Username Generation**: Generate random usernames to check availability.
- **Duplicate Removal**: Automatically removes duplicate usernames from input files.
- **Colored Output**: Get clear results with colored messages using `colorama`.
- **Async Batch Mode**: Faster batch validation with concurrency control.
- **Rate Limiting + Retries**: Smarter handling of API throttling and transient errors.
- **Local Precheck**: Basic length/character filtering before API calls.
- **Resume/Skip Checked**: Avoid re-checking usernames on reruns.
- **Exports**: Save results to CSV and JSON.
- **Discord Webhooks**: Send valid usernames or summaries to a webhook.
- **Username Ideas Mode**: Wordlists, prefixes/suffixes, optional leetspeak.
- **Proxy Support**: Optional HTTP(S) proxy for requests.

---

## ✅ Output:
- **Valid Usernames**: Saved to `valid.txt`.
- **Invalid Usernames**: Displayed in the console with specific error reasons.
- **Checked Usernames**: Saved to `checked.txt` for resume/skip.
- **Exports**: `results.csv` and `results.json` when enabled.

---

## 🚀 Requirements:
- Python 3.x
- Libraries: `requests`, `colorama`, `httpx`, `rich`

---

## 🛠 Setup:
1. Clone the repository:
   ```bash
   git clone https://github.com/VVoiddd/Roblox-Username-Checker.git
   cd Roblox-Username-Checker
   ```
2. Install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the script:
   ```bash
   python main.py
   ```

---

## Config
The script reads `config.json` (auto-created on first run). Edit it to customize:
- Batch concurrency, retries, delays, timeouts
- Precheck rules and length limits
- Output files and export paths
- Discord webhook settings
- Proxy settings
- Ideas mode wordlist/prefix/suffix settings

---

## 🎥 Demo:
Check out the video walkthrough below to see how to use the Roblox Username Checker in action!

[![Watch the Demo](https://img.youtube.com/vi/xWfc6wkExKs/0.jpg)](https://youtu.be/xWfc6wkExKs)

---

## 📸 Screenshot:
![New Version Screenshot](release.png)

---

## 🧑‍💻 Developer Credits:
- **Base idea by jprocks101**: This project was initially conceptualized by jprocks101. A big thank you for laying the groundwork!
- **Expanded by Void**: Enhancements and new features were added by Void, making it more versatile and user-friendly.

---

## 🔗 Version Info:
- **Old Version (1.0)**: [https://github.com/jprocks101/Roblox-Username-Checker](https://github.com/jprocks101/Roblox-Username-Checker)
- **New Version (2.0)**: [https://github.com/VVoiddd/Roblox-Username-Checker](https://github.com/VVoiddd/Roblox-Username-Checker)

💻 Happy Checking!
```
