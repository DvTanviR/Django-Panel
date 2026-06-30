import re
import logging

logger = logging.getLogger(__name__)

FORBIDDEN_PATTERNS = [
    (r'FROM\s+\w+', lambda m: None, 'Only single-stage FROM allowed'),
    (r'ADD\s+', None, 'ADD is forbidden, use COPY'),
    (r'RUN\s+curl\s+\|', None, 'Piping curl to sh is forbidden'),
    (r'RUN\s+wget\s+\|', None, 'Piping wget to sh is forbidden'),
    (r'RUN\s+.*\|\s*bash', None, 'Piping to bash is forbidden'),
    (r'RUN\s+chmod\s+.*\+[xs]', None, 'Setting setuid/setgid bits is forbidden'),
    (r'USER\s+root', None, 'Running as root is forbidden'),
    (r'RUN\s+sudo', None, 'sudo is forbidden'),
    (r'RUN\s+apt-get\s+install\s+-y\s+\S+\s+\S+', None, 'Multiple packages in one apt-get line is discouraged'),
]

class DockerfileValidationError(Exception):
    pass

def validate_dockerfile(content: str) -> bool:
    lines = content.split('\n')
    errors = []
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        
        for pattern, _, msg in FORBIDDEN_PATTERNS:
            if re.search(pattern, stripped, re.IGNORECASE):
                errors.append(f"Line {i}: {msg} - {stripped}")
    
    if errors:
        for e in errors:
            logger.warning(f"Dockerfile validation: {e}")
        raise DockerfileValidationError("Dockerfile validation failed:\n" + "\n".join(errors))
    
    logger.info("Dockerfile validation passed")
    return True
