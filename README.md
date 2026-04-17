# Ecocito — Home Assistant Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![HACS][hacs-shield]][hacs]

Intégration Home Assistant pour le service français de collecte des déchets [Ecocito](https://www.ecocito.com/).

Connectez votre compte Ecocito à Home Assistant pour suivre automatiquement tous vos types de collecte :
- 🗑️ **Ordures ménagères** (nombre, poids total, dernière collecte)
- ♻️ **Recyclage** (nombre, poids total, dernière collecte)
- 🌿 **Déchets verts** (nombre, poids total, dernière collecte)
- 🚗 **Visites en déchetterie** (nombre de visites)
- Et tout autre type de collecte exposé par votre collectivité — **découverts automatiquement**

Les données couvrent l'année en cours et les années précédentes (configurable).  
Si votre compte possède plusieurs adresses, un appareil distinct est créé par adresse.

---

## Prérequis

- Home Assistant ≥ 2024.6.0
- Un compte Ecocito actif ([ecocito.com](https://www.ecocito.com/))
- Votre **domaine Ecocito** (ex. `69.ecocito.com` → entrez `69.ecocito.com` ou simplement `69`)

---

## Installation

### Via HACS (recommandé)

[![Ouvrir dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rclsilver&repository=home-assistant-ecocito&category=integration)

1. Cliquez sur le bouton ci-dessus
2. Installez l'intégration depuis HACS
3. Redémarrez Home Assistant

### Installation manuelle

1. Ouvrez le dossier de configuration de votre HA (où se trouve `configuration.yaml`)
2. Créez le dossier `custom_components` s'il n'existe pas
3. Créez le sous-dossier `custom_components/ecocito`
4. Téléchargez tous les fichiers de `custom_components/ecocito/` depuis ce dépôt
5. Copiez-les dans le dossier créé
6. Redémarrez Home Assistant

---

## Configuration

1. Dans HA, allez dans **Paramètres → Intégrations**
2. Cliquez sur **Ajouter une intégration** et recherchez **Ecocito**
3. Renseignez :
   - **Domaine Ecocito** : votre domaine (ex. `69.ecocito.com`)
   - **Identifiant** : votre email ou identifiant Ecocito
   - **Mot de passe** : votre mot de passe Ecocito

### Options (après configuration)

Via **Paramètres → Intégrations → Ecocito → Configurer** :

| Option | Défaut | Description |
|--------|--------|-------------|
| **Années d'historique** | 2 | Nombre d'années précédentes à afficher (0–5) |

---

## Entités créées

> Les types de collecte sont **découverts automatiquement** depuis votre espace Ecocito.  
> Un capteur est créé pour chaque type exposé par votre collectivité — aucune configuration manuelle n'est nécessaire.  
> Si de nouveaux types apparaissent, l'intégration se recharge automatiquement pour les inclure.

Pour chaque type de collecte et chaque adresse de votre compte, les capteurs suivants sont créés.

### Année en cours

| Entité | Unité | Description |
|--------|-------|-------------|
| Nombre de collectes `<type>` | — | Nombre total de collectes |
| Poids total collecté `<type>` | kg | Poids cumulé |
| Poids de la dernière collecte `<type>` | kg | Poids lors de la dernière collecte |
| Nombre de visites en déchetterie | — | Nombre de visites effectuées |

### Années précédentes _(suffixées `(N-n)`, selon la configuration)_

| Entité | Unité |
|--------|-------|
| Nombre de collectes `<type>` (N-n) | — |
| Poids total collecté `<type>` (N-n) | kg |
| Nombre de visites en déchetterie (N-n) | — |

### IDs d'entités

Les IDs sont toujours générés en **anglais**, quelle que soit la langue de votre instance HA.  
Les libellés affichés sont dans la langue de votre instance.

---

## Exemples d'automatisations

### Notification lors d'une nouvelle collecte

```yaml
automation:
  - alias: "Notification collecte d'ordures"
    trigger:
      - platform: state
        entity_id: sensor.ecocito_number_of_garbage_collections
    action:
      - service: notify.mobile_app
        data:
          message: >
            Nouvelle collecte enregistrée !
            Total cette année : {{ states('sensor.ecocito_number_of_garbage_collections') }} collectes
            pour {{ states('sensor.ecocito_total_weight_of_collected_garbage') }} kg.
```

### Affichage dans un dashboard Lovelace

```yaml
type: entities
title: Ecocito — Déchets
entities:
  - entity: sensor.ecocito_number_of_garbage_collections
  - entity: sensor.ecocito_total_weight_of_collected_garbage
  - entity: sensor.ecocito_weight_of_the_latest_garbage_collection
  - entity: sensor.ecocito_number_of_recycling_collections
  - entity: sensor.ecocito_total_weight_of_collected_recycling
  - entity: sensor.ecocito_number_of_visits_to_waste_deposit
```

---

## Dépannage

### Les capteurs affichent "Indisponible"

- Vérifiez que votre identifiant et mot de passe sont corrects
- Vérifiez que votre domaine Ecocito est correct (ex. `69.ecocito.com`)
- Consultez les logs HA : **Paramètres → Système → Journaux** et cherchez `ecocito`

### Les données ne se mettent pas à jour

- Les données sont rafraîchies toutes les **5 minutes**
- En cas d'erreur réseau, l'intégration réessaie jusqu'à 3 fois automatiquement
- Si la session expire, une ré-authentification automatique est tentée

### Un nouveau type de collecte n'apparaît pas

- Les types sont vérifiés **toutes les heures**
- Si un nouveau type est détecté, l'intégration se recharge automatiquement
- Vous pouvez forcer la prise en compte via **Paramètres → Intégrations → Ecocito → (⋮) → Recharger**

### Plusieurs adresses mais un seul appareil visible

- L'intégration détecte les adresses depuis les données de collecte
- Si vous avez récemment ajouté une adresse, attendez la prochaine mise à jour ou rechargez l'intégration

### Reconfigurer les identifiants

**Paramètres → Intégrations → Ecocito → (⋮) → Reconfigurer**

---

## Contribution

Les contributions sont les bienvenues ! Consultez le [guide de contribution](CONTRIBUTING.md).

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/rclsilver/home-assistant-ecocito.svg?style=for-the-badge
[commits]: https://github.com/rclsilver/home-assistant-ecocito/commits/master
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://hacs.xyz/
[license-shield]: https://img.shields.io/github/license/rclsilver/home-assistant-ecocito.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/rclsilver/home-assistant-ecocito.svg?style=for-the-badge
[releases]: https://github.com/rclsilver/home-assistant-ecocito/releases

---

## Prérequis

- Home Assistant ≥ 2024.6.0
- Un compte Ecocito actif ([ecocito.com](https://www.ecocito.com/))
- Votre **domaine Ecocito** (ex. `69.ecocito.com` → entrez `69.ecocito.com` ou simplement `69`)

---

## Installation

### Via HACS (recommandé)

[![Ouvrir dans HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rclsilver&repository=home-assistant-ecocito&category=integration)

1. Cliquez sur le bouton ci-dessus
2. Installez l'intégration depuis HACS
3. Redémarrez Home Assistant

### Installation manuelle

1. Ouvrez le dossier de configuration de votre HA (où se trouve `configuration.yaml`)
2. Créez le dossier `custom_components` s'il n'existe pas
3. Créez le sous-dossier `custom_components/ecocito`
4. Téléchargez tous les fichiers de `custom_components/ecocito/` depuis ce dépôt
5. Copiez-les dans le dossier créé
6. Redémarrez Home Assistant

---

## Configuration

1. Dans HA, allez dans **Paramètres → Intégrations**
2. Cliquez sur **Ajouter une intégration** et recherchez **Ecocito**
3. Renseignez :
   - **Domaine Ecocito** : votre domaine (ex. `69.ecocito.com`)
   - **Identifiant** : votre email ou identifiant Ecocito
   - **Mot de passe** : votre mot de passe Ecocito

### Options (après configuration)

Via **Paramètres → Intégrations → Ecocito → Configurer** :

| Option | Défaut | Description |
|--------|--------|-------------|
| **Années d'historique** | 2 | Nombre d'années précédentes à afficher (0–5) |

---

## Entités créées

> Pour chaque adresse de votre compte, un **appareil** distinct est créé avec les capteurs suivants.

### Année en cours

| Entité | Unité | Description |
|--------|-------|-------------|
| Nombre de collectes d'ordures | — | Nombre total de collectes d'ordures ménagères |
| Poids total des ordures collectées | kg | Poids cumulé des ordures collectées |
| Poids de la dernière collecte d'ordures | kg | Poids lors de la dernière collecte |
| Nombre de collectes de recyclage | — | Nombre total de collectes de recyclage |
| Poids total du recyclage collecté | kg | Poids cumulé du recyclage collecté |
| Poids de la dernière collecte de recyclage | kg | Poids lors de la dernière collecte |
| Nombre de visites en déchetterie | — | Nombre de visites effectuées |

### Années précédentes _(une par année selon la configuration, suffixées `(N-n)` : `N-1`, `N-2`, etc.)_

| Entité | Unité |
|--------|-------|
| Nombre de collectes d'ordures (N-n) | — |
| Poids total des ordures collectées (N-n) | kg |
| Nombre de collectes de recyclage (N-n) | — |
| Poids total du recyclage collecté (N-n) | kg |
| Nombre de visites en déchetterie (N-n) | — |

---

## Exemples d'automatisations

### Notification lors d'une nouvelle collecte

```yaml
automation:
  - alias: "Notification collecte d'ordures"
    trigger:
      - platform: state
        entity_id: sensor.ecocito_nombre_de_collectes_d_ordures
    action:
      - service: notify.mobile_app
        data:
          message: >
            Nouvelle collecte enregistrée !
            Total cette année : {{ states('sensor.ecocito_nombre_de_collectes_d_ordures') }} collectes
            pour {{ states('sensor.ecocito_poids_total_des_ordures_collectees') }} kg.
```

### Affichage dans un dashboard Lovelace

```yaml
type: entities
title: Ecocito — Déchets
entities:
  - entity: sensor.ecocito_nombre_de_collectes_d_ordures
  - entity: sensor.ecocito_poids_total_des_ordures_collectees
  - entity: sensor.ecocito_poids_de_la_derniere_collecte_d_ordures
  - entity: sensor.ecocito_nombre_de_collectes_de_recyclage
  - entity: sensor.ecocito_poids_total_du_recyclage_collecte
  - entity: sensor.ecocito_nombre_de_visites_en_decheterie
```

---

## Dépannage

### Les capteurs affichent "Indisponible"

- Vérifiez que votre identifiant et mot de passe sont corrects
- Vérifiez que votre domaine Ecocito est correct (ex. `69.ecocito.com`)
- Consultez les logs HA : **Paramètres → Système → Journaux** et cherchez `ecocito`

### Les données ne se mettent pas à jour

- Les données sont rafraîchies toutes les **5 minutes**
- En cas d'erreur réseau, l'intégration réessaie jusqu'à 3 fois automatiquement
- Si la session expire, une ré-authentification automatique est tentée

### Plusieurs adresses mais une seule entité visible

- L'intégration détecte les adresses depuis les données de collecte
- Si vous avez récemment ajouté une adresse, attendez la prochaine mise à jour ou redémarrez HA

### Reconfigurer les identifiants

**Paramètres → Intégrations → Ecocito → (⋮) → Reconfigurer**

---

## Contribution

Les contributions sont les bienvenues ! Consultez le [guide de contribution](CONTRIBUTING.md).

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/rclsilver/home-assistant-ecocito.svg?style=for-the-badge
[commits]: https://github.com/rclsilver/home-assistant-ecocito/commits/master
[hacs-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[hacs]: https://hacs.xyz/
[license-shield]: https://img.shields.io/github/license/rclsilver/home-assistant-ecocito.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/rclsilver/home-assistant-ecocito.svg?style=for-the-badge
[releases]: https://github.com/rclsilver/home-assistant-ecocito/releases
