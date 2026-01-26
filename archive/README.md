# Archive Directory

This directory contains scripts and files that have been archived for historical reference but are no longer actively used in the main workflow.

**Last Updated:** 2026-01-26

---

## Directory Structure

### `superseded/`
Scripts that have been replaced by improved versions:

- **`batch_add_utci.py`** - Original UTCI batch processor
  - **Superseded by:** `batch_add_enhanced_utci_optimized.py`
  - **Reason:** Lacks multi-day context (prior/next day weather)
  - **Keep for:** Reference implementation

- **`batch_add_enhanced_utci.py`** - Enhanced UTCI with multi-day context
  - **Superseded by:** `batch_add_enhanced_utci_optimized.py`
  - **Reason:** 10x slower (not optimized)
  - **Keep for:** Understanding enhancement logic

### `phoenix_specific/`
Phoenix, AZ specific implementations:

- **`add_utci_to_phoenix.py`** - Phoenix-specific UTCI processing
  - **Reason:** City-specific, not part of generic multi-city workflow
  - **Status:** May be useful for future single-city deep dives
  - **Related docs:** `docs/phoenix/` directory

### `legacy_scripts/`
Old scripts from previous workflow iterations (to be added as needed)

### `experimental_notebooks/`
Experimental Jupyter notebooks that didn't make it to production (to be added as needed)

---

## Why Archive vs Delete?

We archive rather than delete because:

1. **Historical Context** - Shows evolution of the codebase
2. **Reference Implementation** - Can be consulted for understanding original approaches
3. **Rollback Option** - If new approach fails, we have working fallback
4. **Learning Resource** - Documents what was tried and why it was changed

---

## When to Move Files Here

Move files to archive when:
- ✅ A better/faster replacement exists
- ✅ The file is city-specific but not part of main workflow
- ✅ Experimental work that didn't pan out but has educational value
- ✅ Legacy code that's no longer compatible with current data structures

Do NOT archive:
- ❌ Files still used in any pipeline
- ❌ Core utilities depended on by multiple scripts
- ❌ Files with unique functionality not replicated elsewhere

---

## Archive vs Delete

**Archive** (what's here):
- Superseded implementations
- City-specific scripts
- Experimental prototypes
- Historical versions

**Delete** (not kept):
- True duplicates with zero differences
- Temporary test files
- Auto-generated artifacts
- Files with no historical value

---

## Supersession History

### UTCI Processing Evolution

1. **`batch_add_utci.py`** (Original)
   - Single-day UTCI calculation
   - Basic ERA5 integration
   - ~100 locations/hour

2. **`batch_add_enhanced_utci.py`** (Enhanced)
   - Added prior/next day context
   - Improved temporal accuracy
   - ~10 locations/hour (slow due to repeated API calls)

3. **`batch_add_enhanced_utci_optimized.py`** (Current) ✅
   - Bulk date fetching
   - Caching optimizations
   - ~100+ locations/hour (10x improvement)
   - **This is the production version**

---

## Restoration Instructions

If you need to restore an archived script:

1. Copy (don't move) from archive to working directory
2. Review for compatibility with current data structures
3. Update any hardcoded paths
4. Test thoroughly before using in production
5. Document why restoration was necessary

---

## Regular Maintenance

Review this archive every 6-12 months:
- Delete files that are truly obsolete (>2 years old with no reference value)
- Update this README if new files are added
- Consider compressing old files if archive grows large

---

## Questions?

See `docs/CLEANUP_TODO.md` for the full cleanup rationale and decision process.
