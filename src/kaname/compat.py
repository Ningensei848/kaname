"""Read legacy identifiers without changing existing operational records."""
import os

LEGACY_SYNC_ROOT = 'TechKB'
LEGACY_SYNC_PREFIX = '.techkb-sync'
LEGACY_ALERT_PREFIX = '<!-- techkb-alert:'


def env_value(name, default=None):
    if name in os.environ:
        return os.environ[name]
    return os.environ.get(name.replace('KANAME_', 'TECHKB_', 1), default)
