Download the MobilityData GTFS Validator CLI JAR before running validator baselines:

```bash
mkdir -p vendor
curl -fsSL -o vendor/gtfs-validator-6.0.0-cli.jar \
  https://github.com/MobilityData/gtfs-validator/releases/download/v6.0.0/gtfs-validator-6.0.0-cli.jar
```

The bridge also accepts `gtfs-validator-6.0.0-all.jar` if you build it locally.

Expected SHA-256 for the release CLI JAR:
`4f78d08a0b72a9ad1833a7cd979f701d1590590ff73f4224fb960dc8cc4014fd`.
The regeneration command rejects a missing JAR or digest mismatch. The binary
is a setup dependency and is not part of the retained transit-data snapshots.
Source: https://github.com/MobilityData/gtfs-validator/releases/tag/v6.0.0
Licence: https://github.com/MobilityData/gtfs-validator/blob/v6.0.0/LICENSE
