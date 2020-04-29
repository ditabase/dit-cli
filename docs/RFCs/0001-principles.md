## Summary

This RFC lists the guiding principles of dit. What is dit trying to do, and what it
isn't. How dit will try to solve problems, and how it won't.

## Mission

Make the file type people will use in 200 years. Dit should be the single way to
describe anything.

## Principles

1. **Unite Everything** - If dit can't work with something, that's a bug.
2. **Connect, Not Replace** - Leverage existing tech, don't rebuild it.
3. **Simple** - Leave most things to scripts.
4. **Not a Language** - No `ifs`, `loops`, `threads`, file system commands: unnecessary.
5. **Powerful** - Features must do a lot, even if it makes them complex.
6. **Generic** - If it works one way, it should work every conceivable way.
7. **Just a File** - Email a dit to a random stranger, and it should work.

## Definitions

### All Data/Everything

These terms are regularly used throughout this project, but without specific
description. An attempt at an exhaustive list follows. Everything in this list
represents a possible option for how data might exist today. Dit must work with every
possible combination. As in principle #1, if dit doesn't work with some combination,
that's a bug.

1. Platform
   - Hardware: Datacenter, Server, desktop, mobile, embedded, etc.
   - Architecture: x86, ARM, 6502, ASIC, etc.
   - OS: Linux, Windows, Mac, ChromeOS, etc.
2. Container
   - Text: JSON, XML, CSV, YAML, TOML, INI,

### Work With -

Dit can 'work with' a technology combination when a developer has access to all
fundamental dit features.
