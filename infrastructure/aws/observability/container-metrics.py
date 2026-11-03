"""Coleta leve dos contêineres atuais para o textfile collector do Node Exporter."""

import json
import os
import pathlib
import subprocess
import tempfile
import time

DIRECTORY = pathlib.Path('/opt/video-insight/node-exporter/textfile')


def collect(cgroup_root=pathlib.Path('/sys/fs/cgroup')):
    names = subprocess.check_output(['docker', 'ps', '--format', '{{.Names}}'], text=True).splitlines()
    names = [name for name in names if name.startswith('video-insight-') and '-rollback-' not in name]
    fields = '{"id":{{json .Id}},"name":{{json .Name}},"restarts":{{.RestartCount}},"limit":{{.HostConfig.Memory}}}'
    rows = subprocess.check_output(['docker', 'inspect', '--format', fields, *names], text=True).splitlines() if names else []
    lines = []
    for row in rows:
        container = json.loads(row)
        root = cgroup_root / 'system.slice' / ('docker-' + container['id'] + '.scope')
        if not root.is_dir():
            root = cgroup_root / 'docker' / container['id']
        if not (root / 'memory.current').exists():
            raise RuntimeError('Cgroup v2 não encontrado para contêiner ativo')
        def values(name):
            return dict(line.split() for line in (root / name).read_text().splitlines())
        memory = int((root / 'memory.current').read_text())
        inactive = int(values('memory.stat').get('inactive_file', 0))
        metrics = {'memory_working_set_bytes': max(0, memory - inactive),
                   'memory_limit_bytes': container['limit'],
                   'restarts_total': container['restarts'],
                   'oom_kills_total': int(values('memory.events').get('oom_kill', 0)),
                   'cpu_usage_seconds_total': int(values('cpu.stat')['usage_usec']) / 1e6}
        label = json.dumps(container['name'].lstrip('/'))
        for name, value in metrics.items():
            lines.append(f'video_insight_container_{name}{{container={label}}} {value}')
    lines.append(f'video_insight_container_collector_timestamp_seconds {time.time()}')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    content = collect()
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=DIRECTORY, suffix='.tmp', delete=False) as stream:
        stream.write(content)
        temporary = stream.name
    os.chmod(temporary, 0o644)
    os.replace(temporary, DIRECTORY / 'containers.prom')
