This is the plain-text data for the unreleased City of Heroes Issue 24. This
repo is intended as a baseline starting point with the data necessary to run
and modify City of Heroes. Large binary files such as textures, meshes, and
sounds aren't included, but a script is provided to download and extract it.

# Setup

The *developer* builds of the City of Heroes DbServer, Mapserver, Game client, and Pig
archive manager can be compiled from the source code [monorepo][monorepo]. A
script downloads the matching executables and DLLs, and another fetches the
other publicly available game assets such as textures, meshes, and audio.

**NOTE:** This guide is for beginners. If some steps seem silly to you, then
you know better.

1. Execute [fetch_release.ps1](tools/fetch_release.ps1)
2. Execute [fetch_data.ps1](tools/fetch_data.ps1)
3. Execute [templates.ps1](tools/templates.ps1)

[monorepo]: https://github.com/Thunderspies/CityOfHeroes

# Dependencies

The scripts fetch most dependencies. Runtime dependencies that must be
installed separately include:

## SQL Server

https://www.microsoft.com/en-us/sql-server/sql-server-downloads

The character database is stored in SQL Server. Any version of SQL Server seems
to work. LocalDB is a lighter version of SQL Server that is recommended for
local testing and private use. Instructions to install and administrate SQL
Server is outside the scope of this guide.

* From the provided link, download the free SQL Server Express installer
* During installation, choose "Custom"
* Click through the default install wizard options until prompted for features
* On the features page, uncheck everything and then choose "LocalDB"
* Continue with defaults until installation is complete

NOTE: If you're prompted for something about "Azure", just disable that too

## ODBC17

https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-ver17

The ODBC driver is used by the game server to interface with the SQL Server.
It's basically the bridge between the game and the database. [ODBC 17
x86](https://go.microsoft.com/fwlink/?linkid=2361647) is the only driver that's
supported. Just download and run the installer.

# Usage

To run a server and client locally, run
[start-local.ps1](tools/start-local.ps1). This assumes the dbserver is
configured to run with "fakeauth" in [servers.cfg](data/server/db/servers.cfg).
In fakeauth mode, any username and password may be used to log into the shard.
With a mapserver running in local mode, characters will always zone into that
mapserver when they're created or log in.

## Database Templates and Schema

The DbServer manages its own SQL database for character and supergroup data.
However, the schema depends on data that is not processed by the DbServer.
Since the MapServer loads and processes all of the data necessary to generate
the database schema, it must first be run with `MapServer -templates` to create
teplate files that are then used by DbServer to create or revise the character
databse in SQL. This step must be repeated whenever data is changed or the way
that the MapServer loads or processes data changes. The `templates.ps1` script
can be explicity called to simplift this step, but it's also implicitly called
by `start-local.ps1` before the DbServer starts.

## Creating Data Bins

The plain-text data is parsed into binary files that resembles memory dumps.
These are intended to cache parsed and post-processed data for faster start-up.
Release clients require the bin files since they can't parse the data in
plain-text format.

All of the bins can be found in the following locations:
* `data/bin`
* `data/server/bin`
* `data/geobin`

Only the server requires the bins in `data/server/bin` in addition to the other
bins.

Although bins are a biproduct of the developer mapserver and client running
normally, they can also be created explicitly with the `-createbins` run
argument to both client and server. The
[create-bins.ps1](tools/create-bins.ps1) script simplifies this.

# Contributing

As a baseline and archive of CoH's I24 data, this repo is not accepting
contributions. It's recommended that forks of this repo always commit files
with lowercase names to avoid collisions in case-agnostic filesystems.
