CHECK-LIST — DÉVERROUILLAGE iPHONE XR (A12) — PIPELINE PATH B

ÉTAPE 1 — Préparation matérielle

□ Vérifier que le XR est bien un A12 (CPID 0x8020 — confirmé par le script, pas à l'œil)
□ Utiliser un câble Lightning data d'origine (pas un câble charge seule)
□ Brancher directement sur le portable Linux (pas de hub USB)
□ Vérifier que libirecovery, libimobiledevice, pyusb, requests sont installés
□ Vérifier que le dossier contient les 3 fichiers : dfu_handshake.sh, a12_pathb.py, activate_inject.py
ÉTAPE 2 — Mise en DFU (à refaire à chaque tentative)

□ Volume Haut, relâcher
□ Volume Bas, relâcher
□ Maintenir le bouton latéral (Side) jusqu'à écran noir
□ Sans lâcher Side, maintenir Volume Bas pendant 5 secondes
□ Relâcher Side, garder Volume Bas enfoncé 10 secondes
□ L'écran reste noir → DFU confirmé. Si logo Apple → recovery, recommencer l'étape 2
ÉTAPE 3 — Portier (étage 1)

□ chmod +x dfu_handshake.sh
□ ./dfu_handshake.sh
□ Vérifier la sortie : [+] Appareil confirmé : A12 Bionic et [+] ECID capturé
□ Vérifier que /tmp/a12_pathb.env existe
□ Si CPID ≠ 0x8020 ou timeout → revenir à l'étape 2
ÉTAPE 4 — Handshake (étage 2) — fenêtre étroite

□ python3 a12_pathb.py
□ Attendre [+] Descripteur altéré renvoyé au BootROM
□ Attendre [+] Handshake accepté (200). Session valide ~90 s.
□ Vérifier que /tmp/a12_token.json existe
□ Si 401/403 → revenir à l'étape 2 immédiatement
ÉTAPE 5 — Injection (étage 3) — lancer dans les 90 secondes

□ python3 activate_inject.py tout de suite après le 200
□ Attendre [+] Jeton injecté dans com.apple.mobile.lockdown_cache-ActivationState
□ Attendre [+] mobileactivationd patché
□ Attendre [+] Setup.app -> Setup.app.bak
□ Attendre [+] uicache -a exécuté
□ Attendre le respring (ligne 47) puis 8 secondes
ÉTAPE 6 — Vérification

□ Attendre [+] État : Activated. Écran d'accueil attendu.
□ Vérifier sur l'écran du XR : écran d'accueil affiché, pas l'assistant d'activation
□ Vérifier le signal cellulaire : appels, SMS, données
□ Si état ≠ Activated → revenir à l'étape 2
ÉTAPE 7 — Règles de survie (après succès)

□ NE PAS réinitialiser le téléphone (efface le cache → verrouillage)
□ NE PAS flasher le firmware
□ NE PAS se connecter à iCloud depuis Réglages (re-validation serveur → verrouillage)
□ App Store / iTunes Store : OK avec un nouvel Apple ID
□ Panneau iCloud dans Réglages : interdit
□ Garder le téléphone allumé — l'état est tetheré à cette session de démarrage
RAPPEL DE TIMING

□ Entre le 200 du handshake et le lancement de l'étage 3 : 90 secondes maximum
□ Passé ce délai : nonce périmé → retour à l'étape 2
