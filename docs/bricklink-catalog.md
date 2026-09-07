# The BrickLink catalog

BrickTracker takes its catalog data — sets, parts, minifigures, colours,
categories and every inventory — from a single archive of the official
BrickLink catalog exports.

There is no API key to obtain, no account to register and no rate limit to
respect. Importing a set reads a local file rather than making network calls,
which is also why it takes seconds rather than minutes.

## Downloading it

**The catalog is not downloaded automatically.** Nothing fetches it on
startup and nothing refreshes it on a schedule.

On a fresh installation you have to fetch it once:

> **Admin → Themes (BrickLink catalog) → Download the latest catalog**

Until you do, the interface works but adding anything fails with
*"The BrickLink catalog has not been downloaded yet"*.

The download is around 39 MB.

## Keeping it current

The same button updates it later. Nothing does this for you, so a catalog
stays at whatever date you last pressed it.

That matters less than it sounds: the catalog only changes when BrickLink
adds or corrects items, so an old copy simply will not know about recent
sets. Refresh it when a set you own is missing.

The upstream archive is rebuilt every hour, so you always get something
current when you do press it.

## Where it comes from

By default the latest release of
[brickstore-database](https://github.com/rgriebl/brickstore-database), a
project that regenerates the BrickStore database from the official BrickLink
exports and publishes the result.

That is one person's repository, so the source is configurable:

| Setting | Meaning |
|---|---|
| `BK_BRICKLINK_CATALOG_URL` | Download this address directly. Setting it skips the release lookup entirely |
| `BK_BRICKLINK_CATALOG_RELEASE_URL` | Where to look for the newest release |
| `BK_BRICKLINK_CATALOG_ASSET` | Which file of that release to take |
| `BK_BRICKLINK_CATALOG_PATH` | Where the archive is stored locally |

## What it contains

```
colors.xml  categories.xml  itemtypes.xml
items/{P,S,M,...}.xml          reference data per item type
S/*.xml  M/*.xml  P/*.xml      inventories of sets, minifigures, assemblies
```

Inventories are read one at a time straight out of the archive, so unpacking
it is neither needed nor wanted: it holds some 53000 files.

## Notes

Minifigures use BrickLink numbering (`sw1029`, `oct054`), not Rebrickable's
`fig-######`.

Parts that come with a sticker applied are catalogued by BrickLink as items
of their own and appear in the inventory flagged as counterparts. A
counterpart is a view of a part that is already counted, not an extra piece,
so its quantity is not added to the total.

Images are not part of the archive. They are fetched from BrickLink as
needed, which is the one place the application still touches the network
during an import.
