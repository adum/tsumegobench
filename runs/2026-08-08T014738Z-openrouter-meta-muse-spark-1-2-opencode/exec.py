import subprocess, sys, pathlib
result = subprocess.run([sys.executable, "final_builder.py"], capture_output=True, text=True, cwd="/mnt/c/Users/Adam/Documents/go problem creation/runs/2026-08-08T014738Z-openrouter-meta-muse-spark-1-2-opencode")
print("STDOUT:", result.stdout[:4000])
print("STDERR:", result.stderr[:4000])
print("returncode", result.returncode)
