import os
import re
import subprocess
import google.generativeai as genai

# === Configuration ===
PACKAGE = "open-vm-tools"
ANSIBLE_CHECK_SCRIPT = "check_and_simulate.yml"
ANSIBLE_UPGRADE_SCRIPT = "upgrade_package.yml"
OUTPUT_DIR = "."  # or use a dedicated output path if desired

# === Step 1: Run Ansible Simulation & Checks ===
def run_ansible_check(package):
    print(f"[+] Running Ansible to simulate upgrades for package: {package}")
    subprocess.run([
        "ansible-playbook", ANSIBLE_CHECK_SCRIPT, "-e", f"package_name={package}"
    ], check=True)

# === Step 2: Discover Host Files Dynamically ===
def discover_host_outputs():
    sim_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("simulate_output_") and f.endswith(".txt")]
    hosts = [re.search(r"simulate_output_(.+)\.txt", f).group(1) for f in sim_files]
    return hosts

# === Step 3: Load Results for a Host ===
def load_outputs(host):
    sim_file = os.path.join(OUTPUT_DIR, f"simulate_output_{host}.txt")
    rdep_file = os.path.join(OUTPUT_DIR, f"rdepends_output_{host}.txt")
    with open(sim_file, "r") as sim, open(rdep_file, "r") as deps:
        return sim.read(), deps.read()

# === Step 4: Gemini Risk Analysis ===
def analyze_with_gemini(sim_output, rdepends_output):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = f"""
# Task: Linux Package Upgrade Risk Analysis

Analyze the following outputs to evaluate risks in upgrading a package.

## Instructions:
1. Identify the package and version info.
2. List reverse dependencies.
3. Highlight what packages might break.
4. Assign a risk level: LOW, MEDIUM, HIGH.
5. Recommend if we should proceed.

## Format (JSON):
{{"package": "...", "current_version": "...", "target_version": "...", "risk_level": "...", "reasoning": "...", "recommendation": "..."}}

### Simulated Upgrade Output:
{sim_output}

### Reverse Dependencies:
{rdepends_output}
"""
    model = genai.GenerativeModel("models/gemini-2.0-flash")
    response = model.generate_content(prompt)
    return response.text

# === Step 5: Ask User Whether to Proceed for Each Host ===
def prompt_user_and_apply(package, host):
    choice = input(f"\n[?] Proceed with upgrade on {host}? (y/n): ")
    if choice.lower() == 'y':
        print(f"[+] Running upgrade playbook for host {host}...")
        subprocess.run([
            "ansible-playbook", ANSIBLE_UPGRADE_SCRIPT,
            "-e", f"package={package}", "--limit", host
        ])
    else:
        print(f"[-] Skipping upgrade on {host}.")

# === Main Flow ===
if __name__ == "__main__":
    run_ansible_check(PACKAGE)

    print("\n[+] Discovering hosts from simulation output...")
    discovered_hosts = discover_host_outputs()

    if not discovered_hosts:
        print("[!] No host output files found. Did the Ansible run succeed?")
        exit(1)

    for host in discovered_hosts:
        print(f"\n=== Host: {host} ===")
        try:
            sim_output, rdepends_output = load_outputs(host)
        except FileNotFoundError:
            print(f"[!] Missing output files for host {host}. Skipping.")
            continue

        print("[+] Running Gemini risk analysis...")
        report = analyze_with_gemini(sim_output, rdepends_output)
        print("\n[+] Gemini Risk Report:\n")
        print(report)

        prompt_user_and_apply(PACKAGE, host)
