
## 2024-05-24 - [TacticalAdvisor O(1) Operator Lookup Optimization]
**Learning:** The `TacticalAdvisor` case-insensitive operator lookup was using an O(N) linear scan over all database keys (`self.db.keys()`) when checking for matches (e.g., `name.lower() == key.lower()`). This fallback was triggered frequently when input casing didn't perfectly match the JSON keys.
**Action:** Introduced a pre-computed `_name_map` dictionary in `__init__` that maps lowercase names to their exact database keys, changing the lookup from O(N) to O(1). When dealing with configuration or data dictionaries where keys might be queried case-insensitively, pre-compute a lowercase mapping table instead of doing on-the-fly iteration.
