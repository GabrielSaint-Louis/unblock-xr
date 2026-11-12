#!/usr/bin/env bash
# dfu_handshake.sh — Étage 1 : détection DFU, verrouillage CPID A12, capture ECID
# Dépendances : libirecovery (irecovery), libusb
# Cible : iPhone XR (A12 Bionic, CPID 0x8020)

set -euo pipefail

CPID_A12="0x8020"
POLL_INTERVAL=0.25
MAX_ATTEMPTS=240   # ~60 s de polling
ATTEMPT=0
ECID=""

echo "[*] Étage 1 — attente du mode DFU sur le bus USB..."

while [ "$ATTEMPT" -lt "$MAX_ATTEMPTS" ]; do
    ATTEMPT=$((ATTEMPT + 1))

    # irecovery -q renvoie un bloc clé:valeur si un appareil est en DFU/Recovery
    INFO="$(irecovery -q 2>/dev/null || true)"

    if echo "$INFO" | grep -q "MODE: DFU"; then
        CPID="$(echo "$INFO" | awk -F': ' '/CPID/ {print $2}' | tr -d '[:space:]')"

        if [ "$CPID" != "$CPID_A12" ]; then
            echo "[!] CPID détecté = $CPID — ce n'est pas un A12. Pipeline Path B annulé."
            echo "[!] Ce script ne s'exécute que sur CPID $CPID_A12 (iPhone XR)."
            exit 2
        fi

        ECID="$(echo "$INFO" | awk -F': ' '/ECID/ {print $2}' | tr -d '[:space:]')"

        if [ -z "$ECID" ]; then
            echo "[!] ECID introuvable dans la réponse irecovery. Retour en DFU requis."
            exit 3
        fi

        echo "[+] Appareil confirmé : A12 Bionic (CPID $CPID)"
        echo "[+] ECID capturé : $ECID"
        export DEVICE_ECID="$ECID"
        export DEVICE_CPID="$CPID"

        # Écriture de l'environnement pour l'étage 2
        printf 'DEVICE_ECID=%s\nDEVICE_CPID=%s\n' "$ECID" "$CPID" > /tmp/a12_pathb.env
        echo "[+] Environnement exporté vers /tmp/a12_pathb.env"
        echo "[*] Étage 1 terminé. Passage à a12_pathb.py."
        exit 0
    fi

    sleep "$POLL_INTERVAL"
done

echo "[!] Timeout : aucun appareil en DFU détecté après $MAX_ATTEMPTS tentatives."
echo "[!] Vérifie la combinaison : Vol+, Vol-, Side jusqu'à écran noir, puis Vol- + Side 5 s, relâche Side, garde Vol- 10 s."
exit 1
