# Retained evaluation inputs

The byte-identical evaluated inputs are retained at `sha256/<digest>.zip`. Each adjacent JSON records its publisher URL, dataset metadata URL, licence URL/version, exact acknowledgement, byte count, digest, and acquisition-date status. Digest and size are verified before use. The acquisition date is a historical repository record; exact timestamps are unavailable. These local copies do not establish an independent archive timestamp or an externally published accession. [Frozen manifest](../../docs/bounds_eval/frozen_feed_manifests.json), [fetch implementation](https://github.com/transitxlabs/transit-access-audit/blob/main/scripts/fetch_gtfs.py).

The files in this folder are the exact evaluated inputs. Regeneration copies them to the ignored working cache and checks them. A later publisher update does not change the evaluation input. `--force` downloads a fresh copy from the publisher. If the download or the check fails, the previous input is kept.

| Input | Publisher source | Licence | Acknowledgement |
|---|---|---|---|
| Calgary | [Dataset npk7-z3bj](https://data.calgary.ca/api/views/npk7-z3bj.json) | [Open Government Licence, City of Calgary, v2.1](https://data.calgary.ca/stories/s/u45n-7awa/) | Contains information licensed under the Open Government Licence – City of Calgary. |
| Edmonton | [Dataset 4fvt-p2se](https://data.edmonton.ca/api/views/4fvt-p2se.json) | [Open Government Licence, Edmonton, v1.0, July 2022](https://data.edmonton.ca/stories/s/Open-Government-Licence-Edmonton/msh8-if28/) | Contains information licensed under the Open Government Licence – City of Edmonton. |
| TTC | [Merged schedules dataset](https://open.toronto.ca/dataset/merged-gtfs-ttc-routes-and-schedules/) | [Open Government Licence, Toronto](https://open.toronto.ca/open-data-licence/) | Contains information licensed under the Open Government Licence – Toronto. |

The cited licences allow redistribution with acknowledgement and do not imply endorsement. The Toronto, Calgary and Edmonton licence pages were read on 2026-10-12.
