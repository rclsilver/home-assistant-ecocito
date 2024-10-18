# Integration Blueprint

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

Integration to connect with the French waste collection service [Ecocito](https://www.ecocito.com/).

## Install with HACS

[![Install with HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=rclsilver&repository=home-assistant-ecocito&category=integration)

More information about HACS [here](https://hacs.xyz/).

## Manual installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `ecocito`.
1. Download _all_ the files from the `custom_components/ecocito/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Ecocito"

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/rclsilver/home-assistant-ecocito.svg?style=for-the-badge
[commits]: https://github.com/rclsilver/home-assistant-ecocito/commits/master
[exampleimg]: example.png
[license-shield]: https://img.shields.io/github/license/rclsilver/home-assistant-ecocito.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/rclsilver/home-assistant-ecocito.svg?style=for-the-badge
[releases]: https://github.com/rclsilver/home-assistant-ecocito/releases
