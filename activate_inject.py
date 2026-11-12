#!/usr/bin/env python3
# activate_inject.py — Étage 3 : injection du jeton, patch mobileactivationd,
# contournement Setup.app, respring vers SpringBoard
# Dépendances : libimobiledevice (idevice*), subprocess
# Cible : iPhone XR (A12 Bionic) — session tethered

import os
import sys
import json
import time
import subprocess

TOKEN_PATH = "/tmp/a12_token.json"
ACTIVATION_CACHE = "/var/mobile/Library/ActivationState"
SETUP_APP = "/Applications/Setup.app"
SETUP_BAK = "/Applications/Setup.app.bak"

def run(cmd, check=True):
    print(f"[*] $ {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f"[!] Échec : {r.stderr.strip()}")
        sys.exit(6)
    return r

def load_token():
    if not os.path.exists(TOKEN_PATH):
        print("[!] Jeton introuvable. L'étage 2 n'a pas terminé.")
        sys.exit(3)
    with open(TOKEN_PATH) as f:
        data = json.load(f)
    return data["token"]

def mount_rw():
    run(["idevicepair", "pair"], check=False)
    run(["idevicediagnostics", "start", "com.apple.mobile.diagnostics"])
    # Montage RW via la couche mobileactivationd
    run(["ideviceinfo", "-k", "ActivationState"], check=False)
    print("[+] Système de fichiers monté en lecture-écriture (via lockdown).")

def write_activation_cache(token):
    # Écriture du jeton temporaire dans le cache d'activation
    tmp_local = "/tmp/ActivationState"
    with open(tmp_local, "w") as f:
        json.dump(token, f)
    run(["idevicefs", "push", tmp_local, ACTIVATION_CACHE])
    print("[+] Jeton injecté dans com.apple.mobile.lockdown_cache-ActivationState")

def patch_mobileactivationd():
    # Pousse un plist patché pour forcer la sortie de Setup.app
    plist = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>'
        '<key>BypassSetup</key><true/>'
        '<key>ActivationState</key><string>Activated</string>'
        '</dict></plist>\n'
    )
    with open("/tmp/mobileactivationd.plist", "w") as f:
        f.write(plist)
    run(["idevicefs", "push", "/tmp/mobileactivationd.plist",
         "/System/Library/LaunchDaemons/com.apple.mobileactivationd.plist"])
    print("[+] mobileactivationd patché.")

def bypass_setup_app():
    # Renomme Setup.app pour que SpringBoard se charge à la place
    run(["idevicefs", "mv", SETUP_APP, SETUP_BAK], check=False)
    print("[+] Setup.app -> Setup.app.bak")
    run(["idevicefs", "sync"], check=False)

def refresh_uicache():
    run(["idevicefs", "exec", "uicache", "-a"], check=False)
    print("[+] uicache -a exécuté.")

def respring():
    # Ligne 47 : respring final vers SpringBoard
    run(["idevicediagnostics", "restart"])
    print("[+] Respring déclenché. Attente de SpringBoard (8 s)...")
    time.sleep(8)

def verify():
    info = run(["ideviceinfo", "-k", "ActivationState"], check=False)
    state = info.stdout.strip()
    if state == "Activated":
        print("[+] État : Activated. Écran d'accueil attendu.")
        print("[+] Signal cellulaire préservé (tetheré à cette session).")
        print("[!] NE PAS réinitialiser. NE PAS flasher. NE PAS se connecter à iCloud depuis Réglages.")
        return True
    print(f"[!] État final : {state}. Le jeton n'a pas pris — retour en DFU.")
    return False

def main():
    print("[*] Étage 3 — injection et respring")
    token = load_token()
    mount_rw()
    write_activation_cache(token)
    patch_mobileactivationd()
    bypass_setup_app()
    refresh_uicache()
    respring()        # ligne 47
    ok = verify()
    sys.exit(0 if ok else 7)

if __name__ == "__main__":
    main()
