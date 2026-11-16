# 6.0.0 - "Paranoia as a Service"
Release date: 2026-11-16

## Breaking changes
As 6.0 is a new major, some breaking changes were introduced:

- Packages are no longer being created for legacy Linux distributions.
  - Packages are built on 24.04; anything with a similar glibc version is compatible.
  - Note: this only applies to locally deployed scanners; remotely scanned systems are unaffected.
- Version 3 of the scan-output dataformat was introduced, which is not compatible with previous versions.
  - The server application retains the ability to load and display version 2 data, but any processing/search/advanced features will not work with the older data format.
- The `generic.Uptime` artefact is now a full model, instead of a naked float.
- `generic.PackageList` was removed, as it was replaced by `generic.PackageManagerInfo`.

No configuration changes are required, but any locally deployed scanners must
be updated to 6.0 to avoid errors.

## What's Changed

### General

- `generic.PackageList` is replaced by `generic.PackageManagerInfo`, which now also includes available updates, enabled repositories and last transaction info. (#174)
- Added `server.Docker`, which contains info about downloaded images, running containers and configured compose projects.
- `generic.IPTables`, containing all loaded rules and chains. Partial per-port information is also included for quick reference.
- Added dynamic `ScanOutput` versioning support:
  - Artefacts can now be created with `min_version` and `max_version` constraints.
  - Registries can now load multiple versions of the same artefact.
  - `ScanOutput` is now a base class, with a per-version subclass being generated for each (known) version.

## Server

### Advanced Search
Advanced search has been rewritten to be faster, more maintainable and more extensible. Several extra features have also been added.

New search features include:
- Added the `NOT` operator, which allows negating a search term.
- Added the `!=` comparator, which allows negating a search term.
- Added searching for `null` values
- Text search now uses regular expressions instead of simple substring-comparison.
- Added the `match` function, to allow searching through object-lists.
- Host alerts can now also be searched.

New output features include:
- Columns can now be given a 'friendly name' using the `<field> AS <friendly_name>` syntax.
- Search functions can now be used to process the output.
- Initial 'automatic' column output was added using the `show matches` toggle.

Fixes include:
- Operators (`AND`, `OR`, `CONTANS`, etc.) are now case-insensitive
- Using incorrect type values in search queries now returns an error.
- Resolved an issue in which incorrect return values were used when generating auto-complete suggestions.

### Other features

- Added an opt-in 'categorized' view for v2+ scan output (the host detail page), which splits up facts into multiple 'category' sections.
- Alerts can now be filtered on customer and os
- CLI 'queue scan' command now supports 'advanced search' queries to select which servers to scan
- Various UI elements have been had a readability and consistency pass.
- New OS's are automatically registered upon their first encounter.

### Fixes

- All users can now view acknowledged alerts for their servers (#178)

## Scanner

- Refactored multiple collectors to use `jc` as a common command-output parsing library.
- Added `version` command

**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/5.1.2...6.0.0

---

# 5.1.2 "Et tu, CB?"
Release date: 2026-11-06

## What's Changed

Updated dependecies and rebuild container images to pull in various security fixes in support libraries.


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/5.1.1...5.1.2

---

# 5.1.1 "Et tu, CB?"
Release date: 2026-10-13

## What's Changed

### Fixes
- Fixed a type error when calculating storage costs

**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/5.1.0...5.1.1

---

# 5.1.0 "Et tu, CB?"
Release date: 2026-10-13

## What's Changed

### New features
- Added new user role 'financial operator', as an intermediary between regular user and admin
  - This new role grants full read access to host data, and r/w access to all financial reporting
- Costs reporting now has a 'prognosis' feature, which allows users to predict future costs using the last known VM configuration as a basis.

### Fixes
- Corrected debian package filename to include arch as well\


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/5.0.1...5.1.0

---

# 5.0.1 "Sentient Spaghetti"
Release date: 2026-09-07

## What's Changed
* Worked around `lshw` being broken on Debian 10/11


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/5.0.0...5.0.1

---

# 5.0.0 "Sentient Spaghetti"
Release date: 2026-09-04

## What's Changed

### Breaking changes
- The configuration format for the server components has been rewritten
  - It now uses the same configuration format as the scanner component, supporting both ENV and TOML files
- The target Python version has been updated to 3.14; older versions are not supported
- Scanner now expect `lshw` to be installed on targets

### Humitifier Server
- Added background generation for cost reports, including rerun/delete actions
- Added support for costs reporting of non-vmware hosts
- Added support for running costs reports for hosts on multiple platforms at the same time
- Added more alert filtering options
- Clicking on alert-counts in the sidebar now directs you to a (pre-filtered) alert list
  - Previously, this send you to a pre-filtered host list
- Clicking on pie-chart-slices (on the dashboard) now directs you to a relevant list-page
- Data-cards on a host-detail-page no longer jump around when opening/closing them
- The web-UI has had a comprehensive UI pass
- Added dashboard stats filtering on customer and host-OS
- Added dynamic outdated operating-system management
  - Previously, outdated OS-s were hardcoded, now they are managed through the UI
- Moved datastore sync into a background task
- Fixed datetimes on table pages being in UTC
- Fixed asset tags not being set correctly on the first registration of a host


### Humitifier Scanner
- Added expanded hardware info scanning (via `lshw`), plus improved hardware visualization
- Added ILS Labs artefact group
- Added ILS Labs' PyInfra run-report collecting
- Refactored ping-code into a dedicated `Executor`
- Fixed an issue with closing SSH bastion connections

**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.14.2...5.0.0

---

# 4.14.2 ".. is not a monitoring solution, honest"
Release date: 2026-04-22

## What's Changed
### Humitifier Scanner
- Added more debug logging to local-shell-executor
- Fixed an issue where local-shell calls were executed in a tainted environment


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.14.1...4.14.2

---

# 4.14.1 ".. is not a monitoring solution, honest"
Release date: 2026-04-17

## What's Changed
### Fixes

- Fixed an issue in which generating alerts failed if no reverse-DNS entries could be resolved during scanning
- (Finally) fixed sidebar image being squished
- Fixed Webserver data being shown if no Webserver data was actually present


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.14.0...4.14.1

---

# 4.14.0 ".. is not a monitoring solution, honest"
Release date: 2026-03-17

## What's Changed

* feat: add Systemd info
* feat: added asset tag meta variable for hosts
* feat: added better output for scanner bulk-scan command
* fix: removed webdav field from gendoc artefact visualizer (it's almost always wrong and thus confusing)

**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.13.0...4.14.0

---

# 4.13.0 "Skynet Edition"
Release date: 2026-02-16

## What's Changed

### Humitifier scanner
- Added `total_memory_gb` to the `Hardware` fact

### Humitifier server
- Fixed sidebar image not being square
- Update advanced search to support:
  - OR selectors
  - nested/grouped selectors
  - Aggregations
  - (For integers) greater than/lesser than operators
  - Better autocomplete


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.12.0...4.13.0

---

# 4.12.0 "Clang, Rrr-tack-tack-tack, EEEEEEEEEEEEEEEEEEEEEEE"
Release date: 2026-01-26

## What's Changed

### Humitifier Scanner
- Added an option to the bulk-scan CLI command to combine the output of scans into a single JSON document

### Humitifier Server
#### Fixes
- Self-host wild-wasteland avatar, to avoid Wikipedia Ratelimitting
- Better attribution of wild-wasteland avatar

#### Features
- Added a new 'Advanced Search' feature for admins

* Feat/advanced search by @tymees in https://github.com/CentreForDigitalHumanities/humitifier/pull/152
* 4.12 by @tymees in https://github.com/CentreForDigitalHumanities/humitifier/pull/153


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.11.0...4.12.0

---

# 4.11.0 "Viviane"
Release date: 2026-01-14

## What's Changed
### Humitifier Server

#### Features
* Added a column and filter for virtualization tech to the hosts-overview page
* Debian 11 is now considered outdated

#### Updates
* Updated to Django 5.2
* Updated other dependencies

### Humitifier Scanner
#### Updates
* Updated dependencies


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.10.0...4.11.0

---

# 4.10.0 "What is Time? Baby don't hurt me"
Release date: 2025-11-10

## What's Changed
### Humitifier Server

### Features
* Changed cost reporting to support generating reports over periods of time, instead of a snapshot of the time of report
  * The costs overview page can still be used for a current snapshot overview

### Fixes
* Fixed a None reference error during costs calculations
* Fixed costs overview displaying archived servers by mistake
* Fix typo: aliasses -> aliases by @XanderVertegaal in https://github.com/CentreForDigitalHumanities/humitifier/pull/146

## New Contributors
* @XanderVertegaal made their first contribution in https://github.com/CentreForDigitalHumanities/humitifier/pull/146 Thanks!

**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.9.1...4.10.0

---

# 4.9.1 "setenforce 0"
Release date: 2025-09-08

## What's Changed
* Fixed an issue generating alerts when SELinux is disabled on a server

**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.9.0...4.9.1

---

# 4.9.0 "setenforce 0"
Release date: 2025-09-08

## What's Changed

- Added SELinux fact, collector, visualizer and alerting.


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.8.0...4.9.0

---

# 4.8.0 "I like trains"
Release date: 2025-08-25

## What's Changed
### Scanner
- Added bulk-scan command, that reads a hostlist file of to-scan hosts

### Server
- Removed acknowledged alerts from the 'stoplight' numbers (in the host-list), and added them as a separate counter
- Removed acknowledged alerts from the dashboard by default

**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.7.1...4.8.0

---

# 4.7.1 "Forgetful Foxifier"
Release date: 2025-08-04

## What's Changed
### Server
#### Fixes
- Solved a zero-division error in the memory artefact visualizer


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.7.0...4.7.1

---

# 4.7.0 "Forgetful Foxifier"
Release date: 2025-08-04

## What's Changed

### Server

#### Features
- Added new 'missing memory/swap' alert
- Dashboard: Fill up empty space with easter-eggs in easter-egg mode

#### Fixes
- Fix a zero-division error when a host has no swap
- Fixed the ultrawide breakpoint being set incorrectly

**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.6.3...4.7.0

---

# 4.6.3 "Have you tried turning it off?"
Release date: 2025-06-24

## What's Changed
* Fixed Redis/Valkey support


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.6.2...4.6.3

---

# 4.6.2 "Have you tried turning it off?"
Release date: 2025-06-24

## What's Changed
* Fixed the celery probe for the scanner container
* Updated celery to 5.5.3


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.6.1...4.6.2

---

# 4.6.1 "Have you tried turning it off?"
Release date: 2025-06-16

## What's Changed

### Scanner Fixes
- The SFTP executor now does not see missing files as a SSH connection problem
- The SFTP executor now retries using the new SFTP client, instead of retrying with the old closed client


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.6.0...4.6.1

---

# 4.6.0 "Have you tried turning it off?"
Release date: 2025-06-16

## What's Changed

### Scanner
- A new, more rebust, SSH reconnect method has been implemented

### Server
- Added package-version filtering support
  -  Syntax: `package-name==version` and `package-name~=substring_of_version`
- Added 'billable' and 'offline' states to hosts, available to be set through host-sync
- Several broken tests were fixed
- Much refactoring in the reporting module, to prepare for timebased  cost-reporting


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.5.4...4.6.0

---

# 4.5.4 "It can't be DNS!"
Release date: 2025-05-23

## What's Changed

### Fixes
- Various Sentry settings


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.5.3...4.5.4

---

# 4.5.3 "It can't be DNS!"
Release date: 2025-05-21

## What's Changed
* fix: add localhost check for host online validation by @tymees in https://github.com/CentreForDigitalHumanities/humitifier/pull/123


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.5.2...4.5.3

---

# 4.5.2 "It can't be DNS!"
Release date: 2025-05-21

## What's Changed

### Scanner

#### Fixes
- Wildcard vhosts will not be resolved by `DNSFactCollector` anymore
- Local-FQDN detection has been replaced with a robuster solution, with an optional override setting
- Various edge cases now create sensible errors


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.5.1...4.5.2

---

# 4.5.1 "It can't be DNS!"
Release date: 2025-05-14

## What's Changed

### Fixes
- Some layout issues due to the TW4 update
- Fixed the acknowledgment filter not working if set to 'no'
- Fixed the webserver fact collector breaking over permission issues
- Fixed the 'no alerts' dashboard stat to include hosts with only ack'd hosts
- Fixed storage alerts being unhelpfully worded
- Fixed memory alerts being trigger-happy

**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.5.0...4.5.1

---

# 4.5.0 "It can't be DNS!"
Release date: 2025-05-14

## What's Changed

## Common

### New artefacts
- `DNS`: a list of A, CNAME and PTR records for the host. Uses IP's from the network-interface artefact and hostnames from the webserver artefact to start searching.
- `Webserver`: a detailed overview of webserver configuration, including information for proxies, auth and rewrite-rules.

## Server

### New
- The 'Apache vhost' visualizer has been replaced by the new 'Webserver' visualizer (which uses the new `Webserver` artefact)
- Added a 'DNS' visualizer (which uses the new `DNS` artefact)
- Added new DNS alerts:
  - Warnings for missing PTR (reverse) entries
  - Warnings for FQDN's not found in DNS
  - Info messages for hostnames that do not resolve to the specific host.
- Updated to Tailwind 4
- Made Whitenoise an optional runtime component
- Reworked container entrypoints
  - Added bash to the container
  - Added common script to run-with-venv
  - Made DB migration optional
  - Made `collectstatic` step optional
  - Added script for celery readiness probes

### Fixes
- The package search works again
- Fixed `/api/upload_scan/` incorrectly rejecting scans from manual-scanned hosts.

## Scanner

### New
- Added two new fact collectors
  - `WebserverFactCollector` - retrieves and parses Webserver config. Currently only Apache and partial NGINX compatibility
  - `DNSFactCollector` - Resolves forward and reverse DNS entries for a host
- Added a new `LinuxFileExecutor`, which provides a file-API for collectors. (Instead of `cat`-ing everything).
  - This will automatically use SFTP or regular Python-API calls depending on the connection
  - Several fact collectors have been rewritten to use this new executor.
- Fact collectors can now specify a list of 'nice-to-have' facts, in addition to 'required' facts.
- The CLI can now retrieve and display scan-specs for other hosts
- Shell commands can now be passed as a list-of-arguments, for better
- Reworked container entrypoints
  - Added bash to the container
  - Added common script to run-with-venv
  - Added script for celery readiness probes
- The legacy linux-package now uses a pre-build base container, speeding up CI

### Fixes
- The obviously broken scan-ordering algorithm has been replaced by a proper algorithm
  - It is, genuinely, a miracle it held up as long as it did

**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.4.2...4.5.0

---

# 4.4.2 "Humitifier for Workgroups"
Release date: 2025-04-29

## What's Changed
* Fixed the version number being incorrect
* Fixed Sentry not being aware of the release


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.4.1...4.4.2

---

# 4.4.1 "Humitifier for Workgroups"
Release date: 2025-04-28

## What's Changed

### Fixes
- Fixed Excel sheet names being too long in some cases
- Fixed not selecting customers on the report page resulting in an empty report
- Renamed the 'filter' button to the 'apply' button


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.4.0...4.4.1

---

# 4.4.0 "Humitifier for Workgroups"
Release date: 2025-04-28

## What's Changed

### Server
- Simplified cost calculator to confirmed calculation method + added support costs
- Added excel export for server costs
- Fixed acknowledged alerts being counted in the statistics
- Fixed not being able to delete costs schemes
- Added alert filters:
  - A new exclude-alert-type filter, which can be used to **not** display a certain alert type
  - A new 'acknowledged filter', to see or hide acknowledged alerts

### General
- Refactored artefact-typing to automatically convert data into the correct artefact

**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.3.2...4.4.0

---

# 4.3.2 "Hello, I Like Money"
Release date: 2025-04-15

## What's Changed

### Server

#### Fixes
- The login page now highlights the OIDC login option over local login
- The alert statistics now filter out archived servers


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.3.1...4.3.2

---

# 4.3.1 "Hello, I Like Money"
Release date: 2025-04-14

## What's Changed

### Server

#### Fixes
- Minor formatting fixes regarding numbers
- Fixed disks > 1Tb being ignored
- Filter out non-vmware hosts in pricing overview


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.3.0...4.3.1

---

# 4.3.0 "Hello, I Like Money"
Release date: 2025-04-14

## What's Changed

### Server
- A new reporting section was added, including both a standalone cost calculator as well as a server cost overview page


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.2.0...4.3.0

---

# 4.2.0
Release date: 2025-03-27

## What's Changed

### Scanner

#### Features
- Standalone-mode is now fully supported, with support for pulling scan-specs and uploading results over the API
- CI now builds multiple binaries without any dependencies (except for glibc)


### Server

#### Bugfixes
- The dashboard now shows stats of active hosts, filtering out archived servers

**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.1.1...4.2.0

---

# 4.1.1
Release date: 2025-03-25

## What's Changed
- Revert a change in 4.1 in the `PuppetAgent` fact-collector that causes parse-errors


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.1.0...4.1.1

---

# 4.1.0
Release date: 2025-03-25

## What's Changed

### Features
- The `RebootPolicy` artefact is now available in the API, if available
- An 'OTAP stage' distribution chart is added to the dashboard
- An 'Altert type' breakdown chart is added to the dashboard

### Bugfixes
- The `is_wp` filter was not working due to not being updated to use the v2 scan-format
- The `PuppetAgent` artefact collector could clog up the scanner due to inefficient log-scanning
- The alert-severity shortcuts in the sidebar were not working
- The alert-severity filter on the hosts-list page was broken
- The 'disable'/'enable' user page was showing the wrong text in both cases

**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/4.0.1...4.1.0

---

# 4.0.1
Release date: 2025-03-24

## What's Changed

### Bugfixes
- Fixes an error during scanning hosts with offline memory
- Correctly render 'false' as a value for static-host-data
- Fixed 'has opentofu config' filter not appearing

---

# 4.0.0
Release date: 2025-03-24

## What's Changed

A  lot, so this is not going to be a comprehensive changelog

### Known issues
- The standalone scan mode is not fully supported yet, and is only used for local development at the moment

### Scanner
The Humitifier agent has been replaced by a new app, the Humitifier scanner. (Name changed to avoid confusion with server-workers). As such, a detailed changelog would be useless.

#### Architectural changes
- The scanner is now 'stateless' application, only receiving instructions from external sources
- Facts can now depend on other facts, which makes their data available during collecting fact data.
- Which data is collected is now dynamic, instead of hardcoded. What is collected is now determined by the server.
- The scanner can either be deployed 'standalone', or as a dedicated celery worker. The latter is used for scheduled scanning.
- Parallel scanning has been (mostly) discarded, a single instance will only ever scan one host at a time
   - Instead, parallelization is now accomplished by running the app as a Celery app. This will spawn 12 workers per instance.

#### New (arte)facts

- `Hardware`: details about CPU, Memory, block devices, PCI devices and USB devices
- `NetworkInterfaces`: details about the network stack on the machine
- `RebootPolicy`: the configured reboot policy on the server
- `PuppetAgent`: replaces `PuppetAgentStatus` and includes a lot more information about Puppet. Also, it now actually reports if the agent is enabled instead of always defaulting to 'true'
- `ZFS`: pool and volume usage info.

### Server

#### New features
- Added a new 'export hostnames only' option to export page
- Various fields are now 'host metadata', and will no longer be retrieved from scans:
  - Customer (department in 3.0)
  - Department (new semantics in 4.0)
  - Contact
  - Has tofu configuration (new in 4.0)
  - OTAP stage (new in 4.0)
- Host management
  - Previously, the server only displayed data given to it. Now, the server is responsible for managing the inventory of servers.
  - It also decides what is scanned, when.
  - External apps can now sync hosts over the API, negating the need to have your CI pipeline write into the DB
- Background tasks using Celery
  - Includes managing Celery's 'Beat' scheduler and basic cluster-observation
- Rewritten subsystems: scan visualization, alert generations, cleanup code

#### Bugfixes
- The pagination buttons are now actually _there_

#### New alerts
- Host offline warnings; critical if the host if offline
- Uptime warnings; info at 3 months, warning at 6 and critical at 1 year
- Memory/swap usage warnings; info at (70,30), warning at (80,40) and critical at (90,70)
- Disk usage warnings: warning at 80% usage, critical at 90%
- ZFS usage warnings: same thresholds as disk-usage
- Hardware config warnings: critical if the VM has offline-memory

#### Requested minor changes
- The solis-login button is now the first button on the login screen
- Certain buttons/pills are differently aligned, Саша.
- Removed the dash from Humanities IT



**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/3.3.1...4.0.0

---

# Version 3.3.1
Release date: 2024-11-21

## What's Changed
* CI: proper image tagging and better scanning by @tymees in https://github.com/CentreForDigitalHumanities/humitifier/pull/80
* Version 3.3.1 by @tymees in https://github.com/CentreForDigitalHumanities/humitifier/pull/82


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/3.3.0...3.3.1

---

# Version 3.3
Release date: 2024-11-19

## What's Changed
### New server features
- Various host-filters have been changed to a 'multiselect', which then acts as an 'or' filter. (E.g. you can select all Debian 11 and 12 machines at the same time now).
  - `os`, `department` and `contact`
- Added new 'last scan date' sorting option to the hosts page
- The search bar in the header now takes up the entire width available

### Server fixes
- 'Default homepage' user-setting is now actually used
- Possible filter values are now sorted alphabetically
- Select elements now have their 'dropdown arrow' properly aligned
- Various dropdown elements now properly autoclose
- The 'is wordpress' filter now actually works (Thanks @73616e646572 for reporting)
- The 'OS'  column has been renamed to 'Operating System' to be consistent with the rest of the UI (Thanks @73616e646572 for reporting)


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/3.2.0...3.3.0

---

# Version 3.2
Release date: 2024-11-12

## What's Changed

### New server features
- Users, access control and OIDC support
- A Favicon!
- Easy table page framework (reduces amount of duplicated html by a lot)
- OAuth support for API
- New 'hosts' API endpoint
- 'Export hosts' page

### Server fixes
- Small performance fixes
- Network scanner protections for Sentry

### Agent fixes
- Updated the agent to authenticate using OAuth


**Full Changelog**: https://github.com/CentreForDigitalHumanities/humitifier/compare/3.1.2...3.2.0

---

# Version 3.1.2
Release date: 2024-11-01



---

# Version 3.1.1
Release date: 2024-10-31

Fixed a problem in which I forgot to commit a file

---

# Version 3.1
Release date: 2024-10-31

Added server archivation

---

# Version 3.0
Release date: 2024-10-30



---

# Cleaning update
Release date: 2024-10-18



---

# v2.1.0  QoL updates
Release date: 2024-04-11

- dynamic reload of hosts (`.toml` file gets reloaded on every task run)
- pre-render of index page (the initial page load should be significantly faster now)
- multi-stage build of docker image (the image size is roughly half the size now on account of using `slim`; `alpine` seems to not be functional due to some `asyncpg` dependencies)
- `poetry.lock` is now tracked for more consistent builds

---

# v2.0.0.0 Now with postgres
Release date: 2024-03-08

- Database backend switched to postgres for more better functionalities (e.g. db functions)
- SSH client issues fact collection commands individually to make it easier to debug failures (this is slower, but easier to understand)
- Codebase is simplified thanks to not having to jump through hoops of parsing a huge fact collection at once
- Added improved logging of failure of fact parsing
- Templating moved to jinja-based components
- Hosts are now synced to the database from a list of strings
- Dockerfile is optimized for build time

---

# v1.0.0 - initial release
Release date: 2023-11-07
