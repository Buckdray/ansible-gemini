import os
import subprocess
import google.generativeai as genai

# === Configuration ===
PACKAGE = input("Enter the package you want to assess and upgrade: ").strip()
SIM_OUTPUT_FILE = "simulate_output.txt"
RDEPENDS_FILE = "rdepends_output.txt"
ANSIBLE_PLAYBOOK = "upgrade_package.yml"
ANSIBLE_INVENTORY = "hosts.ini"  # You must define your inventory file

# === Step 1: Run Apt Simulation ===
def run_simulation(package):
    print(f"[+] Running simulation for package: {package}")
    result = subprocess.run([
        "apt-get", "--simulate", "install", package
    ], capture_output=True, text=True)

    with open(SIM_OUTPUT_FILE, "w") as f:
        f.write(result.stdout)

    return result.stdout

# === Step 2: Check Reverse Dependencies ===
def run_rdepends(package):
    print(f"[+] Checking reverse dependencies for: {package}")
    result = subprocess.run([
        "apt", "rdepends", package
    ], capture_output=True, text=True)

    with open(RDEPENDS_FILE, "w") as f:
        f.write(result.stdout)

    return result.stdout

# === Step 3: Analyze With Gemini ===
def analyze_with_gemini(sim_output, rdepends_output):
    print("[+] Sending data to Gemini for analysis...")
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

    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    return response.text

# === Step 4: Ask User Whether to Proceed ===
def prompt_user_and_apply(package):
    choice = input("\nDo you want to proceed with the upgrade using Ansible? (y/n): ")
    if choice.lower() == 'y':
        print(f"[+] Running Ansible playbook to upgrade {package}...\n")
        subprocess.run([
            "ansible-playbook",
            ANSIBLE_PLAYBOOK,
            "-i", ANSIBLE_INVENTORY,
            "-e", f"package={package}"
        ])
    else:
        print("[!] Upgrade skipped by user.")

# === Main Flow ===
if __name__ == "__main__":
    try:
        sim_output = run_simulation(PACKAGE)
        rdepends_output = run_rdepends(PACKAGE)

        report = analyze_with_gemini(sim_output, rdepends_output)

        print("\n[+] Gemini Risk Analysis Report:\n")
        print(report)

        prompt_user_and_apply(PACKAGE)

    except Exception as e:
        print(f"[!] Error: {str(e)}")
