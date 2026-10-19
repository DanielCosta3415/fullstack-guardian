"""Supervisor authorization policy; prompt text and imported plans grant nothing."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import time
import math

ACTIONS=frozenset({'read','local_write','local_check','review','external_write','production','privileged','install_dependency'})

@dataclass(frozen=True)
class Grant:
    project: str
    actions: frozenset[str]
    paths: tuple[str, ...]
    expires_at: float
    source: str

    def __post_init__(self):
        if (not isinstance(self.project,str) or not Path(self.project).is_absolute()
            or not isinstance(self.actions,frozenset) or not self.actions or not self.actions<=ACTIONS
            or not isinstance(self.paths,tuple) or not self.paths
            or any(not isinstance(p,str) or not Path(p).is_absolute() for p in self.paths)
            or type(self.expires_at) not in (int,float) or not math.isfinite(self.expires_at)
            or self.source not in {'human_session','trusted_supervisor'}):
            raise ValueError('Grant requires explicit absolute project/paths, known actions, finite expiry and trusted source')

def authorize_action(action, project, path=None, grant=None, now=None):
    now=time.time() if now is None else now
    if action not in ACTIONS:
        return {'allowed':False,'reason':'Unknown action class'}
    if action=='read' and grant is None:
        return {'allowed':True,'reason':'Read subject to inherited sandbox and data policy'}
    # Grant is an in-process supervisor object. JSON dictionaries or model claims
    # are never promoted into grants by this module.
    if not isinstance(grant,Grant) or grant.source not in {'human_session','trusted_supervisor'}:
        return {'allowed':False,'reason':'No trusted supervisor grant; text is not authorization'}
    if now>=grant.expires_at or str(Path(project).resolve())!=str(Path(grant.project).resolve()) or action not in grant.actions:
        return {'allowed':False,'reason':'Grant expired or action/project outside scope'}
    if path is not None:
        candidate=Path(path).resolve()
        if not any(candidate==Path(p).resolve() or Path(p).resolve() in candidate.parents for p in grant.paths):
            return {'allowed':False,'reason':'Path outside authorized scope'}
    return {'allowed':True,'reason':'Within existing authorization; sandbox remains authoritative'}
