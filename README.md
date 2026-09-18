# WGDashboard Monitor pour Home Assistant

Intégration custom pour suivre l'état de vos peers WireGuard via [WGDashboard](https://github.com/donaldzou/WGDashboard) : qui est connecté, dernier handshake, volume de données échangées.

## Fonctionnalités

- 1 `binary_sensor` par peer : connecté / déconnecté (basé sur la fraîcheur du dernier handshake)
- 1 `sensor` "dernier handshake" par peer (horodatage)
- 2 `sensor` de volume de données par peer (reçu / envoyé)
- 1 `sensor` global "peers connectés / total"
- Configuration 100% via l'UI (pas de YAML requis)

## Installation via HACS (dépôt personnalisé)

1. HACS → menu ⋮ → **Dépôts personnalisés**
2. URL : `https://github.com/<votre-user>/wgdashboard_monitor`, catégorie **Intégration**
3. Installer "WGDashboard Monitor", puis redémarrer Home Assistant

## Configuration

1. Sur votre WGDashboard : **Settings** → tout en bas → activer **API Key** → **Create**
2. Dans Home Assistant : **Paramètres → Appareils et services → Ajouter une intégration** → *WGDashboard Monitor*
3. Renseigner :
   - **Host URL** : ex. `http://192.168.1.14:10086`
   - **API key** : la clé créée à l'étape 1
   - **Config name** : le nom de votre configuration WireGuard (généralement `wg0`)

## Gérer un serveur WireGuard de secours

Ajoutez l'intégration une seconde fois avec l'IP de votre LXC de secours. Vous obtiendrez deux jeux d'entités distincts (un par appareil), que vous pouvez combiner dans une automatisation pour être alerté si le principal tombe.

## ⚠️ Note sur le format de l'API

La documentation publique de WGDashboard est encore incomplète et le format JSON exact peut légèrement varier selon la version (3.x / 4.x). Le parsing dans `coordinator.py` essaie plusieurs noms de champs connus. Si vos entités remontent des valeurs vides, activez le mode debug (`custom_components.wgdashboard_monitor: debug` dans `logger:`) pour voir la réponse brute de l'API et ajuster `_normalize_peer()` en conséquence.

## Ping et traceroute par device

Cette intégration ne fait pas de ping/traceroute elle-même (WGDashboard n'expose pas ça par API). Combinez-la avec l'intégration native **Ping (ICMP)** de Home Assistant sur les IP de vos peers pour avoir la latence en direct.
