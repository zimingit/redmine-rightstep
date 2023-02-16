def sortByVersion(issue):
    version = issue.fixed_version.name if hasattr(issue, 'fixed_version') else 'Без версии'
    if "TEST" in version:
        return -1
    if "DEV" in version:
        return 0
    else:
        return 1