# TODO

Improvements to public modules in this repo.

## permute

- [ ] Extract the default wordlist into `files/hostname_permutations.txt` so it's user-editable without editing the module. Follow the `brute_hosts.py` pattern: `options` points to a path, module reads the file.
- [ ] Parallelise DNS queries via `ThreadingMixin` (hosts-hosts/brute_hosts uses this). Current sequential behaviour is noticeably slow past ~50 input hosts.
- [ ] Add "character substitution" patterns: `o`↔`0`, `l`↔`1`, `e`↔`3`. Common in typosquat-style subdomains.
- [ ] Add "environment-split" insertion: for `api.example.com`, try `api.dev.example.com` (word inserted *after* leaf, not before).
