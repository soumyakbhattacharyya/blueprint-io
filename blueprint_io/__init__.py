import json
import logging
import sys
import urlparse

from blueprint import git
from blueprint import Blueprint
from blueprint import context_managers
import http


def pull(server, secret, name):
    """
    Pull a blueprint from the secret and name on the configured server.
    """
    r = http.get('/{0}/{1}'.format(secret, name), server=server)
    if 200 == r.status:
        b = Blueprint()
        b.name = name
        b.update(json.loads(r.read()))

        for filename in b.sources.itervalues():
            logging.info('fetching source tarballs - this may take a while')
            r = http.get('/{0}/{1}/{2}'.format(secret, name, filename),
                         server=server)
            if 200 == r.status:
                try:
                    f = open(filename, 'w')
                    f.write(r.read())
                except OSError:
                    logging.error('could not open {0}'.format(filename))
                    return None
                finally:
                    f.close()
            elif 404 == r.status:
                logging.error('{0} not found'.format(filename))
                return None
            elif 502 == r.status:
                logging.error('upstream storage service failed')
                return None
            else:
                logging.error('unexpected {0} fetching tarball'.
                              format(r.status))
                return None

        return b
    elif 404 == r.status:
        logging.error('blueprint not found')
    elif 502 == r.status:
        logging.error('upstream storage service failed')
    else:
        logging.error('unexpected {0} fetching blueprint'.format(r.status))
    return None


def push(server, secret, b):
    """
    Push a blueprint to the secret and its name on the configured server.
    """

    r = http.put('/{0}/{1}'.format(secret, b.name),
                 b.dumps(),
                 {'Content-Type': 'application/json'},
                 server=server)
    if 202 == r.status:
        pass
    elif 400 == r.status:
        logging.error('malformed blueprint')
        return None
    elif 502 ==  r.status:
        logging.error('upstream storage service failed')
        return None
    else:
        logging.error('unexpected {0} storing blueprint'.format(r.status))
        return None

    tree = git.tree(b._commit)
    for dirname, filename in sorted(b.sources.iteritems()):
        blob = git.blob(tree, filename)
        content = git.content(blob)
        logging.info('storing source tarballs - this may take a while')
        r = http.put('/{0}/{1}/{2}'.format(secret, b.name, filename),
                     content,
                     {'Content-Type': 'application/x-tar'},
                     server=server)
        if 202 == r.status:
            pass
        elif 400 == r.status:
            logging.error('tarball content or name not expected')
            return None
        elif 404 == r.status:
            logging.error('blueprint not found')
            return None
        elif 502 == r.status:
            logging.error('upstream storage service failed')
            return None
        else:
            logging.error('unexpected {0} storing tarball'.format(r.status))
            return None

    return '{0}/{1}/{2}'.format(server, secret, b.name)


def secret(server):
    """
    Fetch a new secret from the configured server.
    """
    r = http.get('/secret', server=server)
    if 201 == r.status:
        secret = r.read().rstrip()
        logging.warning('created secret {0}'.format(secret))
        logging.warning('to set as the default secret, store it in ~/.blueprint-io.cfg:')
        sys.stderr.write('\n[default]\nsecret = {0}\nserver = {1}\n\n'.
            format(secret, cfg.server()))
        return secret
    elif 502 == r.status:
        logging.error('upstream storage service failed')
        return None
    else:
        logging.error('unexpected {0} creating secret'.format(r.status))
        return None
