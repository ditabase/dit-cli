## Summary

This RFC lists the guiding principles of dit. What is dit trying to do, and what it
isn't. How dit will try to solve problems, and how it won't. These principles are
further clarified by definitions.

## Principles

1. **Unite Everything** - If dit can't work with something, that's a bug.
2. **Simple** - Leave almost all features to scripts.
3. **Generic** - If it works one way, it should work every conceivable way.
4. **Not a Language** - No `ifs`, `loops`, `threads`, `fs.read()`.
5. **Just a File** - Email a dit to a random stranger, and it should work.
6. **Connect, Not Replace** - Leverage existing tech, don't rebuild it.
7. **Reference is Fine** - Keep your architecture, convert to dit when necessary.
8. **Speed Doesn't Matter** - Performance is fickle. Compatibility is forever.
9. **Shortcuts are Fine** - If dit is slow, go around it with something faster.
10. **The Long Tail** - Data is always much more complex than you think.

## Definitions

### All Data/Everything

What is really meant by "all data"? The long tail of data entropy is very, very long.
This list is an attempt to show some of that long tail, and inspire understanding of the
scope of the problem. The true list is probably infinite and the relationships much more
complex. Per #1, dit must work with all of these.

1. Hardware/Platform
   - Datacenter, Server, Desktop, Mobile, Embedded, IoT, etc.
   - Paper Documents<sup id="paper-documents">[1](#footnote-1)</sup>, DNA, Neural
     Implants, etc.
   - USB Flash Drive, SD card, Memory Stick, etc.
   - EMV chip, magnetic strip, SIM card,
     [EAS](https://en.wikipedia.org/wiki/Electronic_article_surveillance), RFID,
     Barcode, QR code, etc.
2. Architecture
   - x86, ARM, RISC-V, GPU, ASIC, etc.
   - Neural Nets, Human/Mechanical Turk, Analog, Quantum, Biological etc.
3. Operating System
   - Linux, Windows, MacOS, iOS, Android, ChromeOS, Embedded, None, etc.
4. File System
   - NTFS, ext4, APFS, etc.
   - FAT32, exFAT, ext1-3, HFS, etc.
   - ZFS, Btrfs, XFS, GlutterFS, etc.
5. Database
   - Often, none.
   - temp [Test][the link]
6. [Container](https://en.wikipedia.org/wiki/List_of_file_formats)<sup id="container">[2](#footnote-2)</sup>
   - [General Purpose Data Formats](https://en.wikipedia.org/wiki/Comparison_of_data-serialization_formats)
     - Serialization
       - CSV, Delimited by Comma, Tab, Space, Custom, Newline terminated/custom, etc.
       - JSON, [JSON5](https://json5.org/), [HJSON](https://hjson.github.io/),
         [Jsonnet](https://jsonnet.org/), [CSON](https://github.com/bevry/cson), a
         different [CSON](http://noe.mearie.org/cson/),
         [jsonc](https://code.visualstudio.com/docs/languages/json#_json-with-comments),
         [ndjson](http://ndjson.org/), etc.
       - XML, XAML, XHTML, XBRL, XLink, XPath, many many semantic web formats, etc.
       - INI, TOML, YAML, [StrictYAML](https://github.com/crdoconnor/strictyaml),
         [YAMLEX](https://docs.saltstack.com/en/latest/ref/serializers/all/salt.serializers.yamlex.html),
         [HOCO](https://github.com/lightbend/config/blob/master/HOCON.md),
         [HCL](https://github.com/hashicorp/hcl), [Dhall](https://dhall-lang.org/),
         [CUE](https://cuelang.org/), etc.
     - Serialization + Binary
       - JSON: BSON, jsonb, Smile, CBOR, UBJSON, etc.
       - XML: EXI, Fast Infoset, etc.
       - MessagePack, Binn, Bencode, etc.
     - Serialization + Schema
       - JSON-Schema, JSON-LD, etc.
       - XML-Schema: XSD, DTD, RELAX NG, METS, etc.
     - Full
       [Interface Description Language](https://en.wikipedia.org/wiki/Interface_description_language)
       - Protocol Buffers, Apache Thrift, Apache Avro, SOAP, ASN.1, Amazon Ion, etc.
   - Domain Specific formats
     - Healthcare [FHIR](https://www.hl7.org/fhir/overview.html), Ethereum
       [RLP](https://github.com/ethereum/wiki/wiki/RLP), Data Science
       [HDF5](https://www.hdfgroup.org/solutions/hdf5/), etc.
   - Markup Languages
     - temp
   - Media Formats
7. Encoding, Sub/Super-container
   - Binary, ASCII, UTF-8, UTF-16, etc.
   - Base64, Base4, DNA,
8. Content
   - temp
   - [Identification Code/Number](https://en.wikipedia.org/wiki/Category:Identifiers)

### Compatible -

Dit is compatible with a technology combination when a developer has access to all
fundamental dit features.

test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test test

test

- <a name="footnote-1">[1:](#paper-documents)</a> It would seem that paper documents
  (and perhaps MTurk, Quantum) have little to do with data formats, so why does dit need
  to worry about them? Suppose you fill out a paper form at a doctor's office. That form
  adheres to some specification, which eventually conforms, at least partially, to a
  dit. If the form needs to change, so does the dit, and vice versa. Therefore, dit
  cares about paper documents. The same is true of "validation" done using humans, or
  dit "scripts" implemented as shortcuts in ASIC hardware, neural nets, quantum
  algorithms, etc. To be clear, half of these things might never happen, but for dit,
  it's important to think about what _might_ happen in 50 years.

- <a name="footnote-2">[2:](#documents)</a> That wikipedia page is extremely outdated,
  and missing a huge number of very common formats. I just kept finding more and more as
  I dug. The serialization comparison article also includes many apparently dead
  formats, which may have never been used at all. I have skipped any formats I couldn't
  find any sign of having been used in the last ~5 years. However, this does not mean
  they aren't hiding out there in the wild, lurking in some obscure database.
