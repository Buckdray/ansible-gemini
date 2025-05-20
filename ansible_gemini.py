import os
import subprocess
import google.generativeai as genai

# === Configuration ===
PACKAGE = "curl"
HOSTNAME = "target_host"  # match inventory_hostname in Ansible
SIM_OUTPUT_FILE = f"simulate_output_{HOSTNAME}.txt"
RDEPENDS_FILE = f"rdepends_output_{HOSTNAME}.txt"
ANSIBLE_CHECK_SCRIPT = "check_and_simulate.yml"
ANSIBLE_UPGRADE_SCRIPT = "upgrade_package.yml"

# === Step 1: Run Ansible Simulation & Checks ===
def run_ansible_check(package):
    print(f"[+] Running Ansible to check/install/simulate for: {package}")
    subprocess.run([
        "ansible-playbook", ANSIBLE_CHECK_SCRIPT, "-e", f"package_name={package}"
    ])

# === Step 2: Load Results from Files ===
def load_outputs():
    with open(SIM_OUTPUT_FILE, "r") as sim, open(RDEPENDS_FILE, "r") as deps:
        return sim.read(), deps.read()

# === Step 3: Gemini Risk Analysis ===
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
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    return response.text

# === Step 4: Ask User Whether to Proceed ===
def prompt_user_and_apply(package):
    choice = input("\nDo you want to proceed with the upgrade using Ansible? (y/n): ")
    if choice.lower() == 'y':
        print("[+] Running Ansible playbook to upgrade package...")
        subprocess.run(["ansible-playbook", ANSIBLE_UPGRADE_SCRIPT, "-e", f"package={package}"])
    else:
        print("Upgrade skipped.")

# === Main Flow ===
if __name__ == "__main__":
    run_ansible_check(PACKAGE)
    
    if os.path.exists(SIM_OUTPUT_FILE) and os.path.exists(RDEPENDS_FILE):
        sim_output, rdepends_output = load_outputs()
        print("[+] Running Gemini risk analysis...")
        report = analyze_with_gemini(sim_output, rdepends_output)
        print("\n[+] Gemini Risk Report:\n")
        print(report)
        prompt_user_and_apply(PACKAGE)
    else:
        print("[!] Simulation or dependency output missing. Aborting.")
