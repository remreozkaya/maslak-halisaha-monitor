"""One scheduled GitHub Actions check. Never initializes missing remote state."""
import logging
import os
from datetime import datetime
from .config import Settings
from .github_state import GithubState, RemoteStore
from .main import run_once, make_sender
from .schedule import ISTANBUL, window_at
from .site import SiteProbe
from .store import Store

LOG=logging.getLogger('maslak-monitor')

def main():
    logging.basicConfig(level=logging.WARNING,format='%(message)s')
    now=datetime.now(ISTANBUL)
    if window_at(now) is None:
        LOG.warning('status=outside_window')
        return 0
    remote=None
    sender=None
    try:
        settings=Settings.from_env()
        if settings.dry_run:
            store=Store(':memory:')
        else:
            remote=GithubState(os.environ['GITHUB_REPOSITORY'],os.environ['GITHUB_TOKEN'],
                               os.environ['STATE_ENCRYPTION_KEY'].encode())
            store=RemoteStore(remote)
        with store:
            if not settings.dry_run:
                store.recover_interrupted()
            sender=make_sender(settings)
            with SiteProbe(settings) as probe:
                result=run_once(now,settings,probe,store,sender,settings.dry_run)
            LOG.warning('status=%s available_count=%s',result.status,result.count)
            return int(result.status.endswith(('_unknown','_rejected')))
    except Exception as exc:
        # URLs, authentication responses and exception messages may contain private data.
        LOG.error('check_failed_type=%s',type(exc).__name__)
        return 1
    finally:
        if sender: sender.close()
        if remote: remote.close()

if __name__=='__main__':
    raise SystemExit(main())
