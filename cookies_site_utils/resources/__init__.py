from cookies_site_utils.core import File
import importlib.resources


def sync_resource(target_path):
    resource_path = importlib.resources.files('cookies_site_utils') / 'resources'
    src = (resource_path / target_path.name).read_text(encoding='utf-8')
    File(target_path, verbose=True).write_text(src)
